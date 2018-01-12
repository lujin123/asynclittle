# Created by lujin at 10/12/2017
import json
import logging
import socket

import httptools
from littleweb.error import MissingArgumentError
from littleweb.utils import parse_body_arguments, parse_qs_bytes


class HttpRequest:
    _ARG_DEFAULT = object()

    def __init__(self, transport, url, headers, version, body):
        self.transport = transport
        self._headers = headers
        self.version = version
        self._body = body
        self._parsed_url = httptools.parse_url(url)

        self._query_arguments = None
        self._body_arguments = None
        self._json_arguments = None

        self._socket = None
        self._ip = None
        self._port = None
        self._remote_addr = None

    def _parse_query_args(self):
        query = self._parsed_url.query
        return parse_qs_bytes(query.decode('utf-8')) if query else {}

    def _parse_body_args(self):
        content_type = self._headers.get('Content-Type', '')
        return parse_body_arguments(content_type, self._body)

    def _get_argument(self, name, default, source, strip):
        args = self._get_arguments(name, source, strip=strip)
        if not args:
            if default is self._ARG_DEFAULT:
                raise MissingArgumentError(name)
            return default
        return args[-1]

    def _get_arguments(self, name, source, strip=True):
        values = []
        for v in source.get(name, []):
            v = v.decode('utf-8')
            if strip:
                v = v.strip()
            values.append(v)
        return values

    def get_query_arguments(self, name, strip=True):
        if self._query_arguments is None:
            self._query_arguments = self._parse_query_args()
        return self._get_arguments(name, self._query_arguments, strip=strip)

    def get_query_argument(self, name, default=_ARG_DEFAULT, strip=True):
        if self._query_arguments is None:
            self._query_arguments = self._parse_query_args()
        return self._get_argument(name, default, self._query_arguments, strip=strip)

    def get_body_arguments(self, name, strip=True):
        if self._body_arguments is None:
            self._body_arguments = self._parse_body_args()
        return self._get_arguments(name, self._body_arguments, strip=strip)

    def get_body_argument(self, name, default=_ARG_DEFAULT, strip=True):
        if self._body_arguments is None:
            self._body_arguments = self._parse_body_args()
        return self._get_argument(name, default, self._body_arguments, strip=strip)

    def _parse_json_args(self):
        try:
            return json.loads(self._body.decode('utf-8'))
        except (ValueError, TypeError) as e:
            logging.error('Request parse json body error: %s', e)
            return {}

    def get_json_argument(self, name, defaut=_ARG_DEFAULT, strip=True):
        if self._json_arguments is None:
            self._json_arguments = self._parse_json_args()
        value = self._json_arguments.get(name, default=defaut, strip=strip)
        if not value and value is self._ARG_DEFAULT:
            raise MissingArgumentError(name)
        else:
            return value

    def _get_address(self):
        sock = self.transport.get_extra_info('socket')

        if sock.family == socket.AF_INET:
            self._socket = (self.transport.get_extra_info('peername') or
                            (None, None))
            self._ip, self._port = self._socket
        elif sock.family == socket.AF_INET6:
            self._socket = (self.transport.get_extra_info('peername') or
                            (None, None, None, None))
            self._ip, self._port, *_ = self._socket
        else:
            self._ip, self._port = (None, None)

    @property
    def ip(self):
        if not self._socket:
            self._get_address()
        return self._ip

    @property
    def port(self):
        if not self._socket:
            self._get_address()
        return self._port

    @property
    def host(self):
        return self._headers.get('Host', '')

    @property
    def path(self):
        return self._parsed_url.path.decode('utf-8')

    @property
    def scheme(self):
        # todo 暂时没有设置websockt开关的地方，如果headers中带有upgrade==‘websocket’即认为是ws
        if self._headers.get('Upgrade') == 'websocket':
            scheme = 'ws'
        else:
            scheme = 'http'

        if self.transport.get_extra_info('sslcontext'):
            scheme += 's'

        return scheme

    @property
    def remote_addr(self):
        """Attempt to return the original client ip based on X-Forwarded-For.
        :return: original client ip.
        """
        if self._remote_addr is None:
            forwarded_for = self._headers.get('X-Forwarded-For', '').split(',')
            remote_addrs = [
                addr for addr in [
                    addr.strip() for addr in forwarded_for
                ] if addr
            ]
            self._remote_addr = remote_addrs[0] if remote_addrs else ''
        return self._remote_addr

    @property
    def json_args(self):
        if self._json_arguments is None:
            self._json_arguments = self._parse_json_args()
        return self._json_arguments

    @property
    def body_args(self):
        if self._body_arguments is None:
            self._body_arguments = self._parse_body_args()
        return self._body_arguments

    @property
    def query_args(self):
        if self._query_arguments is None:
            self._query_arguments = self._parse_query_args()
        return self._query_arguments

class HttpResponse:
    def __init__(self, protocol):
        self._protocol = protocol
        self._headers = {}

    def set_header(self, name, value):
        self._headers[name] = value

    def set_headers(self, headers):
        self._headers = dict(self._headers, **headers)

    def write(self, data, status_code=200, content_type='text/plain'):
        self._protocol.write(data.encode(
            'utf-8'), status_code, content_type, self._headers)

    def json(self, json_data, status_code=200, json_cls=None):
        data = json.dumps(json_data, cls=json_cls)
        self.write(data, status_code, content_type='application/json')
