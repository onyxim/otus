import logging
from configparser import ConfigParser

from lib_errors import MyException, ErrorMessages

logging_settings = dict(
    format='[%(asctime)s] %(levelname).1s %(message)s',
    level=logging.INFO
)

DEFAULT_SECTION_NAME = 'SETTINGS'


class SettingsKeys:
    report_size = "report_size"
    reports_dir = "report_dir"
    nginx_logs_dir = "nginx_log_dir"
    analyzer_log_file = "analyzer_log_file"
    parse_success_threshold_percent = "parse_success_threshold_percent"
    max_time_parsing_for_log = 'max_time_parsing_for_log'


INT_VALUES = [SettingsKeys.report_size, SettingsKeys.parse_success_threshold_percent,
              SettingsKeys.max_time_parsing_for_log]

DEFAULT_SETTINGS = {
    SettingsKeys.report_size: 1000,
    SettingsKeys.reports_dir: "./reports",
    SettingsKeys.nginx_logs_dir: "./log",
    SettingsKeys.analyzer_log_file: None,
    SettingsKeys.parse_success_threshold_percent: 100,
    SettingsKeys.max_time_parsing_for_log: 600,
}

DEFAULT_CONFIG_PATH = "./config.ini"
REPORT_TEMPLATE_PATH = './report.html'


def check_config(config):
    sections = config.sections()
    if not sections:
        raise MyException(ErrorMessages.no_section)
    elif len(sections) > 1:
        raise MyException(ErrorMessages.more_than_one_error.format(sections, DEFAULT_SECTION_NAME))
    elif sections[0] != DEFAULT_SECTION_NAME:
        raise MyException(ErrorMessages.wrong_section_name.format(sections[0], DEFAULT_SECTION_NAME))
    settings_from_config = dict(config[DEFAULT_SECTION_NAME])
    not_allowed = set(settings_from_config.keys()).difference(DEFAULT_SETTINGS.keys())
    if not_allowed:
        raise MyException(ErrorMessages.not_in_allowed_keys.format(not_allowed))
    for v in INT_VALUES:
        current_value = settings_from_config[v]
        settings_from_config[v] = int(current_value)
    return settings_from_config


def get_settings_from_config(config_path):
    try:
        config = ConfigParser()
        with open(config_path) as config_file:
            logging.info('Open file {}'.format(config_path))
            config.read_file(config_file)
            return check_config(config)

    except OSError:

        raise MyException('Wrong path "{}" to config file! The script will be stopped.'.format(config_path))


def reset_logger(log_path):
    if log_path:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename=log_path, filemode='w', **logging_settings)
