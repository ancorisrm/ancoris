#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
from helpers.consul_common import *
import json
import copy
from errors.consul import (
    InsufficientResourcesError,
    NodeRegistrationError,
    LockError,
)

dfs_list = ['glusterfs']

################################################################################

def get_disk_path(node, device_type, device_id, session):
    key = 'nodes/' + node + '/resources/devices/' + device_type
    if device_id:
        key +=  '/' + device_id
    key += '/path'
    return get_single_value(key, session)

def get_timestamp_millis():
    return int(datetime.datetime.today().timestamp())

def get_timestamp_seconds():
    return int(get_timestamp_millis() / 1000)

def get_date():
    return datetime.datetime.today().strftime('%d%m%y')

def get_new_entity_id(entity, session, is_group=False):
    date = get_date()
    key = entity + '/'

    prefix = entity[:-1]
    if is_group:
        prefix += '_group'

    partial_kv = get_nested_dict(session.kv.find(key))
    index = 0
    if partial_kv:
        if is_group:
            sublevel = 'groups'
            underscore_index = 2
        else:
            sublevel = 'all'
            underscore_index = 1

        for key in partial_kv[entity][sublevel].keys():
            if key.split('_')[underscore_index] == date:
                index += 1

    return f"{prefix}_{date}_{index}"

def get_new_task_id(session):
    return get_new_entity_id('tasks', session)

def get_new_volume_id(session):
    return get_new_entity_id('volumes', session)

def get_new_volume_group_id(session):
    return get_new_entity_id('volumes', session, is_group=True)

def get_task_group_id(task_id):
    if task_id:
        return task_id.replace('task_', 'task_group_')

# def get_new_task_group_id(session):
#     return get_new_entity_id('tasks', session, is_group=True)

def _register_entity_instance(entity, item_id, item_data, group_ids, session):
    nested_dict = {entity: {'all': {item_id: item_data}}}

    for group_id in group_ids:
        # Get the previous group volumes
        try:
            group_volumes = json.loads(
                (get_entity_group_items(entity, group_id, session)))
            group_volumes.append(item_id)
        except KeyError:
            group_volumes = [item_id]

        if not 'groups' in nested_dict[entity]:
            nested_dict[entity]['groups'] = {}
        nested_dict[entity]['groups'][group_id] = group_volumes

    flat_dict = get_flat_dict(nested_dict)
    for key, value in flat_dict.items():
        session.kv[key] = value

def register_task(task_id, execution, group_id, session):
    # Substitute the volume dict with a volume list of ids
    # (dictionary COPY)
    execution_copy = copy.deepcopy(execution)
    resources = execution_copy['resources']
    if 'volumes' in resources:
        volume_list = []
        volumes = resources['volumes']
        for volume in volumes:
            volume_list.append(volume['id'])
        execution_copy['resources']['volumes'] = volume_list
    _register_entity_instance('tasks',
                              task_id,
                              execution_copy,
                              [group_id],
                              session)

def register_volume(volume, session, task_id=None):
    """
    Register a new volume in Consul and generate a new ID for it and a
    new volume group for it if necessary. It modifies the volume object.
    """

    entity = 'volumes'
    volume_info = {}
    volume_info['size'] = volume['size']
    volume_info['type'] = volume['type']
    volume_info['mode'] = volume['mode']

    if not 'groups' in volume:
        volume['groups'] = [get_new_volume_group_id(session)]

    volume_info['groups'] = volume['groups']

    if not 'id' in volume:
        volume['id'] = get_new_volume_id(session)

    # Store the task_id (only for task dependent volumes)
    if task_id:
        volume_info['task_id'] = task_id

    _register_entity_instance(entity,
                              volume['id'],
                              volume_info,
                              volume['groups'],
                              session)

def get_workers_info(session):
    return get_nested_dict(get_dict_value('nodes', session))

# TODO
def _unlock_node_device(node, family, model, session):
    pass

# TODO
def _lock_node_device(node, familiy, id, session):
    pass


def free_resources(node, task_id):
    # en el máster
    pass

