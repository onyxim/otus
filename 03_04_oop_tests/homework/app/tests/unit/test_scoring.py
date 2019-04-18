import datetime
from unittest import mock

import pytest

import scoring
from store import Store


class TestGetStore:
    CONST_ARGS = ('7586', 'email@example.com')
    CONST_KWARGS = {'gender': 'male'}

    @staticmethod
    def get_store(return_mock_get):
        store = mock.create_autospec(Store)
        store.cache_get.return_value = return_mock_get
        store.cache_set
        return store

    @pytest.mark.parametrize('first_name, last_name, birthday, get_key, score', [
        ('John', 'Doe', datetime.datetime.strptime('01.01.2000', '%d.%m.%Y'), 'uid:87d4f21e2a10a198d629cdd2e5297b90',
         5.0),
        (None, None, None, 'uid:d41d8cd98f00b204e9800998ecf8427e', 3.0),
    ])
    def test_get_score_fresh_score(self, first_name, last_name, birthday, get_key, score):
        store = self.get_store(None)

        r = scoring.get_score(store, *self.CONST_ARGS, first_name=first_name, last_name=last_name, birthday=birthday,
                              **self.CONST_KWARGS)
        assert r == score
        store.cache_get.assert_called_once_with(get_key)
        store.cache_set.assert_called_once_with(get_key, score, 3600)

        store.reset_mock()

    @pytest.mark.parametrize('first_name, last_name, birthday, get_key', [
        ('John', 'Doe', datetime.datetime.strptime('01.01.2000', '%d.%m.%Y'), 'uid:87d4f21e2a10a198d629cdd2e5297b90'),
        (None, None, None, 'uid:d41d8cd98f00b204e9800998ecf8427e'),
    ])
    def test_get_score_success_get_from_cache(self, first_name, last_name, birthday, get_key):
        store = self.get_store(b'10.0')

        r = scoring.get_score(store, *self.CONST_ARGS, first_name=first_name, last_name=last_name, birthday=birthday,
                              **self.CONST_KWARGS)
        assert r == 10.0
        store.cache_get.assert_called_once_with(get_key)
        store.cache_set.assert_not_called()

        store.reset_mock()


class TestGetInterests:
    @staticmethod
    def get_store(return_value):
        store = mock.create_autospec(Store)
        store.get.return_value = return_value
        return store

    @pytest.mark.parametrize('return_mock, return_value', [
        (b'{"test":"test"}', {'test': 'test'}),
        (None, []),
    ])
    def test_get_interests_success_return(self, return_mock, return_value):
        store = self.get_store(return_mock)
        key = 'test'

        r = scoring.get_interests(store, key)

        assert r == return_value
        store.get.assert_called_with(f"i:{key}")
