#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import docker
import re

SUBMITTER_CONF = {}

with open('docker-submitter.yaml', 'r') as stream:
    SUBMITTER_CONF = None
    try:
	    SUBMITTER_CONF = yaml.load(stream)
    except yaml.YAMLError as ex:
        import sys
        sys.stderr.write(ex)
        sys.exit(1)
		
		
def get_mib(size):
    """
    Transforms a size specified with different factors to MiB
    """
    
    if type(size) is str:
        size = size.strip()
        size_items = size.split()
    
        if len(size_items) == 1:
            m = re.search('([0-9]+)([A-Za-z]+)', size_items[0])
            if m.group(1) and m.group(2):
                size_items = [m.group(1), m.group(2)]
            
        # MiB interpreted by default
        try:
            size = float(size_items[0])
        except ValueError:
            return -1
            
        if len(size_items) == 2:
            if size_items[1] in ['B', 'b']:
                size = size / 1048576
            elif size_items[1] in ['KB', 'K', 'k']:
                size = size / 1024
            elif size_items[1] in ['GB', 'G', 'g']:
                size = size * 1024
            elif size_items[1] in ['TB', 'T', 't']:
                size = size * 1048576
            # Bad factor
            elif size_items[1] not in ['MB', 'M', 'm']:
                size = -1
        # Bad format            
        elif len(size_items) > 2:
            return -1
    else:
        # MiB interpreted by default
        size = float(size)
    
    # Negative size
    if size <= 0:
        return -1
    
    return size
    
    

