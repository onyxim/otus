import logging
import os
import re
from collections import namedtuple
from datetime import datetime

from lib_errors import ErrorMessages, MyException

NGINX_LOG_NAME_RE = r"""
^nginx-access-ui.log-       # обязательный префикс
(?P<date>\d{8})             # дата, ровно 8 цифр подряд
(?P<ext>\.gz|\.log)$        # в конце либо .gz либо пусто
"""
regex_name = re.compile(NGINX_LOG_NAME_RE, re.VERBOSE)

REPORT_NAME_TEMPLATE = 'report-{}.html'

log_params = namedtuple('log_name', ('date_str', 'date', 'report_file_path', 'log_file_path', 'ext'))


def check_result_log_name(result, nginx_logs_path, reports_path, existed_reports):
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
    report_name = REPORT_NAME_TEMPLATE.format(date_str_report)
    # Можно конечно проверять наличие файла через os.path.isfile, но так не будет системного вызова
    if report_name in existed_reports:
        # Значит уже существует отчет на лог с полученным именем
        return False
    report_file_path = os.path.join(reports_path, report_name)
    nginx_file_path = os.path.join(nginx_logs_path, result.string)
    return log_params(date_str, log_date, report_file_path, nginx_file_path, re_dict['ext'])


def get_logs_names_to_parse(nginx_logs_path, reports_path):
    max_date = None
    logs_registry = {}
    existed_reports = set(os.listdir(reports_path))
    for entry in os.scandir(nginx_logs_path):
        if entry.is_dir():
            continue
        result = regex_name.match(entry.name)
        result = check_result_log_name(result, nginx_logs_path, reports_path, existed_reports)
        if not result:
            continue
        elif result.date in logs_registry:
            logging.error(ErrorMessages.probably_duplicate.format(result.date_str))
            continue
        logs_registry[result.date] = result
        if not max_date or result.date > max_date:
            max_date = result.date
    return logs_registry, max_date


def validate_dirs(*args):
    result = []
    for directory in args:
        # Прогоняем через abspath, чтобы решить проблему с trailing slash
        abs_directory = os.path.abspath(directory)
        if not os.path.isdir(abs_directory):
            raise MyException(ErrorMessages.directory_not_exist.format(directory))
        result.append(abs_directory)
    return result
