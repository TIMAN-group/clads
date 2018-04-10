#!/bin/bash

docker-machine create \
    --driver azure \
    --azure-resource-group CLaDS \
    --azure-size $1 \
    --azure-vnet CLaDS-vnet \
    --azure-subnet default \
    --azure-subnet-prefix 10.0.0.0/24 \
    --azure-open-port 80 \
    --azure-open-port 443 \
    --azure-open-port 222 \
    clads-vcs
