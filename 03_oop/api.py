#!/usr/bin/env python
import datetime
import hashlib
import json
import logging
import uuid
from abc import ABC, abstractmethod, ABCMeta
from copy import deepcopy
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
        self.value = None
        self.field_name: str = None

    def validate(self, value):
        """Валидируем и устанавливаем значение"""
        if self.nullable and value is None or value == '':
            self.value = value
        elif not self.nullable and not value and value != 0:
            raise MyException(response='Param "{}" can\'t be empty'.format(self.field_name))
        else:
            self.value = self._validate(value)

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
        fields = {}
        required_fields = set()
        attr_to_create = {}
        for name, attr in attrs.items():
            if not isinstance(attr, property) and isinstance(attr, Field):
                fields[name] = attr
                if attr.required:
                    required_fields.add(name)
                attr.field_name = name
            # Чтобы были лишь у инстансов класса
            elif name in ('_required_fields', '_fields'):
                continue
            else:
                attr_to_create[name] = attr
        attr_to_create.update({
            '_required_fields': required_fields,
            '_fields': fields,
        })
        result = super().__new__(mcs, c_name, bases, attr_to_create)
        return result


class AbstractRequest(metaclass=MetaRequest):
    _required_fields = set()
    _fields = {}

    def __init__(self, **request_dict: dict):
        """
        :param strict: Если будут ключи, в request_dict, которые не описаны в декларативной модели,
        будет вызвана ошибка
        """
        for f_name, field_obj in self._fields.items():
            param = request_dict.pop(f_name, None)
            if param is None:
                if f_name in self._required_fields:
                    raise MyException(response='Missing required field "{}" in the request'.format(f_name))
            # deepcopy, чтобы избежать проблем с использованием одних и тех же объектов в атрибутах разных инстансов
            field_obj: Field = deepcopy(field_obj)
            field_obj.validate(param)
            setattr(self, f_name, field_obj)
        if len(request_dict) != 0:
            raise MyException(response='There are still exist some unused keys in the request '
                                       'params like:\n{}'.format(request_dict.keys()))

    @abstractmethod
    def get_request_result(self, *args, **kwargs):
        """Метод для того, чтобы непосредственно получить результат вызова"""
        pass

    def dump(self, not_null=False):
        """Дампим декларированные поля в dict"""
        result = {}
        for name in self._fields.keys():
            try:
                value = getattr(self, name)
                if not_null and not value and value != 0:
                    continue
                result[name] = value
            except AttributeError:
                continue
        return result

    # Да, я знаю как и что можно было сделать через дескрипторы с сохранением значений в инстансах классов. Но,
    # решил попрактиваться и реализовать что-то вроде протокола дескрипторов для инстансов.
    def __getattribute__(self, item):
        if item != '_fields' and item in object.__getattribute__(self, '_fields').keys():
            field_obj: Field = object.__getattribute__(self, item)
            return field_obj.value
        else:
            return object.__getattribute__(self, item)

    def __setattr__(self, key, value):
        fields = object.__getattribute__(self, '_fields')
        if key in fields.keys():
            try:
                field_obj: Field = object.__getattribute__(self, key)
                field_obj.validate(value)
            except AttributeError:
                if not isinstance(value, Field):
                    field_obj: Field = deepcopy(fields[key]).validate(value)
                    field_obj.validate(value)
                else:
                    field_obj = value
                object.__setattr__(self, key, field_obj)

        else:
            object.__setattr__(self, key, value)


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

    def __init__(self, **request_dict):
        super().__init__(**request_dict)
        arguments = set(self.dump(not_null=True).keys())
        not_pair = True
        for pair in self.PAIRS:
            if not set(pair).difference(arguments):
                not_pair = False
                break
        if not_pair:
            raise MyException(response='There have to be at leas one pair of parameters: "{}", but there are only "{}"'
                              .format(self.PAIRS, arguments))

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

    def __init__(self, request_dict: dict):
        super().__init__(**request_dict)
        self.method: str
        if self.method not in self.METHODS_ROUTER:
            raise MyException(response='Wrong method ' + self.method)
        self.method_class = self.METHODS_ROUTER[self.method]

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    def get_request_result(self, ctx: dict, store):
        self.arguments: dict
        ctx.clear()
        return self.method_class(**self.arguments).get_request_result(self.is_admin, ctx, store)


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
        method_request = MethodRequest(body)
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
