#!/bin/bash

find . -regex "\(*~\|.*__pycache__.*\|*.py[co]\)" -delete
find . -name "*~" -delete

tar --dereference -c -f ancoris-master.tar.gz \
    services \
    helpers \
    errors \
    conf \
    master.py \
    samples.py

docker build -t ancorisorchestration/master .
