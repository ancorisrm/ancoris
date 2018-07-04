#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO GESTIONAR CLIENTES CONSUL/DOCKER REINSTANCIAR ANTE ERROR

import yaml
import logging
from flask import Flask, request, Response
from flask_restful import Resource
import docker
import consulate as consul
from helpers import docker as docker_helper
from helpers import volumes as volumes_helper
from helpers import consul as consul_helper
from conf import conf_loader as conf
from errors.volumes import (
    MountVolumeError,
    CreateVolumeError,
)
from errors.docker import ContainerError
import time


dfs_list = ['glusterfs']
logging.getLogger().setLevel(logging.INFO)

def load_kwargs(instance, kwargs):
    instance.node_name = kwargs['node_name']
    instance.consul_session = kwargs['consul_session']
    instance.docker_client = kwargs['docker_client']
    instance.docker_low_level_client = kwargs['docker_low_level_client']

class Container(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs)

    def delete(self, container_name):
        """
        Delete a Docker container if it exists (docker kill)
        """
        if not docker_helper.exists_container(container_name,
                                              self.docker_low_level_client):
            return None, 404
        try:
            docker_helper.rm_container(container_name, self.docker_low_level_client)
        except ContainerError as e:
            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

        return Response(status=204)

class Containers(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs)

    def post(self):
        data = request.get_json(force=True)

        resources = data['resources']
        volumes = resources['volumes']

        # TODO MATAR CONTENEDOR Y LIMPIAR DIRECTORIOS EN CASO DE FALLO
        # TODO DEVOLVER LOS DATOS DEL CONTENEDOR

        # if not consul_helper.use_resources(self.node_name, data, self.consul_session):
        #    return {'error': 'Could not allocate the requested resources.'}, 500

        if not 'events' in data:
            data['events'] = {}
        if not 'on_exit' in data['events']:
            data['events']['on_exit'] = {}

        ## Mandatory parameters for creating a volume
        # - id (volume id)
        # - type (disk type)
        # - device (disk device id)
        # - size (size of the volume)

        shared_volumes_path = consul_helper.get_node_shared_volumes_path(
            self.node_name,
            self.consul_session)

        if volumes:
            for volume in volumes:
                volume['host_path'] = volume['disk_path'] + '/' + volume['id'] \
                    + '/mount-point'

                volume['group_path'] = volume['disk_path'] + '/' + data['group']

                # TODO comprobar existencia de volúmenes en GlusterFS,
                # y pasarlos a local

                volume_exists = volumes_helper.exists(volume['disk_path'],
                                                             volume['id'])

                # Avoid real volumes for distributed filesystems
                if volume['type'] not in dfs_list:
                    volume_mounted = volumes_helper.is_mounted(volume['disk_path'],
                                                                      volume['id'])
                    # Create the volume only if it does not exist
                    if not volume_exists:
                        # Create the volume
                        try:
                            volumes_helper.create_volume(volume['disk_path'],
                                                         volume['id'],
                                                         volume['size'])
                            time.sleep(1)
                        except CreateVolumeError as e:
                            # Internal Server Error
                            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

                    # Mount the volume if it is not already mounted
                    if not volume_mounted:
                        # Mount the volume
                        try:
                            volume_mode = consul_helper.get_volume_mode(
                                volume['id'],
                                self.consul_session)
                            volume_mode = volume_mode.split('-')
                            volume_group_mode = None
                            if len(volume_mode) == 2:
                                volume_group_mode = volume_mode[1]

                            volumes_helper.mount_volume(volume['disk_path'],
                                                        volume['id'],
                                                        volume_groups=volume['groups'],
                                                        volume_group_mode=volume_group_mode,
                                                        shared_volumes_path=shared_volumes_path,
                                                        mode=volume['mode'],
                                                        tmpfs=(volume['type']=='tmpfs'))
                        except MountVolumeError as e:
                            # Internal Server Error
                            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

            # Add the shared path to the volumes array so it will be mapped
            # by Docker
            for volume_group in volume['groups']:
                volumes.append({
                    'host_path': shared_volumes_path + '/' + volume_group,
                    'bind_path': '/mnt/' + volume_group,
                    'mode': 'rw'
                })

        # Calc the number of cores to be used in the current machine
        # with respect to the given number of vCores
        cpu_normalizer = consul_helper.get_node_cpus_normalizer(
            self.node_name,
            self.consul_session)
        cores = cpu_normalizer * resources['cores']

        # Add default Docker image version
        if len(data['image'].split(':')) == 1:
            data['image'] += ':latest'

        # Launch the container
        try:
            docker_helper.run_container(
            data['image'],
            data['task_id'],
            self.docker_client,
            args=data.get('args'),
            environment=data.get('environment'),
            cores=cores,
            memory=resources['memory'],
            swap=resources.get('swap'),
            swappiness=data.get('opts').get('swappiness'),
            volumes=volumes,
            ports=resources.get('ports'),
            devices=data.get('devices'),
            task_id=data['task_id'],
            group_id=data['group'],
            network_mode=data.get('opts').get('network_mode'),
            auto_remove=data['events']['on_exit'].get('destroy'),
            auto_restart=data['events']['on_exit'].get('restart'))
        except ContainerError as e:
            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

        # Register the service with its healthcheck
        try:
            consul_helper.register_service(
            data['task_id'],
            self.consul_session,
            self._get_health_endpoint(data['task_id']),
            interval='5s')
        except ServiceRegistrationError as e:
            # Internal Server Error (Can't register service)
            return {'error': f'{type(e).__name__}: {str(e)}'}, 500

        response = { 'ports':
            docker_helper.get_container_port_mappings(
                data['task_id'],
                self.docker_low_level_client) }

        return response, 200

    def _get_health_endpoint(self, container_name):
        address = consul_helper.get_node_address(self.node_name, self.consul_session)
        port = consul_helper.get_node_port(self.node_name, self.consul_session)
        return 'http://' + address + ':' + port + '/api/v1.0/containers/' \
            + container_name + '/status'

class ContainerStatus(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs=kwargs)

    def get(self, container_name):
        try:
            status = docker_helper.get_container_status(
                container_name,
                self.docker_low_level_client)

            http_code = 200
            if status == 'removing' or \
                status == 'paused' or \
                status == 'exited' or \
                status == 'dead':
                http_code = 410 # Gone
            return {'status': status}, http_code
        except ContainerError:
            return None, 404

class ContainerLogs(Resource):
    def __init__(self, **kwargs):
        load_kwargs(self, kwargs=kwargs)

    def get(self, container_name):
        logs = docker_helper.get_container_logs(
            container_name,
            self.docker_low_level_client)
        if logs:
            return {'logs': logs}, 200
        return None, 404
