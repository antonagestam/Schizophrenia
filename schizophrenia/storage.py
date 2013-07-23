import os, logging

from django.core.files.storage import Storage, FileSystemStorage
from django.conf import settings
from django.utils.importlib import import_module

logger = logging.getLogger(__name__)


class SchizophreniaStorage(Storage):

    def __init__(self, source=None, target=None):
        if not source:
            source = settings.SCHIZOPHRENIA_SOURCE_STORAGE

        if not target:
            target = settings.SCHIZOPHRENIA_TARGET_STORAGE

        self.source = self.get_storage(source)
        self.target = self.get_storage(target)
        self.downloads = FileSystemStorage(settings.SCHIZOPHRENIA_CACHE_DIR)

    def get_storage(self, klass):
        """Import storage module and return instance"""
        if isinstance(klass, str):
            parts = klass.split('.')
            storage_name = parts.pop()
            module = import_module('.'.join(parts))
            klass = getattr(module, storage_name)()
        return klass

    def download(self, name):
        """Download file and return instance of local File"""
        remote_file = self.source.open(name)
        self.downloads.save(name, remote_file)
        return self.downloads.open(name)

    def sync(self, name, verify=False):
        """Get file from source storage and upload to target"""

        local_file = self.download(name)

        if self.target.exists(name):
            self.target.delete(name)

        self.target.save(name, local_file)

        self.downloads.delete(name)
        self.cleanup()

        if verify and not self.verify(name):
            logger.error("Sync verification failed for '%s'" % name)
            return False

        return True

    def issynced(self, name):
        """Does the file exist on target storage?"""
        return self.target.exists(name)

    def verify(self, name):
        return self.target.open(name).read() == self.source.open(name).read()

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
        url = self.target.url(name)

        if url is None:
            url = self.source.url(name)

        return url
