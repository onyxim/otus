#!/usr/bin/env python
import datetime
import hashlib
import json
import logging
import uuid
from abc import ABC, abstractmethod, ABCMeta
from http.server import HTTPServer, BaseHTTPRequestHandler
from optparse import OptionParser

from scoring import get_score, get_interests

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


class MyException(Exception):
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
        try:
            return getattr(instance, '_' + self.field_name)
        except AttributeError:
            return None

    def __set__(self, instance, value):
        setattr(instance, '_' + self.field_name, self.validate(value))
        pass

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
    def _validate(self, value):
        original_value = value
        if isinstance(value, int):
            value = str(value)
        elif isinstance(value, str):
            try:
                int(value)
            except ValueError:
                raise MyException(response='Value "{}" of param "{}" should only contains numbers'
                                  .format(value, self.field_name))
        if len(value) != 11:
            raise MyException(response='Value "{}" of param "{}" should be 11 symbols length'
                              .format(value, self.field_name))
        if not value.startswith('7'):
            raise MyException(response='Value "{}" of param "{}" should started with "7"'
                              .format(value, self.field_name))
        return original_value


class DateField(Field):
    def _validate(self, value):
        self._check_type(value, str)
        try:
            value = datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            raise MyException(response='The param "{}" must be in the format like this:'
                                       ' "DD.MM.YYYY", but received "{}"'.format(self.field_name, value))
        return value


class BirthDayField(DateField):
    def _validate(self, value):
        value = super()._validate(value)
        now = datetime.datetime.now()
        delta = now.year - value.year
        if delta >= 70 or delta < 0:
            raise MyException(response='The BirthDayField "{}" must not exceed 70 years from current moment'
                                       ' and be positive, but there is "{}"'.format(self.field_name, value))
        return value


class GenderField(Field):
    def _validate(self, value):
        if value not in GENDERS:
            raise MyException(response='Gender must be one of the following:\n{}'.format(GENDERS))
        return value


class ClientIDsField(Field):
    def _validate(self, value):
        self._check_type(value, list)
        for id_ in value:
            self._check_type(id_, int, text='All elements the list of param "{}" must be only "{}" type.')
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
    _required_fields = set()
    _fields = set()

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
            self.validate_errors[
                'general'] = 'There are still exist some unused keys in the request params like:\n{}'.format(
                request_dict.keys())
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
        super().validate(**request_dict)
        arguments = set(self.dump(not_null=True).keys())
        not_pair = True
        for pair in self.PAIRS:
            if not set(pair).difference(arguments):
                not_pair = False
                break
        if not_pair:
            self.validate_errors['request_special'] = 'There have to be at leas one pair of parameters: "{}", ' \
                                                      'but there are only "{}"'.format(self.PAIRS, str(arguments))
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


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

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
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    opts, args = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
