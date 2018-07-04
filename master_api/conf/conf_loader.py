#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml

def __load_conf(filename):
    with open(filename, 'r') as stream:
        try:
            return yaml.load(stream)
        except yaml.YAMLError as ex:
            import sys
            sys.stderr.write(ex)
            sys.exit(1)

master = __load_conf('conf/master.yaml')
consul = __load_conf('conf/consul.yaml')
