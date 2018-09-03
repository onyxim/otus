import logging
import os
import re
from collections import namedtuple
from datetime import datetime

from lib_errors import ErrorMessages, MyException

log_params = namedtuple('log_name', ('date_str', 'date', 'report_file_path', 'log_file_path', 'ext'))


def check_result_log_name(result, nginx_logs_path, reports_path, existed_reports, report_name_template, **settings):
    if not result:
        return False
    re_dict = result.groupdict()
    date_str = re_dict['date']
    try:
        log_date = datetime.strptime(date_str, '%Y%m%d')
    except ValueError:
        logging.error(ErrorMessages.wrong_date_conversion.format(date_str, result.string))
        return False
    date_str_report = log_date.strftime('%Y.%m.%d')
    report_name = report_name_template.format(date_str_report)
    # Можно конечно проверять наличие файла через os.path.isfile, но так не будет системного вызова
    if report_name in existed_reports:
        # Значит уже существует отчет на лог с полученным именем
        return False
    report_file_path = os.path.join(reports_path, report_name)
    nginx_file_path = os.path.join(nginx_logs_path, result.string)
    return log_params(date_str, log_date, report_file_path, nginx_file_path, re_dict['ext'])


def get_fresh_log_to_parse(nginx_logs_dir, reports_dir, nginx_log_name_re, **settings):
    max_date = None
    logs_registry = {}
    existed_reports = set(os.listdir(reports_dir))
    regex_name = re.compile(nginx_log_name_re, re.VERBOSE)
    for entry in os.scandir(nginx_logs_dir):
        if entry.is_dir():
            continue
        result = regex_name.match(entry.name)
        result = check_result_log_name(result, nginx_logs_dir, reports_dir, existed_reports, **settings)
        if not result:
            continue
        elif result.date in logs_registry:
            logging.error(ErrorMessages.probably_duplicate.format(result.date_str))
            continue
        logs_registry[result.date] = result
        if not max_date or result.date > max_date:
            max_date = result.date
    return logs_registry.pop(max_date, None)


def validate_dirs(**settings):
    for key, directory in settings.items():
        if not key.endswith('dir'):
            continue
        # Прогоняем через abspath, чтобы решить проблему с trailing slash
        abs_directory = os.path.abspath(directory)
        if not os.path.isdir(abs_directory):
            raise MyException(ErrorMessages.directory_not_exist.format(directory))
