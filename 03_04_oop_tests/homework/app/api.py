#!/usr/bin/env python
import datetime
import hashlib
import json
import logging
import os
import uuid
import yaml
from abc import ABC, abstractmethod, ABCMeta
from argparse import ArgumentParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from scoring import get_score, get_interests
from store import Store

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class MyException(BaseException):
    def __init__(self, *args, response=None, code=INVALID_REQUEST, **kwargs):
        self.response = response
        self.code = code
        super().__init__(*args, **kwargs)


class Field(ABC):
    def __init__(self, required: bool = False, nullable: bool = False):
        self.required = required
        self.nullable = nullable
        self.field_name: str = None

    def __get__(self, instance, owner):
        return getattr(instance, '_' + self.field_name, None)

    def __set__(self, instance, value):
        setattr(instance, '_' + self.field_name, self.validate(value))

    def validate(self, value):
        """Валидируем и устанавливаем значение"""
        if self.nullable and value is None or value == '':
            return value
        elif not self.nullable and not value and value != 0:
            raise MyException(response='Param "{}" can\'t be empty'.format(self.field_name))
        else:
            return self._validate(value)

    @abstractmethod
    def _validate(self, value):
        """Для реализации в классах потомках для кастомной валидации"""
        return value

    def _check_type(self, value, type_, text=None):
        text = 'Value of param "{}" must be  "{}" type.' if not text else text
        if not isinstance(value, type_):
            raise MyException(response=text.format(self.field_name, type_.__name__))


class CharField(Field):
    def _validate(self, value):
        self._check_type(value, str)
        return value


class ArgumentsField(Field):
    def _validate(self, value):
        self._check_type(value, dict)
        return value


class EmailField(CharField):
    def _validate(self, value):
        super()._validate(value)
        if '@' not in value:
            raise MyException(response='Value "{}" of param "{}" should contain "@"'.format(value, self.field_name))
        return value


class PhoneField(Field):
    MSG_INT = 'Value "{}" of param "{}" should only contains numbers'
    MSG_TYPES = 'Value "{}" of param "{}" should be only str or int types'
    MSG_LENGTH = 'Value "{}" of param "{}" should be 11 symbols length'
    MSG_START_7 = 'Value "{}" of param "{}" should started with "7"'

    def _validate(self, value):
        original_value = value
        if isinstance(value, int):
            value = str(value)
        elif isinstance(value, str):
            try:
                int(value)
            except ValueError:
                raise MyException(response=self.MSG_INT.format(value, self.field_name))
        else:
            raise MyException(response=self.MSG_TYPES.format(value, self.field_name))
        if len(value) != 11:
            raise MyException(response=self.MSG_LENGTH.format(value, self.field_name))
        if not value.startswith('7'):
            raise MyException(response=self.MSG_START_7.format(value, self.field_name))
        return original_value


class DateField(Field):
    DATE_FORMAT = '%d.%m.%Y'

    MSG_FORMAT = 'The param "{}" must be in the format like this: "DD.MM.YYYY", but received "{}"'

    def _validate(self, value):
        self._check_type(value, str)
        try:
            value = datetime.datetime.strptime(value, self.DATE_FORMAT)
        except ValueError:
            raise MyException(response=self.MSG_FORMAT.format(self.field_name, value))
        return value


class BirthDayField(DateField):
    MSG_EXCEED = 'The BirthDayField "{}" must not exceed 70 years from current moment and be positive,' \
                 ' but there is "{}"'

    def _validate(self, value):
        value = super()._validate(value)
        now = datetime.datetime.now()
        delta = now.year - value.year
        if delta >= 70 or delta < 0:
            raise MyException(response=self.MSG_EXCEED.format(self.field_name, value))
        return value


class GenderField(Field):
    MSG_GENDERS = f'Gender must be one of the following:\n{GENDERS}'

    def _validate(self, value):
        self._check_type(value, int)
        if value not in GENDERS:
            raise MyException(response=self.MSG_GENDERS)
        return value


class ClientIDsField(Field):
    MSG_ERROR = 'All elements the list of param "{}" must be only "{}" type.'

    def _validate(self, value):
        self._check_type(value, list)
        for id_ in value:
            self._check_type(id_, int, text=self.MSG_ERROR)
        return value


class MetaRequest(ABCMeta):
    def __new__(mcs, c_name, bases, attrs):
        required_fields = set()
        fields = set()
        attr_to_create = {}
        for name, attr in attrs.items():
            if isinstance(attr, Field):
                fields.add(name)
                if attr.required:
                    required_fields.add(name)
                attr.field_name = name
            attr_to_create[name] = attr
        attr_to_create.update({
            '_required_fields': required_fields,
            '_fields': fields,
        })
        result = super().__new__(mcs, c_name, bases, attr_to_create)
        return result


