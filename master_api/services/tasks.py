#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import json
from flask import Flask, request, Response
from flask_restful import Resource
from helpers import (
    consul as consul_helper,
    volume as volume_helper,
    task as task_helper,
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
    LockError,
)
from errors.volume import (
    VolumeNotFoundError,
)
import samples


def load_kwargs(instance, kwargs):
    instance.consul_session = kwargs['consul_session']


class Tasks(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs)

    def _release_entities(self, restore_data):
        for entity, mutex_backup in restore_data.items():
            consul_helper.unlock_entity(entity,
                                        mutex_backup[0],
                                        self.consul_session)

    def _restore_release_kv(self, entity, mutex, backup):
        consul_helper.restore_kv_backup(backup, self.consul_session)
        consul_helper.unlock_entity(entity, mutex, self.consul_session)

    def _restore_release_kv_many(self, restore_data):
        for entity, mutex_backup in restore_data.items():
            self._restore_release_kv(entity, mutex_backup[0], mutex_backup[1])

    def post(self):
        try:
            try:
                data = request.get_json(force=True)
            except json.decoder.JSONDecodeError:
                return {'error', 'Bad JSON format'}, 400

            # Lock Consul
            restore_data = consul_helper.lock_all(self.consul_session)

            # Mandatory: image, cores, memory
            try:
                task_helper.valid_post_input(data, self.consul_session)
            except VolumeNotFoundError as e:
                self._restore_release_kv_many(restore_data)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 404
            except TaskInputError as e:
                self._restore_release_kv_many(restore_data)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 400

            data['task_id'] = consul_helper.get_new_task_id(
                self.consul_session)
            if not 'group' in data:
                data['group'] = consul_helper.get_task_group_id(
                    data['task_id'])

            prefered_hosts = []
            # Ver lo que me pide
            if 'opts' in data:
                if 'prefered_hosts' in data['opts']:
                    prefered_hosts = data['opts']['prefered_hosts']

            # Reserve resources
            try:
                # Node selection based on user preferences
                selected_node, volumes = task_helper.reserve_task_resources(
                    data,
                    prefered_hosts,
                    self.consul_session)
            except (TaskResourceAllocationError, KeyError) as e:
                self._restore_release_kv_many(restore_data)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 500

            # Set the volume mount modes for the worker
            try:
                volume_helper.set_volume_modes(data['task_id'],
                                               volumes,
                                               self.consul_session)
            except ForbiddenRequirementsError as e:
                self._restore_release_kv_many(restore_data)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 403

            # Launch container
            post_container_request_data = \
                task_helper.get_post_container_request_data(data, volumes)

            worker_info = consul_helper.get_node_info(
                selected_node, self.consul_session)

            try:
                worker_response = task_helper.post_container_worker(
                    post_container_request_data,
                    worker_info)
            except TaskLaunchError as e:
                self._restore_release_kv_many(restore_data)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 500

            # Register task
            post_task_response_data = \
                task_helper.get_post_task_response_data(data,
                                                        worker_response,
                                                        volumes,
                                                        worker_info['address'],
                                                        selected_node)
            try:
                consul_helper.register_task(
                    data['task_id'],
                    post_task_response_data,
                    data['group'],
                    self.consul_session)
            except Exception as e:
                self._restore_release_kv_many(restore_data)
                return {'error': f'{type(e).__name__}: {str(e)}'}, 500

        except Exception as e:
            if 'restore_data' in locals():
                self._restore_release_kv_many(restore_data)
            import traceback
            traceback.print_exc()
            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

        self._release_entities(restore_data)
        return post_task_response_data, 201


class Task(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs)

    def get(self, task_id):
        return samples.get_task_response, 200

    def delete(self, task_id):
        try:
            try:
                task_node = consul_helper.get_task_node(task_id,
                                                        self.consul_session)
                worker_info = consul_helper.get_node_info(task_node,
                                                          self.consul_session)
            except KeyError:
                return None, 404

            try:
                worker_response = task_helper.delete_container_worker(task_id,
                                                                      worker_info)
            except TaskDeleteError as e:
                return {'error': f'{type(e).__name__}: {str(e)}'}, e.http_code

        except Exception as e:
            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

        return Response(status=204)


class TaskStatus(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs)

    def get(self, task_id):
        return samples.get_task_status, 200
