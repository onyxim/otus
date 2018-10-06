import argparse
import asyncio
import datetime
import logging
import multiprocessing
import os
import signal
import sys
import urllib.parse
from asyncio import StreamReader, StreamWriter, IncompleteReadError
from functools import partial
from multiprocessing import Process
from time import sleep

from http_specs import RESPONSE, re_http_protocol_first_line, ALLOWED_HTTP_METHODS, HttpResponse, BadRequest, \
    MethodNotAllowed, HttpException, Forbidden, NotFound, re_http_path, OK, CONTENT_TYPES, HEAD, InternalServerError, \
    RESPONSE_CONTENT

logging.basicConfig(level=logging.INFO, format='%(asctime)s [PID:%(process)d] %(message)s')


def validate_head(head: bytes):
    first = True
    for line in head.split(b'\r\n'):
        try:
            line = line.decode()
        except UnicodeDecodeError:
            raise BadRequest('Request should be utf-8 encoded.')
        if first:
            result = re_http_protocol_first_line.match(line)
            if not result:
                raise BadRequest('It\s not valid first line in http request')
            method = result.group('method')
            path = urllib.parse.unquote(result.group('path'))
            if method not in ALLOWED_HTTP_METHODS:
                raise MethodNotAllowed(f'Method "{method}" not allowed or implemented.\n'
                                       f'Only "{"|".join(ALLOWED_HTTP_METHODS)}" allowed')
            first = False
            break
        else:
            # Здесь могла бы быть валидация других полей из HEAD http запроса, если необходимо, могу сделать.
            pass
    return method, path


def format_response(response: HttpResponse, content_type=None, content_length=0):
    response = RESPONSE.format(
        code=response.code,
        code_text=response.name,
        date=datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
    )
    if content_type and content_length:
        response = response + RESPONSE_CONTENT.format(content_length, content_type)
    return response + "\r\n"


def get_file(document_root, path):
    path = urllib.parse.unquote(path)
    result = re_http_path.match(path)
    if result is None:
        raise BadRequest(f'Wrong path "{path}" in http request')
    path = result.group('path')
    ext = result.group('ext')
    content_type = CONTENT_TYPES['default']
    if ext:
        content_type = CONTENT_TYPES.get(ext, content_type)
    end_with_slash = path.endswith('/')
    if not ext and not end_with_slash:
        raise BadRequest(f'Wrong path "{path}" in http request')
    if end_with_slash:
        path = path + "index.html"
        content_type = CONTENT_TYPES['.html']
    abs_path = os.path.abspath(os.path.join(document_root, path))
    if document_root not in abs_path:
        raise Forbidden('Directory escaping from document root are not allowed.')
    try:
        file_size = os.path.getsize(abs_path)
    except OSError:
        raise NotFound('Can\'t find requested file in document root')
    with open(abs_path, mode='br') as file:
        file_data = file.read()
    return file_size, file_data, content_type


async def handle_request(reader: StreamReader, writer: StreamWriter, read_timeout=0, document_root='', sleep_time=0,
                         **kwargs):
    file_data: bytes = b""
    method = ''
    try:
        try:
            head: bytes = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), timeout=read_timeout)
        except TimeoutError:
            raise BadRequest('Wait too long to get http request.')
        except IncompleteReadError:
            logging.info('Empty request.')
            return None
        method, path = validate_head(head)
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        file_size, file_data, content_type = await loop.run_in_executor(None, partial(get_file, document_root, path))
        response = format_response(OK, content_type, file_size)
    except HttpException as e:
        response = format_response(e)
    except Exception as e:
        logging.exception('Some error occurred.')
        response = format_response(InternalServerError)

    addr = writer.get_extra_info('peername')
    logging.info(f"Received {head.decode()} from {addr!r}")
    logging.info(f"Send: {response}")
    writer.write(response.encode())
    if method == HEAD:
        file_data = None
    if file_data:
        writer.write(file_data)
    await writer.drain()
    writer.close()
    logging.info("The connection was closed")
    sleep(sleep_time)


async def start_server(*args, port: int = None, host: str = '', **kwargs):
    handle_request_mod = partial(handle_request, **kwargs)
    server = await asyncio.start_server(
        handle_request_mod, host, port, reuse_port=True)
    addr = server.sockets[0].getsockname()
    logging.info(f'Serving on {addr}\nPID for worker is {os.getpid()}')
    async with server:
        await server.serve_forever()


def worker_main(*args, **kwargs):
    asyncio.run(start_server(*args, **kwargs))


def start_worker(*args, **kwargs):
    p = Process(target=worker_main, args=args, kwargs=kwargs)
    p.start()
    return p


class CleanChildProcesses:
    def __enter__(self):
        os.setpgrp()  # create new process group, become its leader

    def __exit__(self, type, value, traceback):
        os.killpg(0, signal.SIGINT)  # kill all processes in my group


def parse_args():
    parser = argparse.ArgumentParser(description='HTTP async web server.')
    parser.add_argument('-w', '--workers', type=int, default=multiprocessing.cpu_count(), dest='workers',
                        help='Number of workers used to work with server.')

    parser.add_argument('-c', '--checkalive', type=int, default=10, dest='checkalive',
                        help='Timeout to check that workers processes is alive. ')
    parser.add_argument('-rt', '--read_timeout', type=int, default=5, dest='read_timeout',
                        help='Set timeout to read for a request.')
    parser.add_argument('-r', '--document_root', dest='document_root', required=True, type=os.path.abspath,
                        help='Root folder from which will be serve data.')
    parser.add_argument('-p', '--port', dest='port', type=int, default=8080,
                        help='Port for listening web server.')
    parser.add_argument('--host', dest='host', type=str, default='', help='Host for listening web server.')
    return vars(parser.parse_args())


if __name__ == "__main__":
    args = parse_args()
    workers = args.pop('workers')
    document_root = args['document_root']
    checkalive = args.pop('checkalive')
    if not os.path.isdir(document_root):
        logging.error(f'Document root "{document_root}" doesn\'t exist')
        sys.exit(1)
    logging.info(f"Use {workers} workers for server.")
    processes = {}
    start_worker_mod = partial(
        start_worker,
        **args,
    )
    with CleanChildProcesses():
        for n in range(workers):
            if n == 0:
                args.copy().update({'sleep_time': 10})
                sleep_worker = partial(
                    start_worker,
                    **args,
                )
                processes['worker_' + str(n)] = sleep_worker()
                continue
            processes['worker_' + str(n)] = start_worker_mod()
        while True:
            sleep(checkalive)
            for name, p in processes.copy().items():
                if not p.is_alive():
                    processes[name] = start_worker_mod()
