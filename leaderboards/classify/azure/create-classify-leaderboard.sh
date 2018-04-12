#!/bin/bash
set -e

docker-machine create \
    --driver azure \
    --azure-resource-group CLaDS \
    --azure-size $1 \
    --azure-vnet CLaDS-vnet \
    --azure-subnet default \
    --azure-subnet-prefix 10.0.0.0/24 \
    --azure-private-ip-address 10.0.0.11 \
    --azure-open-port 80 \
    --azure-custom-data cloud-init.txt \
    clads-classify-leaderboard

eval $(docker-machine env clads-classify-leaderboard)
docker-compose up -d
docker-compose exec mongo \
    mongo competition --eval "db.results.createIndex({'username': 1})"
