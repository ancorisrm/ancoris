#!/usr/bin/python
# -*- coding: utf-8 -*-

class LockError(Exception):
    pass

class NodeRegistrationError(Exception):
    pass

class NodeDeregistrationError(Exception):
    pass

class ServiceRegistrationError(Exception):
    pass
