class MyException(Exception):
    pass


class ErrorMessages:
    more_than_one_error = 'There are {} more than one default section "{}" in the config file.'
    wrong_section_name = 'Section "{}" not equal to default section name "{}"'
    no_section = 'There is no a section in the config file or section is empty.'
    not_in_allowed_keys = 'There are not allowed keys {} in the config file.'
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
