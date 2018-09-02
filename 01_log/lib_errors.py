class MyException(Exception):
    pass


class ErrorMessages:
    wrong_date_conversion = 'Date "{}" is invalid in filename "{}"'
    directory_not_exist = 'Directory "{}" not exist. Maybe it wrong?'
    log_encoding_error = 'There is an encoding error in the logfile "{}". File has to be properly utf-8 encoding. ' \
                         'Log file skipped.'
    log_file_open_problem = 'Can\'t open log file "{}". Going to the next one.'
    line_not_matched = 'Couldn\'t parse next line:\n'
    threshold_not_reached = 'The quality parsing threshold {} is not reached and currently is {}. Log file skipped.'
    probably_duplicate = 'There is already another file for the date "{}" has planned to parse. ' \
                         'Probably duplicate gz archive or plain log?'
    parsing_time_exceeded = 'Parsing time {} for the log "{}" exceeded. Going to the next one.'
