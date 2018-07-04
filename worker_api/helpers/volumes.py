#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import glob
import logging
from errors.volumes import (
    MountVolumeError,
    UmountVolumeError,
    CreateVolumeError,
    ExecCommandError,
)


logging.getLogger().setLevel(logging.INFO)

def _get_volume_path(disk_path, volume_id):
    return disk_path + '/' + volume_id

def exists(disk_path, volume_id):
    volume_path = _get_volume_path(disk_path, volume_id)
    return os.path.exists(volume_path)

def is_mounted(disk_path, volume_id, mount_relative_dir='mount-point'):
    volume_path = _get_volume_path(disk_path, volume_id)
    mount_path = volume_path + '/' + mount_relative_dir
    return os.path.exists(mount_path)

def create_volume(disk_path,
                  volume_id,
                  size,
                  filesystem="ext4"):
    """
    Create and compress a loop device with a filesystem
    """

    # TODO SHA1 DEL TARGZ

    # Size in MiB
    size = int(size)

    if type is "ssd":
        BLOCK_SIZE = 32768 # 32 KiB
    elif type is "hdd":
        BLOCK_SIZE = 131072 # 128 KiB
    else:
        BLOCK_SIZE = 65536 # 64 KiB

    volume_path = _get_volume_path(disk_path, volume_id)

    if not os.path.exists(volume_path):
        os.makedirs(volume_path)

    img_name = volume_id + '.img'
    img_path = volume_path + '/' + img_name

    # Avoid overwriting an existing volume
    targz_path = img_path.replace('.img', '.tar.gz')
    if os.path.exists(targz_path):
        raise CreateVolumeError('It exists a compressed volume with the same ID.')

    success = _exec_cmd(['dd',
                         'if=/dev/zero',
                         'of=' + img_path,
                         'bs=' + str(BLOCK_SIZE),
                         # MiB -> bytes
                         'count=' + str(int(size * 1048576 / BLOCK_SIZE)) ])
    if not success:
        raise CreateVolumeError('Could not create the loop device: ' + volume_id)
    logging.info(success)

    if filesystem == 'ext4':
        mkfs_cmd = 'mkfs.ext4'
    if filesystem == 'ext3':
        mkfs_cmd = 'mkfs.ext3'
    if filesystem == 'xfs':
        mkfs_cmd = 'mkfs.xfs'
    # EXT4 by default
    else:
        mkfs_cmd = 'mkfs.ext4'

    success = _exec_cmd([mkfs_cmd,
                         '-F',
                         img_path])
    if not success:
        raise CreateVolumeError('Could not format the loop device: ' + volume_id)
    logging.info(success)

    # Compress the volume
    success = _exec_cmd(['tar',
                         'cvzf',
                         targz_path,
                         '-C',
                         volume_path,
                         img_name])
    if not success:
        raise CreateVolumeError('Could not compress the volume: ' + volume_id)
    logging.info(success)

    # Delete the uncompressed volume
    os.remove(img_path)

def destroy_volume(volume_id):
    umount_volume(volume_id)
    # TODO


