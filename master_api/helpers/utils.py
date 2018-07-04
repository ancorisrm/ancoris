#!/usr/bin/python
# -*- coding: utf-8 -*-

import humanfriendly
import math


def get_mib(input):
    input = str(input)
    input_digits = 0
    integer_input = ""
    for c in input:
        try:
            int(c)
            integer_input += c
            input_digits += 1
        except ValueError:
            break

    output = input
    num_bytes = humanfriendly.parse_size(input)

    # Same number of digits => interpreted bytes but MiB by default
    if input_digits == len(str(num_bytes)):
        output = integer_input
    else:
        output = num_bytes / 1048576 # MiB

    return math.ceil(float(output))
