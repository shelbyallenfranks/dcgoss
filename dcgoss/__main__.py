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

import os
import argparse
import logging
import dcgoss


def main():
    # Setup the argument parser
    parser = argparse.ArgumentParser(prog='dcgoss', description='A docker-compose wrapper for goss')
    parser.add_argument('action', type=str, choices=['run', 'edit'], help='action to execute')
    parser.add_argument('service', type=str, help='docker-compose service name')
    parser.add_argument('path', type=str, nargs='?', default=os.getcwd(), help='docker-compose project path')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + dcgoss.__version__)

    # Parse the arguments
    args = parser.parse_args()

    try:
        # Execute the requested action
        return getattr(dcgoss, args.action)(args.path, args.service)

    except FileNotFoundError as e:
        logging.error(e)
        return 1


if __name__ == '__main__':
    exit(main())
