from django.core.files.storage import Storage
from django.conf import settings


class SchizophreniaStorage(Storage):

    def __init__(self, source_storage=None, target_storages=None):
        if not source_storage:
            source_storage = settings.SCHIZOPHRENIA_SOURCE_STORAGE

        if isinstance(source_storage, type):
            source_storage = source_storage()

        self.source_storage = source_storage

        if not target_storages:
            target_storages = settings.SCHIZOPHRENIA_TARGET_STORAGES

        for storage, key in target_storages:
            if isinstance(storage, type):
                target_storages[key] = storage()

        self.target_storages = target_storages

    def _open(self, *args, **kwargs):
        return self.source_storage._open(*args, **kwargs)

    def _save(self, *args, **kwargs):
        for storage in self.target_storages:
            storage._save(*args, **kwargs)
        return self.source_storage._save(*args, **kwargs)

    def get_available_name(self, name):
        return self.source_storage.get_available_name(name)

    def get_valid_name(self, name):
        return self.source_storage.get_valid_name(name)

    def delete(self, name):
        for storage in self.target_storages:
            storage.delete(name)
        return self.source_storage.delete(name)

    def exists(self, name):
        pass

    def listdir(self, path):
        pass

    def size(self, name):
        pass

    def url(self, name):
        pass
