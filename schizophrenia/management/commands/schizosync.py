# -*- coding: utf-8 -*-

from __future__ import with_statement

import os
from optparse import make_option

from django.core.management.base import CommandError, NoArgsCommand
from django.core.files.storage import get_storage_class, DefaultStorage
from django.utils.encoding import smart_str
from django.db.models import get_models, FileField

from ...storage import SchizophreniaStorage
from ...exceptions import VerificationException


class Command(NoArgsCommand):
    """
    Syncs files between Schizophrenias storage backends.
    """
    option_list = NoArgsCommand.option_list + (
        make_option('--verify',
            action='store_true', dest='verify', default=False,
            help="Verify synced files after upload."),
    )
    help = "Syncs files between Schizophrenias storage backends."
    requires_model_validation = True

    def __init__(self, *args, **kwargs):
        super(NoArgsCommand, self).__init__(*args, **kwargs)
        # Use ints for file times (ticket #14665), if supported
        if hasattr(os, 'stat_float_times'):
            os.stat_float_times(False)

    def set_options(self, **options):
        """Set instance variables based on an options dict"""
        self.verbosity = int(options.get('verbosity', 1))
        self.verify = options['verify']

    def get_fields(self):
        """Get all FileFields that are using SchizophreniaStorage"""
        fields = []
        default_storage = get_storage_class()
        valid_storage = [SchizophreniaStorage]
        if default_storage == SchizophreniaStorage:
            valid_storage.append(DefaultStorage)

        for model in get_models():
            for field in model._meta.fields:
                if (isinstance(field, FileField)
                        and type(field.storage) in valid_storage):
                    fields.append(field)

        return fields

    def handle_noargs(self, **options):
        self.set_options(**options)
        fields = self.get_fields()
        storage = SchizophreniaStorage()
        source_storage = storage.source.__class__.__name__
        target_storage = storage.target.__class__.__name__

        for field in fields:
            objects = field.model.objects.all()
            for obj in objects:
                try:
                    filename = getattr(obj, field.name).file.name
                except ValueError:
                    # No file associated
                    continue

                try:
                    if storage.sync(filename, self.verify, False):
                        action = "Synced"
                    else:
                        action = "Failed to sync"
                except VerificationException, e:
                    raise CommandError('VerificationException: %s' % e.message)
                finally:
                    self.log("%(action)s '%(filename)s' from '%(source)s' to "
                             "'%(target)s'" % {'action': action,
                                               'filename': filename,
                                               'source': source_storage,
                                               'target': target_storage})

        storage.cleanup()

    def log(self, msg, level=2):
        """
        Small log helper
        """
        msg = smart_str(msg)
        if not msg.endswith("\n"):
            msg += "\n"
        if self.verbosity >= level:
            self.stdout.write(msg)
