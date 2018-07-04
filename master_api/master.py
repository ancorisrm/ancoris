#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
from flask import Flask
import consulate as consul
from flask_restful import reqparse, abort, Api, Resource
from conf import conf_loader as conf
from services import (
    tasks,
    volumes,
    meta,
)

app = Flask(__name__)
api = Api(app)


consul_session = consul.Consul(host=conf.consul['bind_address'],
                               port=conf.consul['port'])


kwargs = {'consul_session': consul_session}


# TASKS
api.add_resource(tasks.Tasks, conf.master['base_url'] + '/tasks',
    resource_class_kwargs=kwargs)

api.add_resource(tasks.Task, conf.master['base_url'] + '/tasks/<task_id>',
    resource_class_kwargs=kwargs)

api.add_resource(tasks.TaskStatus, conf.master['base_url'] + '/tasks/<task_id>/status',
    resource_class_kwargs=kwargs)


# VOLUMES
api.add_resource(volumes.Volumes, conf.master['base_url'] + '/volumes',
    resource_class_kwargs=kwargs)

# META
api.add_resource(meta.Meta, conf.master['base_url'] + '/status')


if __name__ == '__main__':
    app.run(host=conf.master['bind_address'],
            port=conf.master['port'])
