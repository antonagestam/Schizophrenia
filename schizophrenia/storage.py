# -*- coding: utf-8 -*-

import os

from django.core.files.storage import Storage, FileSystemStorage
from django.conf import settings
from django.utils.importlib import import_module

from .exceptions import VerificationException

def get_storage(klass):
    """Helper to import storage module and return instance"""
    if isinstance(klass, str):
        parts = klass.split('.')
        storage_name = parts.pop()
        module = import_module('.'.join(parts))
        klass = getattr(module, storage_name)
    return klass


class SchizophreniaStorage(Storage):

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
        remote_file = self.source.open(name)
        self.downloads.save(name, remote_file)
        return self.downloads.open(name)

    def sync(self, name, verify=False, cleanup=True, clear=True):
        """Get file from source storage and upload to target"""

        local_file = self.download(name)
        exists = self.issynced(name)

        if exists:
            if clear:
                self.target.delete(name)
            else:
                return True

        self.target.save(name, local_file)

        if verify:
            try:
                self.verify(name)
            except VerificationException:
                raise
            finally:
                self.downloads.delete(name)
                if cleanup:
                    self.cleanup()

        self.downloads.delete(name)
        if cleanup:
            self.cleanup()

        return True

    def issynced(self, name):
        """Does the file exist on target storage?"""
        return self.target.exists(name)

    def verify(self, name):
        if self.downloads.exists(name):
            comparison = self.downloads
        else:
            comparison = self.source

        if self.target.open(name).read() != comparison.open(name).read():
            raise VerificationException("Sync verification failed for '%s'"
                                        % name)
        return True

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

    def cleanup(self):
        """Cleanup empty directories that might be left over from downloads"""
        self._remove_empty_folders(settings.SCHIZOPHRENIA_CACHE_DIR)

    def _open(self, name, *args, **kwargs):
        """Always reads from source storage"""
        return self.source._open(name, *args, **kwargs)

    def _save(self, *args, **kwargs):
        """Saves both source and target but returns value of target storage"""

        source_name = self.source._save(*args, **kwargs)
        target_name = self.target._save(*args, **kwargs)

        if source_name != target_name:
            raise ValueError("Storages saved with different names")

        return target_name

    def get_available_name(self, name):
        source_name = self.source.get_available_name(name)
        target_name = self.target.get_available_name(name)

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

    def delete(self, name):
        self.target.delete(name)
        return self.source.delete(name)

    def exists(self, name):
        return self.source.exists(name)

    def listdir(self, path):
        return self.source.listdir(path)

    def size(self, name):
        return self.source.size(name)

    def url(self, name):
        return self.source.url(name)


if getattr(settings, 'SCHIZOPHRENIA_ALIAS_TARGET_STORAGE', False):
    target_storage = get_storage(settings.SCHIZOPHRENIA_TARGET_STORAGE)
    SchizophreniaStorage = target_storage