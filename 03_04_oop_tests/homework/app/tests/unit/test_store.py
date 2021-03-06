from collections import OrderedDict
from unittest import mock

import pytest

from store import Store as OriginalStore


class MyException(Exception):
    pass


class Store(OriginalStore):
    _retry_count = 2

    def __init__(self):
        pass


@mock.patch('store.Redis', autospec=True, return_value=None)
def test_store__init__(mock_redis):
    store = OriginalStore(cache_kwargs={}, store_kwargs={}, retry_count=1)
    assert store._retry_count == 1
    assert store._store_conn is None
    assert store._cache_conn is None


@pytest.fixture
def mock_action(request):
    return_value, side_effect = request.param
    patch = mock.patch.object(Store, '_retry_action_with_store', autospec=True, return_value=return_value,
                              side_effect=side_effect)
    yield patch.start()
    patch.stop()


class TestStore:

    def test__retry_action_with_store_count_overflow(self):
        m = mock.MagicMock()
        m.side_effect = [Exception, MyException]

        with pytest.raises(MyException):
            Store()._retry_action_with_store(m, 'test_key')
        m.assert_called_with('test_key')

    def test__retry_action_with_store_success_return(self):
        m = mock.MagicMock()
        m.side_effect = lambda x: 'test_value'
        r = Store()._retry_action_with_store(m, 'test_key')
        assert r == 'test_value'

    _retry_action_with_store_return_value = 'some_result'

    @staticmethod
    def edited_store(attr, method_name):
        m = mock.MagicMock()
        setattr(m, method_name, None)
        s = Store()
        setattr(s, attr, m)
        return s

    @pytest.mark.parametrize('mock_action', [(_retry_action_with_store_return_value, None)], indirect=True)
    def test_set(self, mock_action):
        params = OrderedDict((('name', 'test_key'), ('value', 'test_value'), ('ex', 3600)))
        store = self.edited_store('_cache_conn', 'set')

        # Call actual method
        assert store.cache_set(*params.values()) == self._retry_action_with_store_return_value
        mock_action.assert_called_with(store, store._cache_conn.set, **params)

    @pytest.mark.parametrize('mock_action,result', [
        ((_retry_action_with_store_return_value, None), _retry_action_with_store_return_value),
        ((None, MyException), None),
    ], indirect=['mock_action'])
    def test_cache_get(self, mock_action, result):
        key = 'some_key'
        store = self.edited_store('_cache_conn', 'get')

        # Call actual method
        assert store.cache_get(key) == result
        mock_action.assert_called_with(store, store._cache_conn.get, key)

    @pytest.mark.parametrize('mock_action', [(_retry_action_with_store_return_value, None)], indirect=True)
    def test_get(self, mock_action):
        key = 'some_key'
        store = self.edited_store('_store_conn', 'get')

        # Call actual method
        assert store.get(key) == self._retry_action_with_store_return_value
        mock_action.assert_called_with(store, store._store_conn.get, key)
