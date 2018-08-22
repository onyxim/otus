import gzip
import logging
import re
import time as sys_time
from statistics import median

from lib_errors import ErrorMessages

NGINX_LINE_LOG_RE = r"""
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
"""
regex_line_from_log = re.compile(NGINX_LINE_LOG_RE, re.VERBOSE)


class EmptyReqData:
    def __init__(self):
        self.count = 0
        self.time_list = []
        self.time_sum = 0


TRIPLE_NONE = (None, None, None)


def analyze_line(line):
    result = regex_line_from_log.match(line)
    if result:
        d = result.groupdict()
        return d['url'], float(d['time']), ''
    else:
        logging.error(ErrorMessages.line_not_matched + line)
        return '', '', line


def get_line(log):
    open_func = gzip.open if log.ext == '.gz' else open
    try:
        with open_func(log.log_file_path, mode='rt', encoding="utf-8") as log_file:
            for line in log_file:
                yield analyze_line(line)

    except ValueError:
        logging.error(ErrorMessages.log_encoding_error.format(log.log_file_path))
        return TRIPLE_NONE
    except OSError:
        logging.error(ErrorMessages.log_file_open_problem.format(log.log_file_path))
        return TRIPLE_NONE


def analyze_log(log, parse_success_threshold_percent, max_time_parsing_for_log, **kwargs):
    parsed_data = {}
    parsed_count = 0
    unparsed_count = 0
    sum_all_time = 0
    max_time = sys_time.time() + max_time_parsing_for_log
    for url, time, line in get_line(log):
        if url:
            req_data = parsed_data.setdefault(url, EmptyReqData())
            req_data.count += 1
            req_data.time_list.append(time)
            sum_all_time += time
            parsed_count += 1
        elif not line:
            # Как правило что-то вроде 400 ответа, где нет никакого запроса, скипаю без учета в количестве
            continue
        elif line:
            unparsed_count += 1
        elif url is None and time is None and line is None:
            # Значит есть ошибка в парсинге, требуется прекратить дальнейший анализ лога
            return TRIPLE_NONE

        if sys_time.time() > max_time:
            logging.error(ErrorMessages.parsing_time_exceeded.format(max_time_parsing_for_log, log.log_file_path))
            return TRIPLE_NONE
    if not parsed_data:
        return TRIPLE_NONE
    parse_threshold_result = int(round(parsed_count * 100 / (parsed_count + unparsed_count), 0))
    if parse_threshold_result >= parse_success_threshold_percent:
        return parsed_data, parsed_count + unparsed_count, round(sum_all_time, 3)
    else:
        logging.error(ErrorMessages.threshold_not_reached.format(parse_threshold_result,
                                                                 parse_success_threshold_percent))
        return TRIPLE_NONE


def get_stat_data(log, report_size, **kwargs):
    parsed_data, count_all_reqs, sum_time_all_reqs = analyze_log(log, **kwargs)
    if not parsed_data:
        return None
    stat_data = []
    for url, data_obj in parsed_data.items():
        # Приходится проходить цикл, чтобы пересчитать общие суммы и отфильтровать запросы на которых суммарно по
        # времени не набирается порог
        time_sum = sum(data_obj.time_list)
        if time_sum < report_size:
            count_all_reqs -= data_obj.count
            sum_time_all_reqs -= time_sum
            continue
        data_obj.time_sum = time_sum
        count = data_obj.count
        time_list = data_obj.time_list
        stat_data.append({
            'url': url,
            'count': count,
            'time_sum': round(time_sum, 3),
            'time_med': round(median(time_list), 3),
            'time_avg': round(time_sum / count, 3),
            'time_max': round(max(time_list), 3),
        })
    for data in stat_data:
        count = data['count']
        time_sum = data['time_sum']
        data.update({
            'count_perc': round(count * 100 / count_all_reqs, 2),
            'time_perc': round(time_sum * 100 / sum_time_all_reqs, 2),
        })
    return stat_data
