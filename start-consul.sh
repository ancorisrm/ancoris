#!/bin/bash

# UBUNTU MASTER
docker rm -f  consul
# docker run -tid --name consul --net=host consul agent -server -bind 172.16.243.131 -bootstrap-expect=1 -ui -client 172.16.243.131
docker run -tid --name consul -e "CONSUL_UI_BETA=true" --net=host consul agent -server -bind 127.0.0.1 -bootstrap-expect=1 -ui -client 127.0.0.1

# CENTOS
# docker run -ti --name consul --net=host consul agent -server -bind 10.0.0.216 -join 172.16.243.131
