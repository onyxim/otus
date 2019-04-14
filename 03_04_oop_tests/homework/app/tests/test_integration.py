import datetime
import json
import logging
import os
import random
from multiprocessing import Process
from unittest import mock

import pytest
import requests
import time

import api
from scoring import CID_KEY
# envs for tests
from tests.helpers import get_config_path, get_store_for_tests, set_valid_auth, OTUS_TEST_EXT_SERVER_URL

PORT = 8080


@pytest.fixture(scope='module', autouse=True)
def run_server():
    if not os.environ.get(OTUS_TEST_EXT_SERVER_URL):
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
    URL = os.getenv(OTUS_TEST_EXT_SERVER_URL, f'http://localhost:{PORT}/method')

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
        return set_valid_auth(request)

    @pytest.mark.parametrize('ids', [
        random.sample(TEST_IDS, k=3) for _ in range(4)
    ])
    def test_ok_interests_request(self, ids):
        arguments = {"client_ids": ids, "date": datetime.datetime.today().strftime("%d.%m.%Y")}
        request = self.prepare_request('clients_interests', arguments)
        result_part = {str(id_): TEST_ANSWER for id_ in ids}
        result = {'response': result_part, 'code': api.OK}

        assert self.make_request(request).json() == result
