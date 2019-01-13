from unittest import mock

import datetime
import random
from unittest.mock import call

import api
from api import MyException, Field as OriginalField, GENDERS, AbstractRequest as OriginalAbstractRequest
import pytest


class Field(OriginalField):
    def _validate(self, value):
        return super()._validate(value)


class Test_Field__get__:
    @pytest.mark.parametrize('field_name, attr_name, return_value', [
        ('_test', '__test', '_test'),
        ('_test', '_test', None),
    ])
    def test(self, field_name, attr_name, return_value):
        f = Field()
        f.field_name = field_name
        setattr(f, attr_name, return_value)
        assert f.__get__(f, Field) == return_value


class Test_Field__set__:
    VALUE = 'test'

    @mock.patch.object(Field, 'validate', autospec=True, return_value=VALUE)
    def test(self, mock_validate):
        f = Field()
        f.field_name = self.VALUE
        f.__set__(f, self.VALUE)

        assert getattr(f, '_' + self.VALUE) == self.VALUE
        mock_validate.assert_called_with(f, self.VALUE)


@pytest.fixture
def mock__validate():
    m = mock.patch.object(Field, '_validate', autospec=True)
    yield m.start()
    m.stop()


class Test_Field_validate:
    def test_exception(self, mock__validate):
        f = Field(nullable=False)

        with pytest.raises(MyException):
            f.validate(None)
        mock__validate.assert_not_called()

    @pytest.mark.parametrize('value, return_value', [
        (None, None),
        ('', ''),
    ])
    def test_return_empty(self, mock__validate, value, return_value):
        f = Field(nullable=True)

        assert f.validate(value) == return_value
        mock__validate.assert_not_called()

    def test__validate_call(self, mock__validate):
        value = 'test'
        mock__validate.return_value = value
        f = Field()

        assert f.validate(value) == value
        mock__validate.assert_called_once_with(f, value)


class Test_Field__validate:
    def test(self):
        f = Field()
        value = 'test'

        assert f._validate(value) == value


class Test_Field__check_type:
    def test(self):
        f = Field()

        assert f._check_type(None, type(None)) is None

    def test_exception(self):
        f = Field()

        with pytest.raises(MyException):
            f._check_type(None, str)

    def test_exception_custom_text(self):
        f = Field()
        value = 'test'

        with pytest.raises(MyException, message=value):
            f._check_type(None, str, text=value)


class Test_CharField__validate:
    def test(self):
        f = api.CharField()

        assert f._validate('test') == 'test'


class Test_ArgumentsField__validate:
    def test(self):
        f = api.ArgumentsField()

        assert f._validate({}) == {}


class Test_EmailField__validate:
    def test_success(self):
        f = api.EmailField()
        value = 'ddsf@example.com'

        assert f._validate(value) == value

    def test_exception(self):
        f = api.EmailField()

        with pytest.raises(MyException):
            f._validate('test')


class Test_PhoneField__validate:
    PHONE = 79454673987

    @pytest.mark.parametrize('input', [
        PHONE,
        str(PHONE),
    ])
    def test_success(self, input):
        f = api.PhoneField()

        assert f._validate(input) == input

    @pytest.mark.parametrize('input, msg_template', [
        ('test', api.PhoneField.MSG_INT),
        (None, api.PhoneField.MSG_TYPES),
        (PHONE * 10, api.PhoneField.MSG_LENGTH),
        ('89454673987', api.PhoneField.MSG_START_7),
    ])
    def test_exception(self, input, msg_template: str):
        f = api.PhoneField()
        f.field_name = 'test'

        with pytest.raises(MyException, message=msg_template.format(input, f.field_name)):
            f._validate(input)


class Test_DateField__validate:

    @mock.patch.object(api.DateField, '_check_type', autospec=True)
    def test_success(self, mock__check_type):
        f = api.DateField()
        value = '01.01.2000'

        assert f._validate(value) == datetime.datetime.strptime(value, f.DATE_FORMAT)
        mock__check_type.assert_called_once_with(f, value, str)

    def test_exception(self):
        f = api.DateField()
        value = 'test'
        f.field_name = value

        with pytest.raises(MyException, message=f.MSG_FORMAT.format(value, value)):
            f._validate(input)


class Test_BirthDayField__validate:
    mock_date = datetime.datetime.now()

    old_mock_date = datetime.datetime(mock_date.year - 71, mock_date.month, mock_date.day)

    @mock.patch.object(api.DateField, '_validate', autospec=True, return_value=mock_date)
    def test_success(self, mock__validate):
        f = api.BirthDayField()
        value = '01.01.2000'

        assert f._validate(value) == self.mock_date
        mock__validate.assert_called_once_with(f, value)

    @mock.patch.object(api.DateField, '_validate', autospec=api.BirthDayField._validate, return_value=old_mock_date)
    def test_exception(self, mock__validate):
        f = api.BirthDayField()
        value = 'test'
        f.field_name = value

        with pytest.raises(MyException, message=f.MSG_EXCEED.format(value, value)):
            f._validate(value)


