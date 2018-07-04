#!/usr/bin/env python
# -*- coding: utf-8 -*-

post_task_response = {
  "id": "task_1502089751_1",
  "group": "group_1502089751_1",
  "image": "ancoris/centos:7.3",
  "host": "node1",
  "resources": {
    "cores": 1,
    "memory": 128,
    "swap": 0,
    "volumes": [
      {
        "id": "volume_1502089751_1",
        "group": "group_1502089751_1",
        "path": "/mnt/volume_1502089751_1",
        "size": 1024,
        "type": "hdd",
        "mode": "rw-ro"
      }
    ],
    "ports": [
      {
        "container": 80,
        "host": 32000
      }
    ],
    "devices": [
      {
        "id": "nvidia0",
        "group": "nvidia_gpu",
        "model": "GTX 1080 Ti 8GB"
      }
    ]
  },
  "opts": {
    "swappiness": 0
  },
  "events": {
    "on_exit": {
      "restart": False,
      "destroy": True
    }
  },
  "status": "SUBMITTED",
  "completion": 0.25
}

get_task_response = [
  {
    "id": "task_1502089751_1",
    "group": "group_1502089751_1",
    "image": "ancoris/centos:7.3",
    "host": "node1",
    "resources": {
      "cores": 1,
      "memory": 128,
      "swap": 0,
      "volumes": [
        {
          "id": "volume_1502089751_1",
          "group": "group_1502089751_1",
          "path": "/mnt/volume_1502089751_1",
          "size": 1024,
          "type": "hdd",
          "mode": "rw-ro"
        }
      ],
      "ports": [
        {
          "container": 80,
          "host": 32000
        }
      ],
      "devices": [
        {
          "id": "nvidia0",
          "group": "nvidia_gpu",
          "model": "GTX 1080 Ti 8GB"
        }
      ]
    },
    "opts": {
      "swappiness": 0
    },
    "events": {
      "on_exit": {
        "restart": False,
        "destroy": True
      }
    },
    "status": "SUBMITTED",
    "completion": 0.25
  }
]

get_task_status = {
  "status": "RUNNING"
}
