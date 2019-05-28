from config.settings.base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 's^=76%v^m^$1qf7l7h3f-aqaq9^utuyj9&omnvv$i59*#m^&z)'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['aclol.me']

INSTALLED_APPS = INSTALLED_APPS + [
    'debug_toolbar',
]

MIDDLEWARE = MIDDLEWARE + [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Necessary for debug_toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]
