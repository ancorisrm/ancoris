#!/usr/bin/python
# -*- coding: utf-8 -*-

from helpers import (
    consul as consul_helper,
    utils,
)
from errors.task import (
    TaskResourceAllocationError,
    TaskLaunchError,
    ForbiddenRequirementsError,
)
from errors.consul import (
    InsufficientResourcesError,
    NodeRegistrationError,
)
from errors.volume import (
    VolumeNotFoundError,
    VolumeInputError,
)
import requests
import json
import humanfriendly
import math


def is_less_restrictive(mode_a, mode_b):
    ordered_modes = ['rw', 'ro']
    if not mode_a in ordered_modes or not mode_b in ordered_modes:
        raise ValueError
    if ordered_modes.index(mode_a) < ordered_modes.index(mode_b):
        return True
    else:
        return False


def set_volume_modes(task_id, volumes, session):
    for volume in volumes:
        # Check if the task has the ownership of the volume
        prime_task = consul_helper.get_volume_prime_task_mutex(volume['id'],
                                                               session)

        # Shared mode registered in Consul for the nodes
        consul_modes = consul_helper.get_volume_mode(volume['id'], session)
        consul_modes = consul_modes.split('-')

        # If the volume is not being used or owned by the own task
        if not prime_task or prime_task == task_id:
            consul_selected_mode = consul_modes[0]
        # If the volume is being used by other task
        else:
            try:
                consul_selected_mode = consul_modes[1]
            except IndexError:
                raise ForbiddenRequirementsError('The volume cannot '
                + 'be shared: ' + volume['id'])

        # The volume will be locked to the current task if it cannot
        # be shared or the selected mode is more restrictive than the
        # volume group permission
        # if not prime_task and len(consul_modes) == 1 \
        # or len(consul_modes) == 2 and is_less_restrictive(consul_modes[1], consul_selected_mode):
        #     # Lock the volume
        #     consul_helper.lock_volume(volume['id'],
        #                               task_id,
        #                               session)
        
        # TODO REVISAR
        if not prime_task:
            # Lock the volume
            consul_helper.lock_volume(volume['id'],
                                      task_id,
                                      session)

        # The given mode only applies if the volume can be shared (the
        # exception was not raised) and the given mode is more
        # restrictive than the assigned one in Consul (ro)
        if 'mode' in volume:
            if volume['mode'] == 'ro':
                continue

        volume['mode'] = consul_selected_mode


def valid_single_volume_input(volume, session, new_volume=True):
    # Volume modes
    shared_modes = ['rw', 'ro', 'rw-rw', 'rw-ro', 'ro-ro', 'ro-rw']
    modes = ['rw', 'ro']

    # Volume types
    volume_types = ['hdd', 'sdd', 'glusterfs']

    # Unrecognized options
    available_opts = {'id', 'groups', 'type', 'size', 'mode', 'path'}
    if set(volume.keys()) - available_opts:
        raise VolumeInputError('')

    # volume['groups'] must be a list
    if 'groups' in volume:
        if type(volume['groups']) is not list:
            raise VolumeInputError('Volume groups have to be specified as a list.')

    # Normalize volume size
    if 'size' in volume:
        volume['size'] = utils.get_mib(volume['size'])

    # Default mount / shared mode
    if not 'mode' in volume:
        volume['mode'] = 'ro'

    # NEW VOLUMES - special cases
    if new_volume:
        if not 'type' in volume:
            raise VolumeInputError('Volume type has to be specified for new volumes.')
        # Mandatory size
        if not 'size' in volume:
            raise VolumeInputError('Size has to be specified for new volumes.')

        # Check shared modes - modes which lock the void volume for everyone
        if volume['mode'] not in set(shared_modes) - set(['ro', 'ro-ro']):
            raise VolumeInputError('Unknown shared mode.')

        # New volumes can't have an identifier
        if 'id' in volume:
            raise VolumeInputError('Identifiers are assigned automatically.')

    # ALREADY EXISTING VOLUMES - special cases
    else:
        if not consul_helper.exists_volume(volume['id'], session):
            raise VolumeNotFoundError(volume['id'])

        # Check mount mode
        if volume['mode'] not in modes:
            raise VolumeInputError('Unknown mount mode.')

        if not 'size' in volume:
            try:
                volume['size'] = consul_helper.get_volume_size(volume['id'],
                                                               session)
            except KeyError as e:
                raise VolumeInputError(f"There is not a default type for the volume: {volume['id']}")


        # Volumes must have a type (explicit or default)
        if not 'type' in volume:
            try:
                volume['type'] = consul_helper.get_volume_type(volume['id'],
                                                               session)
            except KeyError as e:
                raise VolumeInputError(f"There is not a default type for the volume: {volume['id']}")
