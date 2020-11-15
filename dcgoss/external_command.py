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
import subprocess
import sys


class ExternalCommand(object):
    def prepare_cmd(self, *args):
        # Prepare the command to execute
        cmd = list(args)

        # Validate that a to execute binary has been defined
        if not hasattr(self, 'binary'):
            raise AssertionError('No binary defined for external command ({})'.format(self.__class__.__name__))

        # Prepend the path to the binary
        cmd.insert(0, self.binary)

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
