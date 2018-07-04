#!/bin/bash

# http://man7.org/linux/man-pages/man7/capabilities.7.html
# Not working...
# docker run --cap-add=SYS_ADMIN --security-opt apparmor:unconfined -ti -v $(pwd)/disk:/disk --name volm centos

# It works, but volumes are not accesible to the host if mounted inside a
# container
docker run --privileged -ti -v $(pwd)/disk:/disk --name volm centos
