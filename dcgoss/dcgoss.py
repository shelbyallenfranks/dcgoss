# Copyright 2020 Shelby Allen-Franks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dateutil.parser
import logging
import os
import platform
import stat
import subprocess
import sys

from shutil import copy, rmtree, which
from tempfile import mkdtemp
from time import time, sleep


# Define a custom log formatter
class DCGossLogFormat(logging.Formatter):
    LEVELS = {logging.DEBUG: '\033[0;35m', logging.INFO: '\033[0;36m', logging.WARNING: '\033[0;33m',
              logging.ERROR: '\033[0;31m', logging.CRITICAL: '\033[1;31m'}

    def format(self, record):
        if 'NO_COLOR' in os.environ and os.environ['NO_COLOR'].lower() in ['1', 'true']:
            return '{}: {}'.format(record.levelname, record.msg)
        else:
            return '{}{}\033[0m: {}'.format(self.LEVELS[record.levelno], record.levelname, record.msg)


# Initialize colorama for Windows only
if platform.system() == 'Windows':
    import colorama
    colorama.init()

# Fetch the root logger
root = logging.getLogger()
root.setLevel(logging.DEBUG if 'DEBUG' in os.environ and os.environ['DEBUG'].lower() in ['1', 'true'] else logging.INFO)

# Create a log handler that sends INFO/DEBUG logs to stdout
h_stdout = logging.StreamHandler(sys.stdout)
h_stdout.setLevel(logging.DEBUG)
h_stdout.addFilter(lambda record: record.levelno <= logging.INFO)
h_stdout.setFormatter(DCGossLogFormat())

# Create a log handler that sends CRITICAL/ERROR/WARNING logs to stderr
h_stderr = logging.StreamHandler(sys.stderr)
h_stderr.setLevel(logging.WARNING)
h_stderr.setFormatter(DCGossLogFormat())

# Add the log handlers to the root logger
root.addHandler(h_stdout)
root.addHandler(h_stderr)


