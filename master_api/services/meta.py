#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_restful import Resource
from flask import Response

class Meta(Resource):
    def __init__(self, **kwargs):
        pass

    def get(self):
        return Response(status=204)
