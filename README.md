# dcgoss

This is a Python implementation of the [dcgoss](https://github.com/aelsabbahy/goss/tree/master/extras/dcgoss) shell script that provides a wrapper around [goss](https://github.com/aelsabbahy/goss) for executing tests within docker containers using docker-compose.

## Prerequisites

- python3
- docker
- docker-compose
- goss

For non-Linux systems, place the Linux goss binary on your `PATH` or point to it with the `GOSS_PATH` environment variable.

## Installation

```bash
pip3 install dcgoss
```

## Usage

Run tests:
```bash
dcgoss run <service name> [<compose path>]
```

Edit tests:
```bash
dcgoss edit <service name> [<compose path>]
```
