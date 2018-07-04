#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import json
from flask import Flask, request
from flask_restful import Resource
from helpers import volume as volume_helper
from helpers import consul as consul_helper
from errors.consul import (
    InsufficientResourcesError,
    LockError,
)
from errors.volume import (
    VolumeInputError,
    VolumeNotFoundError,
)
import samples

def load_kwargs(instance, kwargs):
    instance.consul_session = kwargs['consul_session']

class Volumes(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs)

    def release_volumes_lock(self, volumes_locker_session_id):
        consul_helper.unlock_entity('volumes',
                                    volumes_locker_session_id,
                                    self.consul_session)
    def post(self):
        try:
            try:
                volume = request.get_json(force=True)
            except json.decoder.JSONDecodeError:
                return {'error', 'Bad JSON format'}, 400

            # Lock volumes in Consul
            volumes_locker_session_id, _ = \
                consul_helper.lock_volumes(self.consul_session)

            # Mandatory: volume info
            try:
                volume_helper.valid_single_volume_input(volume,
                                                        self.consul_session,
                                                        new_volume=True)
            except VolumeInputError as e:
                self.release_volumes_lock(volumes_locker_session_id)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 400

            # Register volume
            consul_helper.register_volume(volume, self.consul_session)

        except Exception as e:
            self.release_volumes_lock(volumes_locker_session_id)
            import traceback
            traceback.print_exc()
            return None, 500

        self.release_volumes_lock(volumes_locker_session_id)
        return volume, 201
