import os
import random

import mimesis
import pytest

import crawler
from config import Config
from crawler import prepare_file_path


def get_test_html_page(name):
    test_main_page_path = os.path.join(os.path.dirname(__file__), name)

    with open(test_main_page_path, newline='') as test_main_page_file:
        return test_main_page_file.read()


class Test_prepare_file_path:
    PATH = "/tmp/test"
    DEFAULT_NAME = "page.html"

    @pytest.mark.parametrize("url,result", [
        ("https://www.dreamsongs.com/Files/WhyOfY.pdf", "/WhyOfY.pdf"),
        ("https://medicalxpress.com/news/diet-cardiovascular.html", "/diet-cardiovascular.html"),
        ("https://rocket.rs/v0.4/news/2018-12-08-version-0.4/", "/page.html"),
        ("https://rocket.rs/v0.4/news/2018-12-08-version-0.4", "/page.html"),
    ])
    def test_prepare_file_path(self, url, result):
        assert prepare_file_path(url, self.PATH, self.DEFAULT_NAME, Config.allowed_suffixs) == self.PATH + result


class Test_get_existed_ids:
    MAX_ID = 999999
    GEN_FOLDER_NUMBER = 5

    def test(self, tmp_path):
        ids_set = set()
        for _ in range(self.GEN_FOLDER_NUMBER):
            rand_id = str(random.randrange(self.MAX_ID))
            ids_set.add(rand_id)
            rand_name = ' '.join(mimesis.Text().words())
            dir_name = f'{rand_id} {rand_name}'
            os.mkdir(os.path.join(tmp_path, dir_name))

        assert ids_set == crawler.get_existed_ids(tmp_path)
