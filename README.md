Schizophrenia
=============

A Django Storage with multiple ~~personalities~~ … storage backends. Created for the
purpose of migrating from one default storage backend to another.

Installation
------------

Put this in settings file:
    
    DEFAULT_FILE_STORAGE = 'schizophrenia.storage.SchizophreniaStorage'
    
    # The storage backend that you want to get rid of
    SCHIZOPHRENIA_SOURCE_STORAGE = 'cumulus.storage.CloudFilesStorage'
    # The storage backend that you want to migrate to
    SCHIZOPHRENIA_TARGET_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    # A directory where Schizophrenia can put temporary files
    SCHIZOPHRENIA_CACHE_DIR = './.schizophrenia_cache/'
    
Migrating files
---------------

To migrate all your files to your new storage backend, run the command below. This will
copy all of your files from your source storage to your target storage.

    $ python manage.py schizosync --verbosity=3 --verify
    
Converting your project
-----------------------

Syncing all the files might take some time but should be fairly straight-forward. To
automatically start using your new backend once the transfer is done, you can put this
in your settings file:
    
    import os
    SCHIZOPHRENIA_ALIAS_TARGET_STORAGE = bool(os.environ.get('SCHIZOPHRENIA_ALIAS_ON', False))
    
And then run the command like this:

    $ python manage.py schizosync --verbosity=3 --verify; export SCHIZOPHRENIA_ALIAS_ON=1
    
As you can see it's easy to create a logic for when to switch to your target storage backend.
The next time you deploy code you'd probably want to set `DEFAULT_FILE_STORAGE` to your new
backend and uninstall Schizophrenia.

License
-------

Schizophrenia is licensed under The MIT License. See the LICENSE file to read the full license.
