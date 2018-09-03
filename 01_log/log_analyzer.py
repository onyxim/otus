#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
from string import Template

import yaml

from lib_analyze import get_stat_data
from lib_errors import MyException
from lib_get_logs_names import get_fresh_log_to_parse, validate_dirs

logging_settings = dict(
    format='[%(asctime)s] %(levelname).1s %(message)s',
    level=logging.INFO
)
logging.basicConfig(**logging_settings)

DEFAULT_SETTINGS = {
    "report_size": 1000,
    "reports_dir": "./reports",
    "nginx_logs_dir": "./log",
    "analyzer_log_file": None,
    "parse_success_threshold_percent": 100,
    "max_time_parsing_for_log": 600,
    "report_name_template": "report-{}.html",
    "nginx_log_name_re": r"""
        ^nginx-access-ui.log-       # обязательный префикс
        (?P<date>\d{8})             # дата, ровно 8 цифр подряд
        (?P<ext>\.gz|\.log)$        # в конце либо .gz либо пусто
    """,
    "nginx_line_log_re": r"""
        ^(?:\S+)\s                          # $remote_addr
        (?:\S+)\s{2}                        # $remote_user
        (?:\S+)\s                           # $http_x_real_ip
        \[(?:\S+\s\S+)\]\s                  # $time_local

        "(?:                                # $request
        \S+\s(?P<url>\S+)\s\S+              # Либо получаем нормальный url по шаблону. Именновая capture group.
        |0                                  # Либо получаем 0, тогда приедет None в groupsdict
        )"\s                                # конец non-capture group

        (?:\S+)\s                           # $status
        (?:\S+)\s                           # $body_bytes_sent
        "(?:\S+)"\s                         # $http_referer
        "(?:[^"]+)"\s                       # $http_user_agent
        "(?:\S+)"\s                         # $http_x_forwarded_for
        "(?:\S+)"\s                         # $http_X_REQUEST_ID
        "(?:\S+)"\s                         # $http_X_RB_USER
        (?P<time>\d+\.\d{3})$               # $request_time и еще нужно время, приезжает в виде "0.867"
    """,
}

DEFAULT_CONFIG_PATH = "./config.yml"
REPORT_TEMPLATE_PATH = './report.html'


def get_settings_from_config(config_path):
    try:
        with open(config_path) as config_file:
            logging.info('Open file {}'.format(config_path))
            config = yaml.load(config_file)
            return config

    except OSError:

        raise MyException('Wrong path "{}" to config file! The script will be stopped.'.format(config_path))


def reset_logger(log_path):
    if log_path:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename=log_path, filemode='w', **logging_settings)


def get_template(path):
    with open(path, newline='') as report_template_file:
        return Template(report_template_file.read())


def parse_log(log, report_template, **kwargs):
    logging.info('Begin parsing the log file:\n' + log.log_file_path)
    stat_data = get_stat_data(log, **kwargs)
    if not stat_data:
        return False
    report = report_template.safe_substitute(table_json=json.dumps(stat_data, sort_keys=True))
    try:
        with open(log.report_file_path, mode='w', encoding='utf-8') as report_file:
            report_file.write(report)
    except Exception as exception:
        logging.error('Something going wrong with report creation. Trying to remove report '
                      'file:\n' + log.report_file_path)
        os.remove(log.report_file_path)
        raise exception
    return True


def parse_args():
    parser = argparse.ArgumentParser(description='Create reports from nginx logs.')
    parser.add_argument('-c', '--config', nargs='?', const=DEFAULT_CONFIG_PATH, default='',
                        help='path to config or empty, then default path "./config" relative to script '
                             'location will be used')
    return parser.parse_args()


def main(do_parse_args=True):
    config_path = False
    if do_parse_args:
        config_path = parse_args().config
    settings = DEFAULT_SETTINGS.copy()
    if config_path == DEFAULT_CONFIG_PATH:
        logging.info('Used default config path "{}"'.format(DEFAULT_CONFIG_PATH))
    if config_path:
        settings_from_config = get_settings_from_config(config_path)
        settings.update(settings_from_config)
        logging.info('Successfully update settings from config {}'.format(config_path))

    # С этого момента начинаем выводить лог в файл, если задано в настройках
    reset_logger(settings["analyzer_log_file"])

    report_template = get_template(REPORT_TEMPLATE_PATH)

    validate_dirs(**settings)

    fresh_log = get_fresh_log_to_parse(**settings)
    if fresh_log:
        parse_log(fresh_log, report_template, **settings)
    else:
        logging.info('No new log find to parse.')


if __name__ == "__main__":
    try:
        main()
    except MyException as e:
        logging.error(e)
        logging.error('Script stopped.')
    except Exception as e:
        logging.exception(e)
