import datetime
import functools
import hashlib
import os
import random

import api
from store import Store

OTUS_TEST_EXT_SERVER_URL = 'OTUS_TEST_EXT_SERVER_URL'
OTUS_TEST_REDIS_PORT = 'OTUS_TEST_REDIS_PORT'
OTUS_TEST_REDIS_HOST = 'OTUS_TEST_REDIS_HOST'


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)

        return wrapper

    return decorator


def get_config_path():
    dir = os.path.dirname(os.path.abspath(api.__file__))
    return os.path.join(dir, 'config.yaml')


def get_store_for_tests():
    confif_file_path = get_config_path()
    config = api.get_config(confif_file_path)

    # Work with params from env vars
    test_redis_port = os.environ.get(OTUS_TEST_REDIS_PORT)
    test_redis_host = os.environ.get(OTUS_TEST_REDIS_HOST)
    if test_redis_host and test_redis_port:
        test_dict = {
            'host': test_redis_host,
            'port': test_redis_port,
        }
        config.store_connection_settings.update(test_dict)
        config.cache_connection_settings.update(test_dict)

    return Store(cache_kwargs=config.cache_connection_settings, store_kwargs=config.store_connection_settings,
                 retry_count=config.retry_count)


def get_interest():
    interests = ("cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus")
    while True:
        yield random.sample(interests, 2)


def set_valid_auth(request):
    if request.get("login") == api.ADMIN_LOGIN:
        date = datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
        request["token"] = hashlib.sha512(date.encode('utf-8')).hexdigest()
    else:
        msg = request.get("account", "") + request.get("login", "") + api.SALT
        request["token"] = hashlib.sha512(msg.encode('utf-8')).hexdigest()
    return request
