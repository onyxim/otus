import unittest
from multiprocessing import Process

import json
import logging
import time
from unittest import mock

import datetime
import functools
import hashlib
import os
import pytest
import random
import requests

import api
from scoring import CID_KEY
from store import Store


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
    dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dir, 'config.yaml')


def get_store_for_tests():
    confif_file_path = get_config_path()
    config = api.get_config(confif_file_path)
    return Store(cache_kwargs=config.cache_connection_settings, store_kwargs=config.store_connection_settings,
                 retry_count=config.retry_count)


def get_interest():
    interests = ("cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus")
    while True:
        yield random.sample(interests, 2)


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = get_store_for_tests()

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    @staticmethod
    def set_valid_auth(request):
        if request.get("login") == api.ADMIN_LOGIN:
            date = datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
            request["token"] = hashlib.sha512(date.encode('utf-8')).hexdigest()
        else:
            msg = request.get("account", "") + request.get("login", "") + api.SALT
            request["token"] = hashlib.sha512(msg.encode('utf-8')).hexdigest()
        return request

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}},
    ])
    def test_bad_auth(self, request):
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
        {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
        {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases([
        {},
        {"phone": "79175002040"},
        {"phone": "89175002040", "email": "stupnikov@otus.ru"},
        {"phone": "79175002040", "email": "stupnikovotus.ru"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
        {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {"phone": "79175002040", "email": "stupnikov@otus.ru"},
        {"phone": 79175002040, "email": "stupnikov@otus.ru"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 0, "birthday": "01.01.2000"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_ok_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [1, 2], "date": "19.07.2017"},
        {"client_ids": [0]},
    ])
    # Решил восстановить работу оригинального теста
    @mock.patch.object(api, 'get_interests', autospec=True, side_effect=get_interest())
    def test_ok_interests_request(self, arguments, mock_):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(v and isinstance(v, list) and all(isinstance(i, str) for i in v)
                            for v in response.values()))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))


PORT = 8080


@pytest.fixture(scope='module', autouse=True)
def run_server():
    args = mock.MagicMock()
    args.port = PORT
    args.log = None
    args.config = get_config_path()
    p = Process(target=api.main, args=(args,))
    yield p.start()
    p.kill()


TEST_IDS = [n for n in range(100)]
TEST_ANSWER = {"test": "test"}


@pytest.fixture(scope='module')
def test_store():
    store = get_store_for_tests()
    store._store_conn.flushdb()
    return store


@pytest.fixture(scope='module', autouse=True)
def prepare_inrest_data(test_store):
    json_str = json.dumps(TEST_ANSWER)
    for id_ in TEST_IDS:
        test_store.cache_set(CID_KEY.format(id_), json_str, 60 * 60)


class TestRequests:
    URL = f'http://localhost:{PORT}/method'

    def make_request(self, request: dict):
        retry_count = 3
        for n in range(retry_count):
            try:
                return requests.post(self.URL, json=request, timeout=1)
            except Exception as e:
                if n == retry_count - 1:
                    raise e
            logging.exception('Catch some error.')
            time.sleep(1)

    def prepare_request(self, method, arguments: dict, admin_user=False):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": method,
            "arguments": arguments,
        }
        if admin_user:
            request['login'] = api.ADMIN_LOGIN
        return TestSuite.set_valid_auth(request)

    @pytest.mark.parametrize('ids', [
        random.sample(TEST_IDS, k=3) for _ in range(4)
    ])
    def test_ok_interests_request(self, ids):
        arguments = {"client_ids": ids, "date": datetime.datetime.today().strftime("%d.%m.%Y")}
        request = self.prepare_request('clients_interests', arguments)
        result_part = {str(id_): TEST_ANSWER for id_ in ids}
        result = {'response': result_part, 'code': api.OK}

        assert self.make_request(request).json() == result
