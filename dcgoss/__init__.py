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

from .dcgoss import DCGoss
from .docker import Docker
from .docker_compose import DockerCompose

__version__ = '0.1.3'


def run(path, service, retry_timeout=300, retry_interval=0.2):
    return DCGoss(path, Docker(), DockerCompose(path), retry_timeout, retry_interval).run(service)


def edit(path, service, retry_timeout=300, retry_interval=0.2):
    return DCGoss(path, Docker(), DockerCompose(path), retry_timeout, retry_interval).edit(service)
