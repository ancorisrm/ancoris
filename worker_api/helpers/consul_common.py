#!/usr/bin/python
# -*- coding: utf-8 -*-

import json


###############################################################################

def get_node_port(node, session):
    key = 'nodes/' + node + '/ancoris/port'
    return get_single_value(key, session)

def get_node_shared_volumes_path(node, session):
    key = 'nodes/' + node + '/ancoris/shared_volumes_path'
    return get_single_value(key, session)

def get_node_address(node, session):
    key = 'nodes/' + node + '/ancoris/address'
    return get_single_value(key, session)

def get_node_info(node, session):
    key = 'nodes/' + node + '/ancoris/'
    return get_nested_dict(get_dict_value(key, session))['nodes'][node]['ancoris']

###############################################################################

def get_nodes(session):
    return get_nested_dict(get_dict_value('nodes/', session))['nodes']

def get_node_names(session):
    return list(get_nodes(session).keys())

def _get_entity_mutex_key(entity):
    return 'ancoris/.' + entity + '_mutex'

def get_entity_group_items(entity, group_id, session):
    key = entity + '/groups/' + group_id
    return get_single_value(key, session)

###############################################################################
# VOLUMES
###############################################################################

def get_volume_attribute_key(volume_id, attribute):
    return  'volumes/all/' + volume_id + '/' + attribute

def get_volume_mutex_key(volume_id):
    return get_volume_attribute_key(volume_id, '.prime_task')

def lock_volume(volume_id, task_id, session):
    key = get_volume_mutex_key(volume_id)
    lock_key(key, session, value=task_id)

def get_volume_prime_task_mutex(volume_id, session):
    key = get_volume_mutex_key(volume_id)
    try:
        return get_single_value(key, session)
    except KeyError:
        return None

def get_volume_mode(volume_id, session):
    key = get_volume_attribute_key(volume_id, 'mode')
    return get_single_value(key, session)

def get_volume_size(volume_id, session):
    key = get_volume_attribute_key(volume_id, 'size')
    return float(get_single_value(key, session))

def get_volume_groups(volume_id, session):
    key = get_volume_attribute_key(volume_id, 'groups')
    return json.loads(get_single_value(key, session))

def get_volume_type(volume_id, session):
    key = get_volume_attribute_key(volume_id, 'type')
    return get_single_value(key, session)

def exists_volume(volume_id, session):
    key = 'volumes/all/' + volume_id
    if get_dict_value(key, session):
        return True
    return False

def volume_group_exists(volume_group, session):
    key = 'volumes/groups/' + volume_group
    if get_dict_value(key, session):
        return True
    return False


###############################################################################
# TASKS
###############################################################################

def get_task_host(task_id, session):
    key = 'tasks/all/' + task_id + '/host'
    return  get_single_value(key, session)

def get_task_node(task_id, session):
    key = 'tasks/all/' + task_id + '/node'
    return  get_single_value(key, session)

###############################################################################
# NODES/_/RESOURCES/CPUS/*
###############################################################################

def set_node_cpus_cores(node, cores, session):
    return set_items_update_free(get_node_cpus_cores_key(node),
                                 get_node_cpus_free_key(node),
                                 cores,
                                 session)

def get_node_cpus_cores(node, session):
    return float(get_single_value(get_node_cpus_free_key(node), session))

def set_node_cpus_normalizer(node, normalizer, session):
    key = get_node_cpus_normalizer_key(node)
    normalizer = float(normalizer)
    if normalizer <= 0:
        raise ValueError('Normalizer has to be greater than zero')
    session.kv[key] = normalizer

def get_node_cpus_normalizer(node, session):
    return float(get_single_value(get_node_cpus_normalizer_key(node), session))

def add_node_cpus_free(node, units, session):
    return add_free_items(get_node_cpus_cores_key(node),
                            get_node_cpus_free_key(node),
                            units)

def sub_node_cpus_free(node, units, session):
    return sub_free_items(get_node_cpus_cores_key(node),
                          get_node_cpus_free_key(node),
                          units,
                          session)

def get_node_cpus_cores_key(node):
    return 'nodes/' + node + '/resources/cpus/cores'

def get_node_cpus_free_key(node):
    return 'nodes/' + node + '/resources/cpus/free'

def get_node_cpus_normalizer_key(node):
    return 'nodes/' + node + '/resources/cpus/normalizer'

###############################################################################
# NODES/_/RESOURCES/MEMORY/*
###############################################################################
def set_node_memory_mib(node, mib, session):
    return set_items_update_free(get_node_memory_mib_key(node),
                                 get_node_memory_free_key(node),
                                 mib,
                                 session)

def get_node_memory_mib(node, session):
    return float(get_single_value(get_node_memory_free_key(node), session))

def add_node_memory_free(node, units, session):
    return add_free_items(get_node_memory_mib_key(node),
                          get_node_memory_free_key(node),
                          units,
                          session)

def sub_node_memory_free(node, units, session):
    return sub_free_items(get_node_memory_mib_key(node),
                          get_node_memory_free_key(node),
                          units,
                          session)

def get_node_memory_mib_key(node):
    return 'nodes/' + node + '/resources/memory/mib'

def get_node_memory_free_key(node):
    return 'nodes/' + node + '/resources/memory/free'

