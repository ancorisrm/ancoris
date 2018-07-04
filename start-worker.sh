#!/bin/bash

# Remove the current container
docker rm -f ancoris-worker

# Rebuild the worker image
cd worker_api
./build.sh
cd ..

# Run a container with the new image
# NOTE. Both host and container mount paths have to match and the shared option
# is a must. The volumes will be mounted by the host but they will be managed
# by the container once mounted.
docker run -tid \
    --name ancoris-worker \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /mnt/ancoris:/mnt/ancoris:rw,shared \
    -v /mnt/glusterfs:/mnt/ancoris/glusterfs:rw,shared \
    -v "$(pwd)"/conf/consul.yaml:/opt/ancoris/conf/consul.yaml:ro \
    -v "$(pwd)"/conf/worker.yaml:/opt/ancoris/conf/worker.yaml:ro \
    -p 40200:40200 \
    --net=host \
    --privileged \
    ancorisorchestration/worker
