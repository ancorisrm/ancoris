#!/usr/bin/python
# -*- coding: utf-8 -*-

from helpers.consul_common import *
from errors.consul import (
    NodeRegistrationError,
    ServiceRegistrationError,
)

def deregister_node(node, session):
    node_key = 'nodes/' + node
    keys = session.kv.find(node_key)
    for key in keys:
        del session.kv[key]

def register_node(node_conf, session):
    """
    Register the node with the properties available in node.yaml if
    there is not already registered.
    """

    # Generate the node name
    node_index = 0
    nodes_key = 'nodes/'
    kv = get_nested_dict(session.kv.find(nodes_key))
    if "nodes" in kv:
        node_index = len(kv["nodes"].keys())
        for node, _ in kv['nodes'].items():
            if kv['nodes'][node]['ancoris']['address'] \
                == node_conf['ancoris']['address']:
                # Return if the node is already registered
                return node
    node = f"node{node_index}"

    # Write the node's properties
    node_key = nodes_key + node + '/'
    consul_dict = {}
    consul_dict["nodes"] = {}
    consul_dict["nodes"][node] = node_conf
    flat_dict = get_flat_dict(consul_dict)

    for key, value in flat_dict.items():
        session.kv[key] = value

    # Custom setup for resources so free items/units are set
    for key, value in node_conf['resources'].items():
        try:
            if key == 'cpus':
                set_node_cpus_cores(node, value['cores'], session)
            elif key == 'memory':
                set_node_memory_mib(node, value['mib'], session)
            elif key == 'swap':
                set_node_swap_mib(node, value['mib'], session)
            elif key == 'devices':
                for device_key, device_value in value.items():
                    if device_key == 'ssd' or device_key == 'hdd':
                        for disk_id, disk_value in value[device_key].items():
                            set_node_disk_mib(node,
                                              device_key,
                                              disk_id,
                                              disk_value['mib'],
                                              session)
                    elif device_key == 'tmpfs':
                        continue
                    elif device_key == 'glusterfs':
                        continue
                    else:
                        raise NotImplementedError

        except ValueError as e:
            raise NodeRegistrationError(str(e)) from e

    # Return the chosen node name
    return node

def register_service(service_name, session, http_endpoint, interval='5s'):
    try:
        session.agent.service.register(
            service_name,
            httpcheck=http_endpoint,
            interval=interval)
    except ValueError as e:
        raise ServiceRegistrationError('Could not register the service. '
        + str(e))