###############################################################################
# NODES/_/RESOURCES/SWAP/*
###############################################################################
def set_node_swap_mib(node, mib, session):
    return set_items_update_free(get_node_swap_mib_key(node),
                                 get_node_swap_free_key(node),
                                 mib,
                                 session)

def get_node_swap_mib(node, session):
    return float(get_single_value(get_node_swap_free_key(node), session))

def add_node_swap_free(node, units, session):
    return add_free_items(get_node_swap_mib_key(node),
                          get_node_swap_free_key(node),
                          units,
                          session)

def sub_node_swap_free(node, units, session):
    return sub_free_items(get_node_swap_mib_key(node),
                          get_node_swap_free_key(node),
                          units,
                          session)

def get_node_swap_mib_key(node):
    return 'nodes/' + node + '/resources/swap/mib'

def get_node_swap_free_key(node):
    return 'nodes/' + node + '/resources/swap/free'

###############################################################################
# NODES/_/RESOURCES/DEVICES/*
###############################################################################
def set_node_disk_mib(node, type, id, mib, session):
    return set_items_update_free(get_node_disk_mib_key(node, type, id),
                                   get_node_disk_free_key(node, type, id),
                                   mib,
                                   session)

def get_node_disk_mib(node, type, id, session):
    return float(get_single_value(get_node_disk_free_key(node, type, id), session))

def add_node_disk_free(node, type, id, units, session):
    return add_free_items(get_node_disk_mib_key(node, type, id),
                            get_node_disk_free_key(node, type, id),
                            units,
                            session)

def sub_node_disk_free(node, type, id, units, session):
    return sub_free_items(get_node_disk_mib_key(node, type, id),
                            get_node_disk_free_key(node, type, id),
                            units,
                            session)

def get_node_devices(node, session):
    key = 'nodes/' + node + '/resources/devices/'
    return get_dict_value(key, session)

def get_node_disk_mib_key(node, type, id):
    return 'nodes/' + node + '/resources/devices/' + type + '/' + id + '/mib'

def get_node_disk_free_key(node, type, id):
    return 'nodes/' + node + '/resources/devices/' + type + '/' + id + '/free'

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def set_items_update_free(items_key, free_key, units, session):
    if items_key in session.kv:
        items_prev = float(session.kv[items_key])
    else:
        items_prev = units

    if free_key in session.kv:
        free_prev = float(session.kv[free_key])
    else:
        free_prev = units

    used_items = items_prev - free_prev

    # The new number of items has to be greater or equal to the number
    # of used ones
    units = float(units)
    if units < used_items:
        raise ValueError()

    # Update the number of items
    session.kv[items_key] = units

    # Update the number of free items
    session.kv[free_key] = units - used_items

def get_single_value(key, session):
    return session.kv[key]

def get_dict_value(key, session):
    return session.kv.find(key)

def add_free_items(items_key, free_key, units, session):
    units = float(units)
    if units < 1:
        raise ValueError()
    return modify_free_items(items_key, free_key, units, session)

def sub_free_items(items_key, free_key, units, session):
    units = float(units)
    if units < 0:
        raise ValueError()
    return modify_free_items(items_key, free_key, -units, session)

def modify_free_items(items_key, free_key, units, session):
    items_prev = float(session.kv[items_key])
    free_prev = float(session.kv[free_key])
    free = free_prev + units

    # The new number of free cores has to be lower than the total
    # number of cores with a minimum value of 0
    if free <= items_prev and free >= 0:
        session.kv[free_key] = free

###############################################################################
# BASIC FUNCTIONS
###############################################################################

def restore_kv_backup(kv_backup, session):
    # Remove the affected content
    for key in kv_backup:
        del session.kv[key]

    # Restore the initial content
    flat_dict = get_flat_dict(kv_backup)
    for key, value in flat_dict.items():
        session.kv[key] = value


def lock_key(key, session, value=None):
    locker_session_id = session.session.create(delay="0s", ttl="10s")
    if not session.kv.acquire_lock(key, locker_session_id):
        session.session.destroy(locker_session_id)
        return None

    # Set optional value
    if value:
        session.kv[key] = value

    return locker_session_id


def lock_entity(entity, session):
    key = _get_entity_mutex_key(entity)
    locker_session_id = lock_key(key, session)
    if not locker_session_id:
        return None, None
    kv_backup = get_nested_dict(session.kv.find(entity + '/'))

    return locker_session_id, kv_backup


def unlock_entity(entity, locker_session_id, session):
    mutex = _get_entity_mutex_key(entity)
    del session.kv[mutex]
    session.session.destroy(locker_session_id)


def get_flat_dict(hierarchy, kv=None, k1=''):
    """
    Get a flat dictionary from a nested one for its use with Consul
    """
    if not kv:
        kv = {}

    for k2, v2 in hierarchy.items():
        if type(v2) is dict:
            rk1 = k2
            if k1:
                rk1 = k1 + '/' + rk1
            kv = get_flat_dict(v2, kv=kv, k1=rk1)
        else:
            kv[k1 + '/' + k2] = v2
    return kv


def get_nested_dict(kv):
    """
    Get a nested dictionary from a consul flat one
    """
    new_dict = {}
    for key, value in kv.items():
        current_level = new_dict
        # Leaf node
        if key[-1] != '/':
            segments = key.split('/')
            last = segments.pop()
            for segment in segments:
                if segment not in current_level:
                    current_level[segment] = {}
                current_level = current_level[segment]
            current_level[last] = value
    return new_dict