def use_task_resources(node, resources, session):

    # en el master también
    #self.session.agent.service.deregister(container_name)

    ## Check there are enough resources without modifying the available
    ## resources

    # Enough cores...
    cpu_normalizer = get_node_cpus_normalizer(node, session)
    free_cores = cpu_normalizer * get_node_cpus_cores(node, session)
    if not free_cores or not free_cores >= float(resources['cores']):
        raise InsufficientResourcesError('Insufficient free cores')

    # Enough memory...
    needed_memory_so_far = float(resources['memory'])
    free_memory = get_node_memory_mib(node, session)
    if not free_memory or not free_memory >= float(resources['memory']):
        raise InsufficientResourcesError('Insufficient memory')

    # Enough swap... (optional)
    if resources['swap']:
        free_swap = get_node_swap_mib(node, session)
        if not free_swap or not free_swap >= float(resources['swap']):
            raise InsufficientResourcesError('Insufficient swap')

    # Retrieve the required space and disk types for the volumes
    volumes = resources['volumes']
    required_disk_types = set()
    for volume in volumes:
        if not volume['type'] in required_disk_types \
        and volume['type'] != 'tmpfs':
            required_disk_types.add(volume['type'])

    # Retrieve the available space by compatible disks classified by type
    compatible_disks = {}
    devices_dict = get_nested_dict(get_node_devices(node, session))
    devices_dict = devices_dict['nodes'][node]['resources']['devices']
    for device_type, devices in devices_dict.items():
        # If the device is a compatible disk
        if device_type in required_disk_types:
            compatible_disks[device_type] = []
            for device_id, value in devices.items():
                # The space used by distributed filesystems is not monitored
                if device_type in dfs_list:
                    compatible_disks[device_type].append({ 'id': device_id })
                    continue
                compatible_disks[device_type].append({
                    'id': device_id,
                    'free': value['free'] })

    # Disk assignation to volumes
    volume_assignments = {}
    for volume in volumes:
        if volume['type'] == 'tmpfs':
            needed_memory_so_far += float(volume['size'])

            if not free_memory >= needed_memory_so_far:
                raise InsufficientResourcesError('Insufficient memory (tmpfs)')

            volume_assignments[volume['id']] = {
                'disk_id': None,
                'type': volume['type'],
                'size': volume['size']}
        else:
            for disk_type, disks in compatible_disks.items():
                if volume['type'] == disk_type:
                    for disk in disks:
                        # For distributed filesystems the "disk" is assigned
                        # automatically without taking into account the
                        # available space
                        if disk_type in dfs_list:
                            volume_assignments[volume['id']] = {
                                'disk_id': None,
                                'type': volume['type'],
                            }
                            break # Disk is already selected

                        # Retrieve the volume size from Consul
                        volume['size'] = get_volume_size(volume['id'], session)
                        disk['free'] = float(disk['free'])
                        if volume['size'] <= disk['free']:
                            volume_assignments[volume['id']] = {
                                'disk_id': disk['id'],
                                'type': volume['type'],
                                'size': volume['size']}
                            # For checking during next iterations only
                            disk['free'] = disk['free'] - volume['size']
                            break # Disk is already selected

        # If the assignation is not possible to any volume, return False
        if not volume['id'] in volume_assignments:
            raise InsufficientResourcesError('Insufficient disk space')

    ## Modify the node's available resources
    # CPUs
    sub_node_cpus_free(node, resources['cores'], session)

    # Memory
    sub_node_memory_free(node, needed_memory_so_far, session)

    # Swap
    if resources['swap']:
        sub_node_swap_free(node, resources['swap'], session)

    # Volumes
    for volume_id, value in volume_assignments.items():
        if value['type'] not in ['tmpfs'] + dfs_list:
            sub_node_disk_free(node,
                               value['type'],
                               value['disk_id'],
                               value['size'],
                               session)

    return volume_assignments

    # TODO OTHER DEVICES...
################################################################################

def lock_nodes(session):
    """
    Lock nodes root node
    """
    nodes_locker_session_id, nodes_kv_backup = lock_entity(
        'nodes',
        session)
    if not nodes_locker_session_id:
        raise LockError("Could not lock nodes data.")
    return nodes_locker_session_id, nodes_kv_backup

def lock_volumes(session):
    """
    Lock volumes root node
    """
    volumes_locker_session_id, volumes_kv_backup = lock_entity(
        'volumes',
        session)
    if not volumes_locker_session_id:
        raise LockError("Could not lock volumes data.")
    return volumes_locker_session_id, volumes_kv_backup

def lock_tasks(session):
    """
    Lock tasks root node
    """
    tasks_locker_session_id, tasks_kv_backup = lock_entity(
        'tasks',
        session)
    if not tasks_locker_session_id:
        raise LockError("Could not lock tasks data.")
    return tasks_locker_session_id, tasks_kv_backup

def lock_all(session):
    """
    Lock volumes, nodes and tasks root nodes (entities)
    """
    restore_data = {}

    try:
        nodes_locker_session_id, nodes_kv_backup = lock_nodes(session)
        restore_data['nodes'] = (nodes_locker_session_id, nodes_kv_backup)
    except LockError:
        raise LockError("Could not lock nodes data.")

    try:
        volumes_locker_session_id, volumes_kv_backup = lock_volumes(session)
        restore_data['volumes'] = (volumes_locker_session_id, volumes_kv_backup)
    except LockError:
        # Unlock previous locks
        unlock_entity('nodes',
                      nodes_locker_session_id,
                      session)
        raise LockError("Could not lock volumes data.")

    try:
        tasks_locker_session_id, tasks_kv_backup = lock_tasks(session)
        restore_data['tasks'] = (tasks_locker_session_id, tasks_kv_backup)
    except LockError:
        # Unlock previous locks
        unlock_entity('nodes',
                      nodes_locker_session_id,
                      session)
        unlock_entity('volumes',
                      volumes_locker_session_id,
                      session)
        raise LockError("Could not lock tasks data.")

    return restore_data
