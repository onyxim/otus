import gzip
import os
import shutil
import sys
import tempfile
import unittest
from configparser import ConfigParser
from os.path import join

from lib_settings import DEFAULT_SECTION_NAME, SettingsKeys, REPORT_TEMPLATE_PATH
from log_analyzer import main, get_template
from test_data import log_data, test_report_data


class TestCompleteParsing(unittest.TestCase):
    GZ_FILE_NAME = 'nginx-access-ui.log-20170701.gz'
    FILE_NAME = 'nginx-access-ui.log-20170702.log'
    CONFIG_NAME = 'config.ini'
    LOG_NAME = 'logfile.log'

    TEST_LOG_PATH = './test_log.log'
    TEST_REPORT_PATH = './test_report.html'
    CONFIG_TEMPLATE_PATH = './config_template.ini'

    def setUp(self):
        # Create a temporary directory
        self.test_log_dir = tempfile.mkdtemp()
        self.test_report_dir = tempfile.mkdtemp()

        # Готовим файлы логов для парсинга
        test_log_data = log_data.encode('utf-8')
        with open(join(self.test_log_dir, self.GZ_FILE_NAME), mode='wb') as file:
            file.write(gzip.compress(test_log_data))
        with open(join(self.test_log_dir, self.FILE_NAME), mode='wb') as file:
            file.write(test_log_data)

        # Готовим конфиг для теста парсера
        config = ConfigParser()
        with open(self.CONFIG_TEMPLATE_PATH) as config_template_file:
            config.read_file(config_template_file)
        config[DEFAULT_SECTION_NAME][SettingsKeys.nginx_logs_dir] = self.test_log_dir
        config[DEFAULT_SECTION_NAME][SettingsKeys.reports_dir] = self.test_report_dir
        # Иначе все запросы отфильтруются и в отчетах ничего не будет
        config[DEFAULT_SECTION_NAME][SettingsKeys.report_size] = '0'
        self.log_file_path = join(self.test_log_dir, self.LOG_NAME)
        config[DEFAULT_SECTION_NAME][SettingsKeys.analyzer_log_file] = self.log_file_path

        config_file_path = join(self.test_log_dir, self.CONFIG_NAME)
        with open(config_file_path, mode='w') as file:
            config.write(file)

        # Имитируем как-будто бы передачу пути до конфига для парсинга
        sys.argv.extend(('-c', config_file_path))

        # Готовим шаблон для проверки отчетов
        report_template = get_template(REPORT_TEMPLATE_PATH)
        self.report_example = report_template.safe_substitute(table_json=test_report_data)

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_log_dir)
        shutil.rmtree(self.test_report_dir)

    def test_something(self):
        main()
        for report in os.scandir(self.test_report_dir):
            with open(report.path, newline='') as file:
                self.assertEqual(self.report_example, file.read())
        self.assertTrue(os.path.isfile(self.log_file_path))


if __name__ == '__main__':
    unittest.main()
