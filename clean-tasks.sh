#!/bin/bash
docker rm -f $(docker ps -a | awk '{print $NF}' | grep task_*)
