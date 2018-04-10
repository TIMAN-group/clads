#!/bin/bash
set -e

docker-machine create \
    --driver azure \
    --azure-resource-group CLaDS \
    --azure-size $1 \
    --azure-vnet CLaDS-vnet \
    --azure-subnet default \
    --azure-subnet-prefix 10.0.0.0/24 \
    --azure-private-ip-address 10.0.0.5 \
    clads-cache

eval $(docker-machine env clads-cache)

docker run -it -d --restart always -p 9005:9000 \
    -v /srv/.minio:/root/.minio -v /srv/export:/export \
    --name minio \
    minio/minio:latest server /export

docker-machine ssh clads-cache sudo mkdir -p /srv/export/runner
docker-machine ssh clads-cache sudo cat /srv/.minio/config.json
