#!/bin/bash

find . -regex "\(*~\|.*__pycache__.*\|*.py[co]\)" -delete
find . -name "*~" -delete

tar --dereference -c -f ancoris-worker.tar.gz \
    services \
    helpers \
    errors \
    conf \
    worker.py

docker build -t ancorisorchestration/worker .
