# Created by lujin at 10/12/2017
import inspect
import logging

import asyncio
import httptools
from httptools import HttpParserError
from littleweb.http import HttpRequest, HttpResponse
from littleweb import utils


class HttpProtocol(asyncio.Protocol):
    def __init__(self, *, router, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._router = router
        self.transport = None
        self._http_parser = None
        self._request = None
        self._headers = None
        self._url = None
        self.body_arguments = {}
        self.query_arguments = {}
        self.url_source = None
        self.body = []
        self._version = '1.1'

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        logging.exception(exc)
        self.transport = self._request = self._http_parser = None
        self.body_arguments = {}

    def data_received(self, data):
        if self._http_parser is None:
            assert self._http_parser is None
            self._http_parser = httptools.HttpRequestParser(self)
            self._headers = {}

        try:
            self._http_parser.feed_data(data)
        except HttpParserError as e:
            # todo 现在不处理这种异常，如果socket中传入的数据出现问题
            logging.exception(e)
            self.write('Bad Request', 400)

    # ### httptools method start
    def on_url(self, url):
        if not self._url:
            self._url = url
        else:
            self._url += url

    def on_header(self, name, value):
        self._headers[name.decode()] = value.decode()

    def on_headers_complete(self):
        print('on_headers_complete')
        self._version = self._http_parser.get_http_version()

    def on_body(self, body):
        print('on body: ', body)
        self.body.append(body)

    def on_message_complete(self):
        print('on_message_complete')
        asyncio.ensure_future(self.match_handler(), loop=self._loop)

    def on_chunk_header(self):
        print('on_chunk_header')

    def on_chunk_complete(self):
        print('on_chunk_complete')

    # ### httptools method end

    async def match_handler(self):
        method = self._http_parser.get_method().upper().decode()
        method_queue = self._router.get_method_queue(method)

        for url_pattern, handler in method_queue:
            match = url_pattern.match(self._url.decode('utf-8'))
            if match:
                args = match.groups()
                # todo 这里好像没法处理在在类中的方法，因为缺少一个类的实例参数...
                if handler and callable(handler):
                    if not asyncio.iscoroutinefunction(handler) and not inspect.isgeneratorfunction(handler):
                        handler = asyncio.coroutine(handler)
                self._request = HttpRequest(
                    self.transport, self._url, self._headers, self._version, b''.join(self.body))
                http_response = HttpResponse(self)
                await handler(self._request, http_response, *args)
                break
        else:
            self.write(b'Page Not Found', 404)

    def close(self):
        if self.transport:
            self.transport.close()
            self.transport = None

    def write(self, data, status_code=200, content_type='text/plain', headers=None):
        if headers is None:
            headers = {}
        headers = dict(headers, **{
            'Content-Type': content_type,
            'Content-Length': len(data),
        })

        encode_headers = b''.join([('{}: {}\r\n'.format(name, value)).encode(
            'latin-1') for name, value in headers.items()])

        try:
            self.transport.write(b''.join([
                self._status_line(status_code),
                encode_headers,
                b'\r\n',
                data
            ]))
        except Exception as e:
            logging.error(
                'Write response data failed, connection closed %s', e)
        finally:
            self.close()

    def _status_line(self, status_code):
        status_text = utils.STATUS_CODE.get(status_code, 'UNKOWN')
        return ('HTTP/%s %s %s\r\n' % (self._version, status_code, status_text)).encode('latin-1')
