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

from shutil import which


class Docker(object):
    def __init__(self):
        self.binary = which('docker')

        # Validate that the docker binary is present
        if not self.binary:
            raise FileNotFoundError('docker binary is not present on PATH')

        # Validate that the docker binary is executable
        if not os.access(self.binary, os.X_OK):
            raise PermissionError('docker binary is not executable')

    def _execute_cmd(self, *args):
        # Prepare the command to execute
        cmd = list(args)

        # Prepend the path to the binary
        cmd.insert(0, self.binary)

        # Execute the command
        logging.debug('Executing command: {}'.format(cmd))
        process = subprocess.Popen(cmd)
        process.communicate()

        # Return the process exit code
        return process.returncode

    def cp(self, source, target):
        exit_code = self._execute_cmd('cp', source, target)

        if exit_code > 0:
            raise RuntimeError('docker cp failed with exit code: {}'.format(exit_code))
