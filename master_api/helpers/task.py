#!/usr/bin/python
# -*- coding: utf-8 -*-

from helpers import (
    consul as consul_helper,
    volume as volume_helper,
    utils,
)
from errors.task import (
    TaskResourceAllocationError,
    TaskLaunchError,
    ForbiddenRequirementsError,
    TaskInputError,
    TaskDeleteError,
)
from errors.consul import (
    InsufficientResourcesError,
)
from errors.volume import (
    VolumeInputError,
    VolumeNotFoundError,
)
import requests
from requests.exceptions import RequestException
import json


def _get_worker_error_message(message, response=None, request=None):
    if response != None:
        message += ' Worker response: ' + str(response.content).strip()
    if request != None:
        message += ' Sent payload: ' + json.dumps(request)
    return message

def post_container_worker(data, worker_info):
    try:
        url = f"http://{worker_info['address']}:{worker_info['port']}{worker_info['base_url']}/containers"
        # Worker call
        response = requests.post(url, data=json.dumps(data))
        if response.status_code != 200:
            raise TaskLaunchError(_get_worker_error_message('Error launching the container',
                                                            response=response,
                                                            request=data))
        if response.content:
            return response.json()
    except RequestException as e:
        raise TaskLaunchError(_get_worker_error_message(str(e) + ' Error deleting the container',
                                                        request=data))

def delete_container_worker(task_id, worker_info):
    try:
        url = f"http://{worker_info['address']}:{worker_info['port']}{worker_info['base_url']}/containers/{task_id}"
        # Worker call
        response = requests.delete(url)
        print(response.status_code)
        if response.status_code != 204:
            raise TaskDeleteError(_get_worker_error_message('Error deleting the container',
                                                            response=response),
                                  response.status_code)
        if response.content:
            return response.json()
    except RequestException as e:
        raise TaskDeleteError(_get_worker_error_message(str(e) + ' Error deleting the container'))

def get_post_container_request_data(input_data, volumes):
    # TODO FUNCIÓN INTERMEDIA
    data = {}
    data['task_id'] = input_data['task_id']
    data['group'] = input_data['group']
    data['image'] = input_data['image']

    if 'args' in input_data:
        data['args'] = input_data['args']

    if 'environment' in input_data:
        data['environment'] = input_data['environment']

    data['resources'] = {}
    data['resources']['cores'] = input_data['resources']['cores']
    data['resources']['memory'] = input_data['resources']['memory']
    data['resources']['swap'] = input_data['resources']['swap']

    data['resources']['ports'] = []
    for port in input_data['resources']['ports']:
        data['resources']['ports'].append(port)

    data['resources']['volumes'] = []
    for volume in volumes:
        data['resources']['volumes'].append({
            'id': volume['id'],
            # Retrieve the group from Consul
            'groups': volume['groups'],
            'bind_path': volume['bind_path'],
            'disk_path': volume['path'],
            'size': volume['size'],
            'type': volume['type'],
            'mode': volume['mode']})

    # TODO COPIA PROFUNDA
    data['opts'] = input_data['opts']
    data['events'] = input_data['events']

    return data


def get_post_task_response_data(input_data,
                                worker_response,
                                volumes,
                                worker_address,
                                worker_name):
    data = {}
    data['id'] = input_data['task_id']
    data['host'] = worker_address
    data['node'] = worker_name
    data['group'] = input_data['group']
    data['image'] = input_data['image']

    if 'args' in input_data:
        data['args'] = input_data['args']

    if 'environment' in input_data:
        data['environment'] = input_data['environment']

    data['resources'] = {}
    data['resources']['cores'] = input_data['resources']['cores']
    data['resources']['memory'] = input_data['resources']['memory']
    data['resources']['swap'] = input_data['resources']['swap']

    data['resources']['ports'] = worker_response['ports']

    data['resources']['volumes'] = []
    for volume in volumes:
        data['resources']['volumes'].append({
            'id': volume['id'],
            'groups': volume['groups'],
            'path': volume['bind_path'],
            'size': volume['size'],
            'type': volume['type'],
            'mode': volume['mode']})

    # TODO COPIA PROFUNDA
    data['opts'] = input_data['opts']
    data['events'] = input_data['events']

    return data


def valid_volumes_input(volumes, session):
    if volumes == None:
        raise VolumeInputError('Void volumes array')

    for volume in volumes:
        new_volume = not 'id' in volume
        # Exceptions
        volume_helper.valid_single_volume_input(volume,
                                                session,
                                                new_volume)