class AbstractRequest(metaclass=MetaRequest):

    def __init__(self):
        self.validate_errors = {}

    def validate(self, **request_dict: dict):
        self.validate_errors = {}
        for f_name in self._fields:
            param = request_dict.pop(f_name, None)
            if param is None and f_name in self._required_fields:
                self.validate_errors[f_name] = 'Missing required field in the request'
            try:
                setattr(self, f_name, param)
            except MyException as e:
                self.validate_errors[f_name] = e.response
        if len(request_dict) != 0:
            text = 'There are still exist some unused keys in the request params like:\n{}'
            self.validate_errors['general'] = text.format(request_dict.keys())
        return not self.validate_errors

    @abstractmethod
    def get_request_result(self, *args, **kwargs):
        """Метод для того, чтобы непосредственно получить результат вызова"""
        pass

    def dump(self, not_null=False):
        """Дампим декларированные поля в dict"""
        result = {}
        for name in self._fields:
            try:
                value = getattr(self, name)
                if not_null and not value and value != 0:
                    continue
                result[name] = value
            except AttributeError:
                continue
        return result


class ClientsInterestsRequest(AbstractRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def get_request_result(self, user_is_admin: bool, ctx: dict, store):
        self.client_ids: list
        ctx["nclients"] = len(self.client_ids)
        result = {}
        for id_ in self.client_ids:
            # В задании указано, что ключ должен в str
            result[str(id_)] = get_interests(store, id_)
        return result, OK


class OnlineScoreRequest(AbstractRequest):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    PAIRS = (('first_name', 'last_name'), ('email', 'phone'), ('gender', 'birthday'))

    def validate(self, **request_dict: dict):
        if super().validate(**request_dict):
            arguments = set(self.dump(not_null=True).keys())
            not_pair = True
            for pair in self.PAIRS:
                if not set(pair).difference(arguments):
                    not_pair = False
                    break
            if not_pair:
                text = 'There have to be at leas one pair of parameters: "{}", but there are only "{}"'
                self.validate_errors['request_special'] = text.format(self.PAIRS, str(arguments))
        return not self.validate_errors

    def get_request_result(self, user_is_admin: bool, ctx: dict, store):
        arguments = self.dump()
        # Предполагаем, что пустые явно заданные значения тоже надо вернуть
        ctx['has'] = [arg for arg, value in arguments.items() if value is not None]
        if user_is_admin:
            result = 42
        else:
            result = get_score(store, **arguments)
        return {"score": result}, OK


class MethodRequest(AbstractRequest):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    METHODS_ROUTER = {
        'online_score': OnlineScoreRequest,
        'clients_interests': ClientsInterestsRequest,
    }

    def __init__(self):
        super().__init__()
        self.method_class = None

    def validate(self, **request_dict: dict):
        super().validate(**request_dict)
        self.method: str
        if not self.method or self.method not in self.METHODS_ROUTER:
            self.validate_errors['request_special'] = 'Wrong method ' + str(self.method)
        elif self.method:
            self.method_class = self.METHODS_ROUTER[self.method]
        return not self.validate_errors

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    def get_request_result(self, ctx: dict, store):
        self.arguments: dict
        ctx.clear()
        subrequest: AbstractRequest = self.method_class()
        if not subrequest.validate(**self.arguments):
            raise MyException(response=subrequest.validate_errors)

        return subrequest.get_request_result(self.is_admin, ctx, store)


def check_auth(request):
    if request.is_admin:
        bytes_ = (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')
        digest = hashlib.sha512(bytes_).hexdigest()
    else:
        bytes_ = (request.account + request.login + SALT).encode('utf-8')
        digest = hashlib.sha512(bytes_).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    try:
        body = request.pop('body', None)
        if not body:
            raise MyException(code=INVALID_REQUEST)
        method_request = MethodRequest()
        if not method_request.validate(**body):
            raise MyException(response=method_request.validate_errors)
        if not check_auth(method_request):
            raise MyException(code=FORBIDDEN)
        return method_request.get_request_result(ctx, store)
    except MyException as e:
        if e.response is not None:
            logging.error(e.response)
        return e.response, e.code


class Config:

    def __init__(self, cache_connection_settings: Dict[str, Any], store_connection_settings: Dict[str, Any],
                 retry_count: int):
        self.cache_connection_settings = cache_connection_settings
        self.store_connection_settings = store_connection_settings
        self.retry_count = retry_count


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler,
    }
    store: Store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


def get_config(path: str) -> Config:
    with open(path) as config_file:
        logging.info('Open file {}'.format(path))
        return yaml.load(config_file)


def get_args():
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    parser.add_argument('-c', '--config', required=True, help='Path to the config file, must be filled.',
                        type=os.path.abspath)

    return parser.parse_args()


def main(args=None):
    if not args:
        args = get_args()
    config = get_config(args.config)

    logging.basicConfig(filename=args.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

    MainHTTPHandler.store = Store(cache_kwargs=config.cache_connection_settings,
                                  store_kwargs=config.store_connection_settings,
                                  retry_count=config.retry_count)
    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