class Test_GenderField__validate:
    @mock.patch.object(api.GenderField, '_check_type', autospec=True)
    @pytest.mark.parametrize('gender', [g for g in GENDERS.keys()])
    def test_success(self, mock__check_type, gender):
        f = api.GenderField()

        assert f._validate(gender) == gender
        mock__check_type.assert_called_once_with(f, gender, int)

    @mock.patch.object(api.GenderField, '_check_type', autospec=True)
    def test_exception(self, mock__check_type):
        f = api.GenderField()
        gender = -1

        with pytest.raises(MyException, message=f.MSG_GENDERS):
            f._validate(gender)
        mock__check_type.assert_called_once_with(f, gender, int)


class Test_ClientIDsField__validate:
    @mock.patch.object(api.ClientIDsField, '_check_type', autospec=True)
    def test_success(self, mock__check_type):
        f = api.ClientIDsField()
        _id = 1
        value = [_id]
        calls = (call(f, value, list), call(f, _id, int, text=f.MSG_ERROR))

        assert f._validate(value) == value
        assert mock__check_type.call_count == 2
        mock__check_type.assert_has_calls(calls)


# AbstractRequest tests

class AbstractRequest(OriginalAbstractRequest):
    def get_request_result(self, *args, **kwargs):
        super().get_request_result()


class Test_AbstractRequest_validate:
    ERROR_TEXT = 'test_error'
    ERRORS_DICT = {
        'required': 'test_error',
        'test': 'test_error',
        'general': "There are still exist some unused keys in the request params like:\ndict_keys(['unwanted'])",
    }

    @mock.patch('api.setattr', side_effect=MyException(response=ERROR_TEXT))
    def test(self, mock_setattr):
        r = mock.MagicMock()
        r._fields = ('required', 'test')
        r._required_fields = ('required',)
        request_dict = {
            'test': 'test',
            'unwanted': 'unwanted',
        }
        calls = (call(r, 'required', None), call(r, 'test', 'test'))

        assert not AbstractRequest.validate(r, **request_dict)
        assert r.validate_errors == self.ERRORS_DICT
        assert mock_setattr.call_count == 2
        mock_setattr.assert_has_calls(calls)


class Test_AbstractRequest_dump:

    @mock.patch('api.getattr', side_effect=(None, 'test', AttributeError))
    def test(self, mock_getattr):
        r = mock.MagicMock()
        r._fields = ('required', 'test', 'attr_error')
        result = {'test': 'test'}
        calls = [call(r, name) for name in r._fields]

        assert AbstractRequest.dump(r, not_null=True) == result
        assert mock_getattr.call_count == 3
        mock_getattr.assert_has_calls(calls)


class Test_ClientsInterestsRequest_get_request_result:

    @mock.patch('api.get_interests', return_value='test', autospec=True)
    def test(self, mock_get_interests):
        r = mock.create_autospec(api.ClientsInterestsRequest)
        r.client_ids = (1, 2)
        result = {'1': 'test', '2': 'test'}, 200
        ctx = {}
        store = 'test_store'
        calls = [call(store, id_) for id_ in r.client_ids]

        assert api.ClientsInterestsRequest.get_request_result(r, True, ctx, store) == result
        assert mock_get_interests.call_count == 2
        mock_get_interests.assert_has_calls(calls)


class Test_OnlineScoreRequest_validate:
    PAIRS = api.OnlineScoreRequest.PAIRS

    @mock.patch.object(api.AbstractRequest, 'validate', autospec=True, return_value=True)
    def test_success(self, mock_validate):
        request_dict = {pair: '' for pair in self.PAIRS[0]}
        r = mock.create_autospec(api.OnlineScoreRequest)
        r.dump.return_value = request_dict
        r.PAIRS = self.PAIRS
        r.validate_errors = {}

        assert api.OnlineScoreRequest.validate(r, **request_dict)
        mock_validate.assert_called_once()
        assert r.validate_errors == {}

    @mock.patch.object(api.AbstractRequest, 'validate', autospec=True, return_value=True)
    def test_errors(self, mock_validate):
        request_dict = {'test': 'test'}
        r = mock.create_autospec(api.OnlineScoreRequest)
        r.dump.return_value = request_dict
        r.PAIRS = api.OnlineScoreRequest.PAIRS
        r.validate_errors = {}
        result_errors = {
            'request_special': 'There have to be at leas one pair of parameters: "'
                               '((\'first_name\', \'last_name\'), (\'email\', \'phone\'), '
                               '(\'gender\', \'birthday\'))", but there are only "{\'test\'}"'
        }

        assert not api.OnlineScoreRequest.validate(r, **request_dict)
        mock_validate.assert_called_once()
        assert r.validate_errors == result_errors


class Test_OnlineScoreRequest_get_request_result:
    SCORE_RESULT = 10

    @mock.patch('api.get_score', return_value=SCORE_RESULT, autospec=True)
    @pytest.mark.parametrize('user_is_admin, output, call_count', [
        (True, 42, 0),
        (False, SCORE_RESULT, 1),
    ])
    def test(self, mock_get_score, user_is_admin, output, call_count):
        r = mock.create_autospec(api.OnlineScoreRequest)
        r.dump.return_value = {'phone': 'test', 'email': 'test'}
        r.client_ids = (1, 2)
        result = {'score': output}, 200
        ctx = {}
        store = 'test_store'

        assert api.OnlineScoreRequest.get_request_result(r, user_is_admin, ctx, store) == result
        assert mock_get_score.call_count == call_count
