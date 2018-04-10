#!/bin/bash
set -e

docker-machine create \
    --driver azure \
    --azure-resource-group CLaDS \
    --azure-size $1 \
    --azure-vnet CLaDS-vnet \
    --azure-subnet default \
    --azure-subnet-prefix 10.0.0.0/24 \
    clads-ci-bastion

eval $(docker-machine env clads-ci-bastion)

docker run -d --name gitlab-runner --restart always \
    -v /etc/gitlab-runner:/etc/gitlab-runner \
    gitlab/gitlab-runner:latest

docker exec -it gitlab-runner gitlab-runner register
docker-machine ssh clads-ci-bastion \
    sudo cat /etc/gitlab-runner/config.toml | grep token
