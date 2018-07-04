#!/bin/bash

# Remove the current container
docker rm -f ancoris-master

# Rebuild the master image
cd master_api
./build.sh
cd ..

docker run -tid \
    --name ancoris-master \
    -v "$(pwd)"/conf/consul.yaml:/opt/ancoris/conf/consul.yaml:ro \
    -v "$(pwd)"/conf/master.yaml:/opt/ancoris/conf/master.yaml:ro \
    -p 40100:40100 \
    --net=host \
    ancorisorchestration/master
