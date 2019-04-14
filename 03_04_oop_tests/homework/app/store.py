import logging

from redis import Redis
from typing import Dict, Union


class Store:
    def __init__(self, *, cache_kwargs: Dict, store_kwargs: Dict, retry_count: int):
        self._cache_conn = Redis(**cache_kwargs)
        self._store_conn = Redis(**store_kwargs)
        self._retry_count = retry_count

    def _retry_action_with_store(self, method, *args, **kwargs):
        # Количество попыток проверяется здесь. А таймаут задается в конфиге Redis connection.
        for n in range(self._retry_count):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                if n + 1 == self._retry_count:
                    logging.exception('Number of retry exhausted, will raise an exception outside.')
                    raise e
                logging.exception('Some exception happend, will try again')

    def cache_set(self, key: str, value: str, ttl: int):
        return self._retry_action_with_store(self._cache_conn.set, name=key, value=value, ex=ttl)

    def cache_get(self, key: str) -> Union[bytes, None]:
        try:
            return self._retry_action_with_store(self._cache_conn.get, key)
        except Exception:
            logging.exception('Something wrong with cache store, but whatever we continue.')

    def get(self, key: str) -> Union[bytes, None]:
        return self._retry_action_with_store(self._store_conn.get, key)
