#!/bin/bash
set -e

docker-machine scp config.toml clads-ci-bastion:~
docker-machine scp cloud-init.txt clads-ci-bastion:~
docker-machine ssh clads-ci-bastion \
    sudo mv config.toml cloud-init.txt /etc/gitlab-runner/
