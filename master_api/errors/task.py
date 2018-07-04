#!/usr/bin/python
# -*- coding: utf-8 -*-

class TaskResourceAllocationError(Exception):
    pass

class TaskLaunchError(Exception):
    def __init__(self, message, http_code=None):
        super(TaskLaunchError, self).__init__(message)
        if http_code:
            self.http_code = http_code

class TaskDeleteError(Exception):
    def __init__(self, message, http_code=None):
        super(TaskDeleteError, self).__init__(message)
        if http_code:
            self.http_code = http_code

class ForbiddenRequirementsError(Exception):
    pass

class TaskInputError(Exception):
    pass
