#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from services import containers, node
import docker
import consulate as consul
from helpers import consul as consul_helper
from conf import conf_loader as conf
from errors.consul import LockError
import logging
import time
import random

logging.getLogger().setLevel(logging.INFO)

app = Flask(__name__)
api = Api(app)

docker_low_level_client = docker.APIClient(base_url='unix://run/docker.sock',
                                           version='auto')

docker_client = docker.DockerClient(base_url='unix://run/docker.sock',
                                    version='auto')

consul_session = consul.Consul(host=conf.consul['bind_address'],
                               port=conf.consul['port'])

# Register the current worker node in Consul
entity = 'nodes'

i = 0
mutex = None
while not mutex:
    if i == 10:
        raise NodeRegistrationError("Could not lock nodes data.")
    if i > 0:
        logging.info("Could not lock nodes data (" + str(i) + "). Retrying...")
        time.sleep(random.randint(1, 5))
    mutex, nodes_kv_backup = consul_helper.lock_entity(entity, consul_session)

try:
    node_name = consul_helper.register_node(conf.worker, consul_session)
except (NotImplementedError, ValueError) as e:
    logging.exception("Exception registering the node.")
    consul_helper.restore_kv_backup(nodes_kv_backup, consul_session)
finally:
    consul_helper.unlock_entity(entity, mutex, consul_session)

kwargs = {'node_name': node_name,
          'docker_low_level_client': docker_low_level_client,
          'docker_client': docker_client,
          'consul_session': consul_session}

ancoris_conf = conf.worker['ancoris']

api.add_resource(node.Node,
    ancoris_conf['base_url'] + '/node',
    resource_class_kwargs=kwargs)

api.add_resource(containers.Containers,
    ancoris_conf['base_url'] + '/containers',
    resource_class_kwargs=kwargs)

api.add_resource(containers.Container,
    ancoris_conf['base_url'] + '/containers/<container_name>',
    resource_class_kwargs=kwargs)

api.add_resource(containers.ContainerStatus,
    ancoris_conf['base_url'] + '/containers/<container_name>/status',
    resource_class_kwargs=kwargs)

api.add_resource(containers.ContainerLogs,
    ancoris_conf['base_url'] + '/containers/<container_name>/logs',
    resource_class_kwargs=kwargs)

if __name__ == '__main__':
    app.run(host=ancoris_conf['bind_address'],
            port=ancoris_conf['port'])
