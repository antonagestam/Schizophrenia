# -*- coding: utf-8 -*-

import os
import logging
import shutil

from django.core.cache import cache
from django.core.files.base import File
from django.core.files.storage import Storage, FileSystemStorage
from django.conf import settings
from django.utils.importlib import import_module

from .exceptions import VerificationException


logger = logging.getLogger(__name__)


def get_storage(klass):
    """Helper to import storage module and return instance"""
    if isinstance(klass, str):
        parts = klass.split('.')
        storage_name = parts.pop()
        module = import_module('.'.join(parts))
        klass = getattr(module, storage_name)
    return klass


class CompatibleFile(File):
    """Hack to deal with s3Boto not assuming Django storage-compatible file"""
    def seek(self, a, *args, **kwargs):
        super(CompatibleFile, self).seek(a)


class SchizophreniaStorage(Storage):
    SYNCED = 'synced'
    VERIFIED = 'verified'

    def __init__(self, source=None, target=None):
        if not source:
            source = settings.SCHIZOPHRENIA_SOURCE_STORAGE

        if not target:
            target = settings.SCHIZOPHRENIA_TARGET_STORAGE

        self.source = get_storage(source)()
        self.target = get_storage(target)()
        self.downloads = FileSystemStorage(settings.SCHIZOPHRENIA_CACHE_DIR)

    def download(self, name):
        """Download file and return instance of local File"""
        if self.downloads.exists(name):
            return self.downloads.open(name)
        remote_file = self.source.open(name)
        self.downloads.save(name, remote_file)
        return self.downloads.open(name)

    def _get_file_cache_key(self, name):
        return 'schizophrenia_state_%s' % name

    def sync(self, name, verify=False):
        """Get file from source storage and upload to target"""

        logger.debug('Checking cached state ...')

        # Check cached state, return if synced
        cache_key = self._get_file_cache_key(name)
        cached_state = cache.get(cache_key, None)

        if cached_state == self.VERIFIED:
            logger.info('File was verified, skipping')
            cache.set(cache_key, self.VERIFIED)
            return True
        elif cached_state == self.SYNCED and not verify:
            logger.info('File was synced, skipping because verify=False')
            return True
        elif cached_state == self.SYNCED or self.target.exists(name):
            logger.info('File was synced, verifying ...')
            # If file exists on target, verify. Return if synced
            try:
                self.verify(name)
            except VerificationException:
                logger.info("File didn't verify, syncing again ...")
                cached_state = None
                cache.delete(cache_key)
            else:
                logger.info('File verified OK')
                cache.set(cache_key, self.VERIFIED)
                return True

        # Sync
        logger.debug('Downloading source file ...')
        local_file = self.download(name)
        logger.debug('Uploading to target storage ...')
        self.target.save(name, local_file)
        cache.set(cache_key, self.SYNCED)

        # Verify
        if verify:
            logger.debug('Verifying ...')
            try:
                self.verify(name)
                logger.debug('Verified OK')
                cache.set(cache_key, self.VERIFIED)
            except VerificationException:
                raise
            finally:
                self.downloads.delete(name)

        self.downloads.delete(name)
        return True

    def issynced(self, name):
        """Does the file exist on target storage?"""
        return self.target.exists(name)

    def verify(self, name):
        if self.target.open(name).read() != self.download(name).read():
            raise VerificationException("Sync verification failed for '%s'"
                                        % name)
        return True

    def cleanup(self, force=False):
        """Cleanup empty directories that might be left over from downloads"""
        if force:
            shutil.rmtree(settings.SCHIZOPHRENIA_CACHE_DIR)
        else:
            self._remove_empty_folders(settings.SCHIZOPHRENIA_CACHE_DIR)

    def _remove_empty_folders(self, path):
        if not os.path.isdir(path):
            return

        # remove empty subfolders
        files = os.listdir(path)
        if len(files):
            for f in files:
                fullpath = os.path.join(path, f)
                if os.path.isdir(fullpath):
                    self._remove_empty_folders(fullpath)

        # if folder empty, delete it
        files = os.listdir(path)
        if len(files) == 0:
            os.rmdir(path)

    def _open(self, name, *args, **kwargs):
        """Reads from target storage if verified, otherwise source"""
        storage = self._get_verified_storage(name)
        return storage.open(name, *args, **kwargs)

    def _storage_save(self, storage, name, content):
        """Save to storage"""

        try:
            name = storage.save(name, content)
        except TypeError:
            content = CompatibleFile(file=content)
            name = storage.save(name, content)

        return name

    def _save(self, name, content):
        """Saves both source and target but returns value of target storage"""

        source_name = self._storage_save(self.source, name, content)
        target_name = self._storage_save(self.target, name, content)

        if source_name != target_name:
            raise ValueError("Storages saved with different names")

        return target_name

    def get_available_name(self, name):
        source_name = self.source.get_available_name(name)
        target_name = self.target.get_available_name(source_name)

        if source_name != target_name:
            raise ValueError("Storages returned different values from "
                             "get_available_name.")

        return target_name

    def get_valid_name(self, name):
        source_name = self.source.get_valid_name(name)
        target_name = self.target.get_valid_name(name)

        if source_name != target_name:
            raise ValueError("Storages returned different values from "
                             "get_valid_name.")

        return target_name

    def _get_verified_storage(self, name):
        if cache.get(self._get_file_cache_key(name), None) == self.VERIFIED:
            storage = self.target
        else:
            storage = self.source
        return storage

    def delete(self, name):
        self.target.delete(name)
        return self.source.delete(name)

    def exists(self, name):
        storage = self._get_verified_storage(name)
        return storage.exists(name)

    def listdir(self, path):
        return self.source.listdir(path)

    def size(self, name):
        storage = self._get_verified_storage(name)
        return storage.size(name)

    def url(self, name):
        storage = self._get_verified_storage(name)
        return storage.url(name)
