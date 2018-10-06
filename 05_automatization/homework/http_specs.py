import re


class HttpResponse:
    code: int = None
    name: str = None


class OK(HttpResponse):
    code = 200
    name = 'OK'


class HttpException(Exception, HttpResponse):
    pass


class BadRequest(HttpException):
    code = 400
    name = 'Bad Request'


class Forbidden(HttpException):
    code = 403
    name = 'Forbidden'


class NotFound(HttpException):
    code = 404
    name = 'Not Found'


class MethodNotAllowed(HttpException):
    code = 405
    name = 'Method Not Allowed'


class InternalServerError(HttpException):
    code = 500
    name = "Internal Server Error"


CONTENT_TYPES = {
    '.swf': 'application/x-shockwave-flash',
    '.gif': 'image/gif',
    '.png': 'image/png',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    'default': 'text/plain',
}

RESPONSE = """\
HTTP/1.1 {code} {code_text}\r
Date: {date}\r
Server: Otus HTTP alpha server\r
"""
RESPONSE_CONTENT = "Content-Length: {}\r\nContent-Type: {}\r\n"

GET = 'GET'
HEAD = 'HEAD'

ALLOWED_HTTP_METHODS = (GET, HEAD)
OTHER_HTTP_METHODS = ('OPTIONS', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT')

HTTP_PROTOCOL_FIRST_LINE_RE = rf"""
^
(?P<method>{'|'.join(ALLOWED_HTTP_METHODS+OTHER_HTTP_METHODS)})\s       # All allowed HTTP methods
/(?P<path>\S+)\s                                                        # Request path without leading slash
HTTP/1\.[10]                                                               # HTTP standard just before a new line
$
"""

re_http_protocol_first_line = re.compile(HTTP_PROTOCOL_FIRST_LINE_RE, re.VERBOSE)

HTTP_PATH_RE = r"""
^(?P<path>[\S\s]+?          # named group for path non greedy mod
(?P<ext>
\.[^\.\W]{2,4})?    # named for extension contains from 3 to 4 elements with leading dot and not contain additional dots
)                       # end named group for path

(?:\?                   # start of optional query string, should contain "?"
(?:                     
\w+=\w+                     # param from query string
&?)*                    # may be ended with "&" and repeated many times
)?                      # it may be not any params
$
"""

re_http_path = re.compile(HTTP_PATH_RE, re.VERBOSE)

HTTP_FIELD_VALUE = r"""
^
(?<field>)
"""
