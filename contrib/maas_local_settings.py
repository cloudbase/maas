# Debug/Production mode.
DEBUG = True

# Default URL specifying protocol, host, and (if necessary) port where
# systems in this MAAS can find the MAAS server.  Configuration can, and
# probably should, override this.
DEFAULT_MAAS_URL = "http://maas.internal.example.com/"

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = '/var/lib/maas/static/'

# Prefix to use for MAAS's urls.
# If FORCE_SCRIPT_NAME is None (the default), all the urls will start with
# '/'.
FORCE_SCRIPT_NAME = '/MAAS'

# Where to store the user uploaded files.
MEDIA_ROOT = '/var/lib/maas/media/'

# Use the (libjs-yui) package's files to serve YUI3.
YUI_LOCATION = '/usr/share/javascript/yui3/'

# Use the package's files to serve RaphaelJS.
RAPHAELJS_LOCATION = '/usr/share/javascript/raphael/'

# RabbitMQ settings.
RABBITMQ_HOST = 'localhost'
RABBITMQ_USERID = 'maas_longpoll'
RABBITMQ_PASSWORD = ''
RABBITMQ_VIRTUAL_HOST = '/maas_longpoll'

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize the logging configuration.
LOGGING_LEVEL = 'INFO'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'log': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/maas/maas.log',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'maasserver': {
            'level': LOGGING_LEVEL,
            'handlers': ['log'],
            'propagate': True,
        },
        'metadataserver': {
            'level': LOGGING_LEVEL,
            'handlers': ['log'],
            'propagate': True,
        },
        'django.request': {
            'level': LOGGING_LEVEL,
            'handlers': ['log'],
            'propagate': True,
        },
        'django.db.backends': {
            'level': LOGGING_LEVEL,
            'handlers': ['log'],
            'propagate': True,
        },
    },
}

# Database access configuration.
DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' etc.
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
    }
}