class DCGoss(object):
    def __init__(self, path, docker, docker_compose, retry_timeout, retry_interval):
        self.docker = docker
        self.compose = docker_compose

        # Resolve the final retry timeout value
        self.retry_timeout = float(self._get_envvar('GOSS_RETRY_TIMEOUT', retry_timeout))

        # Resolve the final retry interval value
        self.retry_interval = float(self._get_envvar('GOSS_SLEEP', retry_interval))

        # Resolve the final initial startup delay value
        self.initial_startup = float(self._get_envvar('GOSS_INITIAL_STARTUP', 5))

        # Resolve the final path to the goss binary
        self.goss_bin = self._get_envvar('GOSS_PATH', which('goss'))

        # Resolve the final path to the goss files
        self.goss_files_path = self._get_envvar('GOSS_FILES_PATH', path)

        # Resolve the final path to the goss file
        self.goss_file = self._get_envvar('GOSS_FILE', '{}/goss.yaml'.format(self.goss_files_path))

        # Resolve the final path to an optional variables file
        self.goss_vars = self._get_envvar('GOSS_VARS', '{}/goss_vars.yaml'.format(self.goss_files_path))

        # Resolve the final path to an optional wait file
        self.goss_wait = self._get_envvar('GOSS_WAIT', '{}/goss_wait.yaml'.format(self.goss_files_path))

        # Resolve the final path where logs will be written
        self.log_path = self._get_envvar('GOSS_LOGS', '{}/.goss/logs'.format(self.goss_files_path))

        # Validate that the goss binary is present
        if not self.goss_bin:
            raise FileNotFoundError('goss binary is not present on PATH or GOSS_PATH is not set')

        # Validate that the goss file is present
        if not os.path.isfile(self.goss_file):
            raise FileNotFoundError('goss.yaml not present in {}'.format(self.goss_files_path))

        # Initialize application state variables
        self.start_time = 0
        self.forced_shutdown = False

    @staticmethod
    def _get_envvar(name, default_value=None):
        return os.environ[name] if name in os.environ else default_value

    def _startup(self, service):
        logging.info('Starting up...')

        # Keep track of the start time
        self.start_time = time()

        # Remove any previously created test resources
        logging.info('Removing any previous test resources...')
        self.compose.down()

        # Bring up the specified service and any dependencies
        logging.info('Starting "{}" service and any dependencies...'.format(service))
        self.compose.up(service)

        # Wait until the service is running
        logging.info('Waiting for "{}" service container to start successfully...'.format(service))
        while True:
            # Validate that the timeout has not been exceeded
            if (time() - self.start_time) > self.retry_timeout:
                raise TimeoutError('Timeout reached while waiting for initial container startup')

            # Validate that the service is up
            if not self._is_service_up(service):
                sleep(1)
                continue

            # Query the container start time
            started1 = self._get_start_time(service)

            # Wait some time to ensure the container remains up for an acceptable period of time
            sleep(self.initial_startup)

            # Query the container start time again
            started2 = self._get_start_time(service)

            # Validate that the container has not restarted
            if started1 == started2:
                sleep(1)
                if self._is_service_up(service):
                    break

        # Copy the goss binary and configs into the container
        logging.info('Copying goss binary and configuration into container...')
        self._copy_in(self.compose.get_container_id(service))

    def _is_service_up(self, service):
        # Query the container ID for the service
        container_id = self.compose.get_container_id(service)

        # Query the current container state
        container = self.docker.inspect(container_id) if container_id else {}
        state = container['State'] if 'State' in container else {}

        # Validate that the container is running
        if 'Running' in state and not state['Running']:
            return False

        # Validate that the container is not restarting
        if 'Restarting' in state and state['Restarting']:
            return False

        # Return true when all of the above checks have passed
        return True

    def _get_start_time(self, service):
        # Query the container ID for the service
        container_id = self.compose.get_container_id(service)

        # Query the current container state
        container = self.docker.inspect(container_id) if container_id else {}
        state = container['State'] if 'State' in container else {}

        # Return the start time for the container
        return dateutil.parser.isoparse(state['StartedAt']) if 'StartedAt' in state else None

    def _copy_in(self, container_id):
        temp_dir = mkdtemp()
        logging.debug('Created temp directory: {}'.format(temp_dir))

        try:
            # Copy in the goss binary and configuration
            logging.debug('Copying goss binary to temp directory: {}'.format(self.goss_bin))
            copy(self.goss_bin, '{}/goss'.format(temp_dir))
            logging.debug('Copying goss config to temp directory: {}'.format(self.goss_file))
            copy(self.goss_file, '{}/goss.yaml'.format(temp_dir))

            # Copy in the goss variables file when present
            if os.path.isfile(self.goss_vars):
                logging.debug('Copying goss variables file to temp directory: {}'.format(self.goss_vars))
                copy(self.goss_vars, '{}/goss_vars.yaml'.format(temp_dir))

            # Copy in the goss wait file when present
            if os.path.isfile(self.goss_wait):
                logging.debug('Copying goss wait file to temp directory: {}'.format(self.goss_wait))
                copy(self.goss_wait, '{}/goss_wait.yaml'.format(temp_dir))

            # Define the file permissions we will apply
            all_read_exec = stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
            all_read_write = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH

            # Ensure the directory is readable and executable
            logging.debug('Setting permissions on temp directory: {}'.format(oct(all_read_exec | all_read_write)))
            os.chmod(temp_dir, all_read_exec | all_read_write)

            # Ensure the binary is readable and executable
            logging.debug('Setting permissions on goss binary: {}'.format(oct(all_read_exec | all_read_write)))
            os.chmod('{}/goss'.format(temp_dir), all_read_exec | all_read_write)

            # Ensure the configuration file is readable and writable
            logging.debug('Setting permissions on goss config: {}'.format(oct(all_read_write)))
            os.chmod('{}/goss.yaml'.format(temp_dir), all_read_write)

            # Ensure the variables file is readable and writable
            if os.path.isfile(self.goss_vars):
                logging.debug('Setting permissions on goss variables file: {}'.format(oct(all_read_write)))
                os.chmod('{}/goss_vars.yaml'.format(temp_dir), all_read_write)

            # Ensure the wait file is readable and writable
            if os.path.isfile(self.goss_wait):
                logging.debug('Setting permissions on goss wait file: {}'.format(oct(all_read_write)))
                os.chmod('{}/goss_wait.yaml'.format(temp_dir), all_read_write)

            # Copy the temp directory into the container
            self.docker.cp(temp_dir, '{}:/goss'.format(container_id))

        finally:
            # Clean up all temporary files
            logging.debug('Removing temp directory: {}'.format(temp_dir))
            rmtree(temp_dir)

    def _copy_out(self, container_id):
        temp_dir = mkdtemp()
        logging.debug('Created temp directory: {}'.format(temp_dir))

        try:
            # Copy the files from the container into the temp directory
            logging.debug('Copying /goss directory from container ({}) into temp directory: {}'.format(container_id, temp_dir))
            self.docker.cp('{}:/goss'.format(container_id), temp_dir)

            # Restore the correct permissions for the goss file
            mode = os.stat(self.goss_file).st_mode
            logging.debug('Restoring correct permissions on goss config: {}'.format(oct(mode)))
            os.chmod('{}/goss/goss.yaml'.format(temp_dir), mode)

            # Restore the correct permissions for the variables file
            if os.path.isfile(self.goss_vars):
                mode = os.stat(self.goss_vars).st_mode
                logging.debug('Restoring correct permissions on goss variables file: {}'.format(oct(mode)))
                os.chmod('{}/goss/goss_vars.yaml'.format(temp_dir), mode)

            # Restore the correct permissions for the wait file
            if os.path.isfile(self.goss_wait):
                mode = os.stat(self.goss_wait).st_mode
                logging.debug('Restoring correct permissions on goss wait file: {}'.format(oct(mode)))
                os.chmod('{}/goss/goss_wait.yaml'.format(temp_dir), mode)

            # Copy the goss file into place
            logging.debug('Copying goss config back to its original location: {}'.format(self.goss_file))
            copy('{}/goss/goss.yaml'.format(temp_dir), self.goss_file)

            # Copy the variables file into place
            if os.path.isfile(self.goss_vars):
                logging.debug('Copying goss variables file back to its original location: {}'.format(self.goss_vars))
                copy('{}/goss/goss_vars.yaml'.format(temp_dir), self.goss_vars)

            # Copy the wait file into place
            if os.path.isfile(self.goss_wait):
                logging.debug('Copying goss wait file back to its original location: {}'.format(self.goss_wait))
                copy('{}/goss/goss_wait.yaml'.format(temp_dir), self.goss_wait)

        finally:
            # Clean up all temporary files
            logging.debug('Removing temp directory: {}'.format(temp_dir))
            rmtree(temp_dir)

    def _shutdown(self):
        logging.info('Shutting down...')

        try:
            if not self._get_envvar('NO_LOGS', '').lower() in ['1', 'true']:
                # Create the log directory
                if not os.path.exists(self.log_path):
                    os.makedirs(self.log_path)

                try:
                    # Save the logs from each container
                    logging.info('Saving container logs...')
                    for svc in self.compose.get_services():
                        with open('{}/{}.log'.format(self.log_path, svc), 'w') as log:
                            log.writelines('\n'.join(self.compose.log(svc)))
                except Exception as e:
                    logging.error('Failed to save container logs: {}'.format(e))

            # Stop all services
            logging.info('Stopping services...')
            self.compose.stop()

            # Remove all services, networks and volumes
            logging.info('Removing services and networks...')
            self.compose.down()

        except KeyboardInterrupt:
            if self.forced_shutdown:
                sys.exit(1)

            # Warn the user that they are interrupting the shutdown process
            logging.warning('Shutdown is in progress, force shutdown by sending another interrupt...')
            self.forced_shutdown = True
            self._shutdown()

    def _run_goss_validate(self, service, goss_file, goss_args):
        # Prepare the global arguments to pass to goss
        goss_args_global = ['--gossfile=/goss/{}'.format(goss_file)]

        # Include the variables file when present
        if os.path.isfile(self.goss_vars):
            goss_args_global.append('--vars=/goss/goss_vars.yaml')

        # Wait some time before executing any tests
        sleep(self.retry_interval)

        # Attempt to render the goss file in order to validate it
        logging.info('Validating goss file...')
        render_exit, render_stdout, _ = self.compose.exec_pipe(service, '/goss/goss', *goss_args_global, 'render')
        if render_exit > 0:
            raise RuntimeError('Failed to parse goss configuration:\n{}'.format(render_stdout))

        # Determine whether or not to display colored output from goss
        if self._get_envvar('NO_COLOR', '').lower() in ['1', 'true']:
            goss_args.append('--no-color')
        else:
            goss_args.append('--color')

        while True:
            # Validate that the timeout has not been exceeded
            if (time() - self.start_time) > self.retry_timeout:
                raise TimeoutError('Timeout reached while waiting for all tests to pass')

            # Execute goss within the container
            logging.info('Executing "goss validate"...')
            goss_exit = self.compose.exec(service, '/goss/goss', *goss_args_global, 'validate', *goss_args)

            # Break the loop if all tests passed successfully
            if goss_exit > 0:
                logging.info('Failed to execute all goss tests')
            else:
                break

            # Wait some time before running goss again
            logging.info('Waiting {} second(s) before retrying...'.format(self.retry_interval))
            sleep(self.retry_interval)

            # Ensure the container is still up and running
            if not self._is_service_up(service):
                self.compose.restart(service)

    def run(self, service):
        try:
            # Start the service
            self._startup(service)

            # Prepare the arguments to pass to 'goss validate' for the goss wait run
            goss_args_wait = self._get_envvar('GOSS_WAIT_OPTS', '--retry-timeout=30s --sleep=1s').split()

            # Prepare the arguments to pass to 'goss validate' for the main goss run
            goss_args = self._get_envvar('GOSS_OPTS', '--format=documentation').split()

            # Run the tests defined in the wait file
            if os.path.isfile(self.goss_wait):
                logging.info('Preparing to execute goss wait tests...')
                self._run_goss_validate(service, 'goss_wait.yaml', goss_args_wait)

            # Run the tests defined in the goss file
            logging.info('Preparing to execute goss tests...')
            self._run_goss_validate(service, 'goss.yaml', goss_args)

            logging.info('All tests successfully executed.')
            return 0

        except Exception as e:
            logging.error(e)
            return 1

        except KeyboardInterrupt:
            return 2

        finally:
            self._shutdown()

    def edit(self, service):
        try:
            # Start the service
            self._startup(service)

            # Query the container ID for the service
            container_id = self.compose.get_container_id(service)

            # Prepare the command to execute
            cmd = self.compose.prepare_cmd('exec', service, 'sh', '-c', 'cd /goss; PATH="/goss:$PATH" exec sh')

            # Execute the command interactively
            logging.info('Starting shell within "{}" service container ({})...'.format(service, container_id[0:12]))
            logging.info('Use "goss add" or "goss autoadd" to add tests and type "exit" when ready to save.')
            logging.debug('Executing interactive command: {}'.format(cmd))
            subprocess.call(cmd)

            # Copy the modified files out of the container
            logging.debug('Copying updated goss configurations from container...')
            self._copy_out(container_id)

            return 0

        except Exception as e:
            logging.error(e)
            return 1

        except KeyboardInterrupt:
            return 2

        finally:
            self._shutdown()