def valid_post_input(data, session):
    if not 'image' in data:
        raise TaskInputError('Docker image is a mandatory parameter. ')

    if not 'resources' in data:
        raise TaskInputError('You must specify basic resources.')

    if not 'cores' in data['resources']:
        raise TaskInputError('No. of cores is a mandatory parameter.')
    data['resources']['cores'] = int(data['resources']['cores'])

    if not 'memory' in data['resources']:
        raise TaskInputError('Memory is a mandatory parameter.')

    data['resources']['memory'] = utils.get_mib(data['resources']['memory'])

    if 'ports' in data['resources']:
        for port in data['resources']['ports']:
            if type(port) is not int:
                raise TaskInputError('Port numbers have to be integers.')

    if 'args' in data and type(data['args']) != list:
        raise TaskInputError('Arguments have to be specified as a list.')

    if 'environment' in data and type(data['environment']) != dict:
        raise TaskInputError(
            'Environment variables have to be specified as dictionary.')

    if 'volumes' in data['resources']:
        # VolumeNotFoundError is not catched
        try:
            valid_volumes_input(data['resources']['volumes'], session)
        except VolumeInputError as e:
            raise TaskInputError(str(e))

    # TODO check values of the options
    if 'opts' in data:
        available_opts = ['swappiness', 'replicas', 'prefered_hosts', 'network_mode']
        for opt in data['opts'].keys():
            if opt not in available_opts:
                raise TaskInputError('Unknown option.')

    if 'events' in data:
        booleans = [True, False]
        available_events = {
            'on_exit': {
                'restart': booleans,
                'destroy': booleans
            }
        }

        for key in data['events'].keys():
            if key not in available_events.keys():
                raise TaskInputError('Unknown event.')
            for key2 in data['events'][key]:
                if key2 not in available_events[key].keys():
                    raise TaskInputError('Event action not valid.')
                if data['events'][key][key2] not in available_events[key][key2]:
                    raise TaskInputError('Event action with unknown value')

node_names_index = 0
def _get_node_sequence(prefered_hosts, session):
    """
    Returns a sequence of ordered nodes given a parcial prefered order
    """
    global node_names_index
    node_names = consul_helper.get_node_names(session)

    # Create a sequence with all the available nodes.
    # Add first the user selected nodes if valid
    sequence = []
    for node_name in prefered_hosts:
        if node_name in node_names:
            sequence.append(node_name)

    sequence.append(node_names[node_names_index])
    node_names_index = (node_names_index + 1) % len(node_names)

    # Append the rest of the nodes
    for node_name in node_names:
        if node_name not in sequence:
            sequence.append(node_name)

    return sequence


def reserve_task_resources(data, prefered_hosts, session):
    task_id = data['task_id']
    resources = data['resources']

    if not 'group' in data:
        data['group'] = consul_helper.get_task_group_id(task_id)

    volumes = resources['volumes']
    if 'volumes' in resources:
        for volume in volumes:
            # Assign the task group as the volume group if not given
            if not 'groups' in volume:
                volume['groups'] = [data['group']]

            # Register the volume only if it does not exist (ID not present)
            if not 'id' in volume:
                # volume_id and group_id are added if not present
                consul_helper.register_volume(volume,
                                              session,
                                              task_id=task_id)
            # Retrieve the volume group from Consul if the volume exists
            else:
                volume['groups'] = consul_helper.get_volume_groups(volume['id'],
                                                                   session)

    sequence = _get_node_sequence(prefered_hosts, session)

    # Looking for a valid node in sequence
    selected_node = None
    volumes_assignments = None

    for node_name in sequence:
        insufficient_resources = False
        try:
            volumes_assignments = consul_helper.use_task_resources(
                node_name,
                resources,
                session)
            selected_node = node_name
            break
        except InsufficientResourcesError as e:
            pass

    if not selected_node:
        raise TaskResourceAllocationError(
            "Could not reserve resources for the task.")

    final_volumes = []
    for volume in volumes:
        if 'path' in volume:
            volume['bind_path'] = volume['path']
        else:
            volume['bind_path'] = '/mnt/' + volume['id']

        final_volumes.append({
            'id': volume['id'],
            'path': consul_helper.get_disk_path(
                selected_node,
                volumes_assignments[volume['id']]['type'],
                volumes_assignments[volume['id']]['disk_id'],
                session),
            'size': volume['size'],
            'type': volume['type'],
            'mode': volume['mode'],
            'bind_path': volume['bind_path'],
            'groups': volume['groups']})

    return selected_node, final_volumes