def mount_volume(disk_path,
                 volume_id,
                 volume_groups=None,
                 volume_group_mode=None,
                 shared_volumes_path='/mnt/ancoris/volume_groups',
                 mount_relative_dir='mount-point',
                 mode='rw',
                 tmpfs=False):

    ###########################################################################
    # TODO TASK_GROUP
    ###########################################################################

    volume_path = _get_volume_path(disk_path, volume_id)

    # Check if the volume exists
    img_path = volume_path + '/' + volume_id + '.img'

    targz_path = img_path.replace('.img', '.tar.gz')

    if not os.path.exists(targz_path):
        raise MountVolumeError('The compressed volume does not exist: '
        + targz_path)

    # Create directory for the volume mount point if it does not exist
    mount_path = volume_path + '/' + mount_relative_dir

    if not os.path.exists(mount_path):
        os.makedirs(mount_path)

    if not tmpfs:
        # Uncompress the volume if the img is not uncompressed
        if not os.path.exists(img_path):
            try:
                _uncompress_volume(targz_path, volume_path)
            except MountVolumeError:
                raise

        # Preserve it as a backup...
        # Delete the compressed volume
        # os.remove(targz_path)

        # Mount the uncompressed volume
        success = _exec_cmd(['mount',
                             img_path,
                             mount_path])
        logging.info(success)

    # tmpfs
    else:
        # Uncompress the volume
        if not os.path.exists(img_path):
            try:
                _uncompress_volume(targz_path, disk_path + '/' + volume_id)
            except MountVolumeError:
                raise

        # Size in bytes of the volume
        volume_size = os.path.getsize(img_path)

        # Create a tmpfs with the same size of the volume
        try:
            _create_tmpfs(str(volume_size), mount_path)
        except ExecCommandError as e:
            raise

        # Mount the volume in disk
        mount_relative_dir = 'tmp-mount-point'
        mount_volume(disk_path,
                     volume_id,
                     mount_relative_dir=mount_relative_dir)

        # Dump all the volume content in the tmpfs
        tmp_mount_path = disk_path + '/' + volume_id + '/' + mount_relative_dir
        try:
            _copy_content(tmp_mount_path, mount_path)
        except ExecCommandError:
            raise

        # Erase the original volume content
        try:
            _remove_content(tmp_mount_path)
        except ExecCommandError:
            raise

        # Umount the temporal volume
        # try...
        # umount_volume(tmp_mount_path)

        # Remove the temporal mount point
        # os.rmdir(tmp_mount_path)

        # Remove the original image_dir
        # os.remove(img_path)

    # Both for tmpfs and ordinary volumes.
    # Remount the volume as read-only if applicable.
    # https://lwn.net/Articles/281157/
    if mode == 'ro':
        _remount_volume_ro(mount_path)

    # Remount the volume so it will be accesible for all the tasks
    # under the same volume group (usually namesake to the task group).
    if volume_groups:
        volume_group_paths = []
        for volume_group in volume_groups:
            volume_group_path =  shared_volumes_path + '/' \
                + volume_group + '/' + volume_id
            if not os.path.exists(volume_group_path):
                os.makedirs(volume_group_path)

            success = _exec_cmd(['mount',
                                 '--bind',
                                 mount_path,
                                 volume_group_path])
            logging.info(success)

            # Remount the volume as read-only if applicable.
            if volume_group_mode == 'ro':
                _remount_volume_ro(volume_group_path)


def umount_volume(mount_path, tmpfs=False):
    ############################################################################
    # TODO -> UMOUNT ESPECIAL PARA TMPFS (COPIAR DE NUEVO)
    ############################################################################

    try:
        if not os.path.exists(mount_path):
            raise UmountVolumeError("The path " + mount_path
            + " does not exist")
        success = _exec_cmd(['umount', mount_path])
        logging.info(success)
    except ExecCommandError:
        raise UmountVolumeError("Could not mount the volume at "
        + mount_path)

################################################################################

def _remount_volume_ro(mount_path):
    try:
        success = _exec_cmd(['mount',
                             '--bind',
                             '-o',
                             'remount,ro',
                             mount_path])
        logging.info(success)
    except ExecCommandError:
        raise ExecCommandError('Error binding a tmpfs in ' + mount_path)

def _create_tmpfs(volume_size, mount_path):
    try:
        success = _exec_cmd(['mount',
                             '-o',
                             'size=' + volume_size,
                             '-t',
                             'tmpfs',
                             'tmpfs_ancoris',
                             mount_path])
        logging.info(success)
    except ExecCommandError:
        raise ExecCommandError('Error binding a tmpfs in ' + mount_path)

def _uncompress_volume(targz_path, target_path):
    try:
        success = _exec_cmd(['tar',
                             'xvzf',
                             targz_path,
                             '-C',
                             target_path])
        logging.info(success)
    except ExecCommandError:
        raise ExecCommandError('Error uncompressing the volume: '
        + targz_path + ' in: ' + volume_path)

def _copy_content(source_path, target_path):
    try:
        success = _exec_cmd(['cp', '-a', source_path + '/.', target_path])
        logging.info(success)
    except ExecCommandError:
        raise ExecCommandError("Error copying the volume's content (tmpfs): "
        + source_path + ' to ' + target_path)

def _remove_content(target_path):
    try:
        files = [f for f in glob.glob(target_path + '/*')]
        success = _exec_cmd(['rm', '-rf'] + files)
        logging.info(success)
    except ExecCommandError:
        raise ExecCommandError("Error removing the volume's content: "
        + target_path)

################################################################################

def _exec_cmd(args):
    try:
        return subprocess.check_output(args, stderr=subprocess.STDOUT) \
            .decode('utf-8')
    except subprocess.CalledProcessError as e:
        raise ExecCommandError(str(e))
