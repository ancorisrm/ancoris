if not volume['bind_path']:
        volume['bind_path'] = '/mnt/' + volume['id']

tmpfs = False
if volume['type'] == 'tmpfs':
    tmpfs = True

disk_path = conf.worker['resources']['devices'] \
                    [volume['type']]
if tmpfs:
    disk_path = disk_path['path']
else:
    disk_path = disk_path[volume['device']]['path']
