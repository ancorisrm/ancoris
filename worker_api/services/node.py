#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, Response
from flask_restful import Resource
import consulate as consul
from helpers import consul as consul_helper
from helpers import docker as docker_helper
from conf import conf_loader as conf

class Node(Resource):
    def __init__(self, **kwargs):
        self.node_name = kwargs['node_name']
        self.consul_session = kwargs['consul_session']
        self.docker_client = kwargs['docker_client']
        self.docker_low_level_client = kwargs['docker_low_level_client']

    def delete(self):
        consul_helper.deregister_node(self.node_name, self.consul_session)
        docker_helper.stop_all_containers(self.docker_low_level_client)
        return Response(status=204) # No content
