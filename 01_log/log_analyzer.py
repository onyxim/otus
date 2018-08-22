#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import json
import logging
import os
from itertools import chain
from string import Template

from lib_analyze import get_stat_data
from lib_get_logs_names import get_logs_names_to_parse, validate_dirs
from lib_settings import MyException, get_settings_from_config, DEFAULT_SETTINGS, DEFAULT_CONFIG_PATH, SettingsKeys, \
    REPORT_TEMPLATE_PATH, logging_settings, reset_logger

logging.basicConfig(**logging_settings)


def get_template(path):
    with open(path, newline='') as report_template_file:
        return Template(report_template_file.read())


def parse_logs(first_log, logs_registry, report_template, **kwargs):
    parsed_logs_count = 0
    for log in chain((first_log,), logs_registry.values()):
        logging.info('Begin parsing the log file:\n' + log.log_file_path)
        stat_data = get_stat_data(log, **kwargs)
        if not stat_data:
            continue
        report = report_template.safe_substitute(table_json=json.dumps(stat_data, sort_keys=True))
        try:
            with open(log.report_file_path, mode='w', encoding='utf-8') as report_file:
                report_file.write(report)
        except Exception as exception:
            logging.error('Something going wrong with report creation. Trying to remove report '
                          'file:\n' + log.report_file_path)
            os.remove(log.report_file_path)
            raise exception
        parsed_logs_count += 1
    return parsed_logs_count


def main():
    parser = argparse.ArgumentParser(description='Create reports from nginx logs.')
    parser.add_argument('-c', '--config', nargs='?', const=DEFAULT_CONFIG_PATH, default='',
                        help='path to config or empty, then default path "./config" relative to script '
                             'location will be used')
    args = parser.parse_args()
    config_path = args.config
    settings = DEFAULT_SETTINGS.copy()
    if config_path == DEFAULT_CONFIG_PATH:
        logging.info('Used default config path "{}"'.format(DEFAULT_CONFIG_PATH))
    if config_path:
        settings_from_config = get_settings_from_config(config_path)
        settings.update(settings_from_config)
        logging.info('Successfully update settings from config {}'.format(config_path))

    # С этого момента начинаем выводить лог в файл, если задано в настройках
    reset_logger(settings[SettingsKeys.analyzer_log_file])

    report_template = get_template(REPORT_TEMPLATE_PATH)

    nginx_logs_dir, reports_dir = validate_dirs(settings[SettingsKeys.nginx_logs_dir],
                                                settings[SettingsKeys.reports_dir])

    logs_registry, max_date = get_logs_names_to_parse(nginx_logs_dir, reports_dir)
    if not logs_registry:
        logging.info('No new logs find to parse.')
    else:
        logs_count = len(logs_registry)
        logging.info('There are {} existed logs to parse.'.format(logs_count))
        parsed_logs_count = parse_logs(logs_registry.pop(max_date), logs_registry, report_template, **settings)
        logging.info('{} of {} logs are parsed successfully.'.format(parsed_logs_count, logs_count))


if __name__ == "__main__":
    try:
        main()
    except MyException as e:
        logging.error(e)
        logging.error('Script stopped.')
    except Exception as e:
        logging.exception(e)
