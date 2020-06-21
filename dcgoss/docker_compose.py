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

import logging
import os
import subprocess
import sys

from shutil import which


class DockerCompose(object):
    def __init__(self, path):
        self.path = path
        self.file = '{}/docker-compose.yaml'.format(self.path)
        self.binary = which('docker-compose')

        # Validate that the docker-compose binary is present
        if not self.binary:
            raise FileNotFoundError('docker-compose binary is not present on PATH')

        # Validate that the docker-compose binary is executable
        if not os.access(self.binary, os.X_OK):
            raise PermissionError('docker-compose binary is not executable')

        # Validate that the docker-compose.yaml file is present
        if not os.path.isfile(self.file):
            raise FileNotFoundError('docker-compose.yaml not present in {}'.format(self.path))

    def prepare_cmd(self, *args):
        cmd = list(args)

        # Prepend the path to the binary
        cmd.insert(0, self.binary)

        # Prepend the name to use for the docker-compose project
        cmd.insert(1, '--project-name')
        cmd.insert(2, 'goss')

        # Prepend the docker-compose project path
        cmd.insert(3, '--project-directory')
        cmd.insert(4, self.path)

        # Prepend the docker-compose file path
        cmd.insert(5, '--file')
        cmd.insert(6, self.file)

        # Allow disabling colored output
        if 'NO_COLOR' in os.environ and os.environ['NO_COLOR'].lower() in ['1', 'true']:
            cmd.insert(7, '--no-ansi')

        return cmd

    def _execute_cmd_pipe(self, *args):
        # Prepare the command to execute
        cmd = self.prepare_cmd(*args)

        # Execute the command and capture any stdout or stderr output
        logging.debug('Executing command: {}'.format(cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = process.stdout.read().decode(sys.getdefaultencoding())
        stderr = process.stderr.read().decode(sys.getdefaultencoding())
        process.communicate()

        # Return the process exit code, stdout and stderr output
        return process.returncode, stdout, stderr

    def _execute_cmd(self, *args):
        # Prepare the command to execute
        cmd = self.prepare_cmd(*args)

        # Execute the command
        logging.debug('Executing command: {}'.format(cmd))
        process = subprocess.Popen(cmd)
        process.communicate()

        # Return the process exit code
        return process.returncode

    def up(self, service=None):
        if service:
            exit_code = self._execute_cmd('up', '-d', service)
        else:
            exit_code = self._execute_cmd('up', '-d')

        if exit_code > 0:
            raise RuntimeError('docker-compose up failed with exit code: {}'.format(exit_code))

    def down(self):
        exit_code = self._execute_cmd('down', '--volumes')

        if exit_code > 0:
            raise RuntimeError('docker-compose down failed with exit code: {}'.format(exit_code))

    def start(self, service=None):
        if service:
            exit_code = self._execute_cmd('start', service)
        else:
            exit_code = self._execute_cmd('start')

        if exit_code > 0:
            raise RuntimeError('docker-compose start failed with exit code: {}'.format(exit_code))

    def stop(self, service=None):
        if service:
            exit_code = self._execute_cmd('stop', service)
        else:
            exit_code = self._execute_cmd('stop')

        if exit_code > 0:
            raise RuntimeError('docker-compose stop failed with exit code: {}'.format(exit_code))

    def restart(self, service=None):
        if service:
            exit_code = self._execute_cmd('restart', service)
        else:
            exit_code = self._execute_cmd('restart')

        if exit_code > 0:
            raise RuntimeError('docker-compose restart failed with exit code: {}'.format(exit_code))

    def exec(self, service, *args):
        return self._execute_cmd('exec', service, *args)

    def exec_pipe(self, service, *args):
        return self._execute_cmd_pipe('exec', service, *args)

    def log(self, service=None):
        if service:
            cmd = self._execute_cmd_pipe('logs', service)
        else:
            cmd = self._execute_cmd_pipe('logs')

        # Return the log lines as a list
        return cmd[1].splitlines()[1:] if cmd[0] == 0 else []

    def get_services(self):
        cmd = self._execute_cmd_pipe('ps', '--services')

        # Return a list of all service names
        return cmd[1].splitlines() if cmd[0] == 0 else []

    def get_container_id(self, service):
        cmd = self._execute_cmd_pipe('ps', '--quiet', service)

        # Return the container ID for the given service
        return cmd[1].rstrip() if cmd[0] == 0 else None

    def is_running(self, service):
        cmd = self._execute_cmd_pipe('top', service)

        # Return the running state of the given service
        return cmd[0] == 0 and cmd[1] != ''
