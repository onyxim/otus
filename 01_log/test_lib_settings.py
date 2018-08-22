import unittest
from configparser import ConfigParser

from lib_settings import check_config, ErrorMessages, DEFAULT_SECTION_NAME, SettingsKeys
from log_analyzer import DEFAULT_SETTINGS, MyException


class Test_check_config(unittest.TestCase):
    WRONG_SECTIONS = ['wrong', 'wrong2']

    def assertErrorMSG(self, *args, msg='', f=None, ex=MyException):
        try:
            f(*args)
        except ex as e:
            self.assertEqual(str(e), msg)

    def test_no_and_two(self):
        c = ConfigParser()
        self.assertErrorMSG(c, f=check_config, msg=ErrorMessages.no_section)
        for section in self.WRONG_SECTIONS:
            c.add_section(section)
        self.assertErrorMSG(c, f=check_config, msg=ErrorMessages.more_than_one_error.
                            format(self.WRONG_SECTIONS, DEFAULT_SECTION_NAME))

    def test_wrong_section(self):
        c = ConfigParser()
        section = self.WRONG_SECTIONS[0]
        c.add_section(section)
        self.assertErrorMSG(c, f=check_config, msg=ErrorMessages.wrong_section_name.
                            format(section, DEFAULT_SECTION_NAME))

    WRONG_KEY = 'wrong'

    def test_wrong_keys_settings(self):
        c = ConfigParser()
        c.add_section(DEFAULT_SECTION_NAME)
        c[DEFAULT_SECTION_NAME][self.WRONG_KEY] = self.WRONG_KEY
        self.assertErrorMSG(c, f=check_config,
                            msg=ErrorMessages.not_in_allowed_keys.format({self.WRONG_KEY, }))

    def test_success_return(self):
        c = ConfigParser()
        c.add_section(DEFAULT_SECTION_NAME)
        test_dict = DEFAULT_SETTINGS.copy()
        test_dict[SettingsKeys.analyzer_log_file] = 'test_log'
        c[DEFAULT_SECTION_NAME] = {k: str(v) for k, v in test_dict.items()}
        self.assertDictEqual(test_dict, check_config(c))


if __name__ == '__main__':
    unittest.main()
