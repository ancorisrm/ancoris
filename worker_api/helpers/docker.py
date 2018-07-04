#!/usr/bin/python
# -*- coding: utf-8 -*-

import docker
import logging
from errors.docker import ContainerError


logging.getLogger().setLevel(logging.INFO)

def stop_all_containers(low_level_client):
    try:
        containers = low_level_client.containers(
            all=True,
            filters={'name': 'task_'})
        for container in containers:
            low_level_client.stop(container['Id'], timeout=0)
    except docker.errors.APIError as e:
        raise ContainerError('Error launching the container: '
        + container_name + '. ' + str(e))

def stop_container(container_name, low_level_client):
    try:
        low_level_client.stop(container_name, timeout=0)
    except docker.errors.APIError as e:
        raise ContainerError('Error stopping the container: '
        + container_name + '. ' + str(e))

def rm_container(container_name, low_level_client):
    try:
        low_level_client.kill(container_name)
    except docker.errors.APIError as e:
        raise ContainerError('Error killing the container: '
        + container_name + '. ' + str(e))

def exists_container(container_name, low_level_client):
    try:
        if _get_container_info(container_name, low_level_client):
            return True
        return False
    except ContainerError:
        raise

def _get_container_info(container_name, low_level_client):
    """
    Returns the available information for an existing container
    which matches exactly the given name.
    """
    try:
        containers_info = low_level_client.containers(
            all=True,
            filters={'name': container_name})
        for container_info in containers_info:
            for name in container_info['Names']:
                if '/' + container_name == name:
                    return container_info
    except (IndexError, docker.errors.APIError) as e:
        raise ContainerError('Error retrieving information about the container: '
        + container_name + '. ' + str(e))

def get_container_port_mappings(container_name, low_level_client):
    # TODO TCP / UDP, MULTI IP?
    """
    Returns the list of port mappings of a given container
    """
    container_info = _get_container_info(container_name, low_level_client)
    if container_info:
        ports = container_info['Ports']
        mappings = []
        for port in ports:
            if 'PublicPort' in port:
                mappings.append({ 'container': port['PrivatePort'],
                                  'host': port['PublicPort'] })
        return mappings
    raise ContainerError('Error retrieving the port mappings of the container: '
    + container_name)

def get_container_status(container_name, low_level_client):
    """
    Returns the current status of a given container
    [CREATED, RESTARTING, RUNNING, REMOVING, PAUSED, EXITED, DEAD]
    """
    container_info = _get_container_info(container_name, low_level_client)
    if container_info:
        return container_info['State']
    raise ContainerError('Error retrieving the status of the container: '
    + container_name)

def pull_image(image, low_level_client):
    """
    Pull a Docker image
    """
    try:
        low_level_client.pull(image)
    except docker.errors.APIError as e:
        raise ContainerError('Error pulling the image: ' + image
        + '. ' + str(e))

def get_container_logs(container_name, low_level_client):
    """
    Returns the logs of a given container
    """
    try:
        logs =  low_level_client.logs(container_name, stream=False)
        return logs.decode('utf-8')
    except docker.errors.APIError as e:
        raise ContainerError('Error retrieving the logs of the container: '
        + container_name + '. ' + str(e))

# Min cores value: 0.01 (1% of the CPU time of one core)
def run_container(image,
                  name,
                  client,
                  args=None,
                  environment=None,
                  cores=None,
                  memory=None,
                  swap=None,
                  swappiness=None,
                  volumes=None,
                  ports=None,
                  devices=None,
                  execution_id=None,
                  task_id=None,
                  group_id=None,
                  network_disabled=None,
                  network_mode=None,
                  cpu_soft_limit=None,
                  auto_remove=None,
                  auto_restart=None):
    """
    Launch a new container
    """

    if args == None:
        args = ""
    if environment == None:
        environment = {}
    if not cores:
        cores = 1
    if not memory:
        memory = 128
    if not swap:
        swap = 0
    if not swappiness:
        swappiness = 0
    if volumes == None:
        volumes = []
    if ports == None:
        ports = []
    if devices == None:
        devices = []
    if network_disabled == None:
        network_disabled = False
    if cpu_soft_limit == None:
        cpu_soft_limit = True
    if auto_remove == None:
        auto_remove = True
    if auto_restart == None:
        auto_restart = False

    run_opts = {}
    run_opts['image'] = image
    run_opts['name'] = name
    run_opts['command'] = args

    # Memory
    run_opts['mem_limit'] = str(memory) + 'm'
    run_opts['memswap_limit'] = str(int(swap) + int(memory)) + 'm'
    run_opts['mem_swappiness'] = int(swappiness)

    # CPU
    if cpu_soft_limit: # Soft CPU limit
        run_opts['cpu_shares'] = int(float(cores) * 200)

    else: # Hard CPU limit
        run_opts['cpu_period'] = 100000
        run_opts['cpu_quota'] = \
            int(float(cores) * run_opts['cpu_period'])

    # Ports
    if ports:
        run_opts['ports'] = {}
        # The specified ports are mapped to the host machine in a random port
        for port in ports:
            run_opts['ports'][str(port) + '/tcp'] = None

    # Devices
    if devices:
        run_opts['devices'] = []
        for device in devices:
            nvidia_gpu = False
            # https://github.com/NVIDIA/nvidia-docker/wiki/GPU-isolation
            if device['group'] == 'nvidia_gpu':
                # These two devices also have to be mounted
                if not nvidia_gpu:
                    run_opts['devices'].extend([
                        "/dev/nvidia-uvm:/dev/nvidia-uvm:rwm",
                        "/dev/nvidiactl:/dev/nvidiactl:rwm"])
                    nvidia_gpu = True
                # The NVIDIA GPU
                device_path = "/dev/" + device['id']
                run_opts['devices'].append(
                    device_path + ":" + device_path + "rwm")
            else:
                raise UnsupportedDevice('Only Nvidia GPUs supported')

    # Volumes
    if volumes:
        run_opts['volumes'] = {}
        for volume in volumes:
            host_path = volume['host_path']
            run_opts['volumes'][host_path] = {}
            if 'bind_path' in volume:
                run_opts['volumes'][host_path]['bind'] = volume['bind_path']
            else:
                run_opts['volumes'][host_path]['bind'] = '/mnt/' + volume['id']

            if not 'mode' in volume:
                volume['mode'] = 'ro'
            run_opts['volumes'][host_path]['mode'] = volume['mode']

    # Environment variables
    run_opts['environment'] = environment
    run_opts['environment']['TASK_ID'] = task_id
    run_opts['environment']['GROUP_ID'] = group_id

    # Events
    if auto_remove:
        run_opts['remove'] = True

    if auto_restart:
        run_opts['restart_policy'] = {"Name": "always"}

    # Other options
    if network_mode:
        run_opts['network_mode'] = network_mode
    run_opts['network_disabled'] = network_disabled
    run_opts['detach'] = True
    run_opts['stdin_open'] = True # Interactive, run bash without exiting, for instance.
    run_opts['tty'] = True # TTY

    logging.info(run_opts)

    try:
        client.containers.run(**run_opts)
    except docker.errors.APIError as e:
        raise ContainerError('Error launching the container: ' + name
        + ' ' + str(e))
