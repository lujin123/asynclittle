# Created by lujin at 12/12/2017
import re


class Router:
    _SUPPORT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'PATCH')

    def __init__(self):
        self._router = {}

    def add_router(self, url_pattern, handler, methods=None):
        if methods is None:
            methods = self._SUPPORT_METHODS
        else:
            methods = [method for method in methods if method in self._SUPPORT_METHODS]

        for method in methods:
            method_queue = self._router.get(method, [])
            method_queue.append(self._prepare_route(url_pattern, handler))
            self._router[method] = method_queue

    def add_get(self, url_pattern, handler):
        self.add_router(url_pattern, handler, ['GET'])

    def add_post(self, url_pattern, handler):
        self.add_router(url_pattern, handler, ['POST'])

    def add_put(self, url_pattern, handler):
        self.add_router(url_pattern, handler, ['PUT'])

    def add_delete(self, url_pattern, handler):
        self.add_router(url_pattern, handler, ['DELETE'])

    @classmethod
    def _prepare_route(cls, pattern, handler):
        if not pattern.startswith('^'):
            pattern = r'^' + pattern
        if not pattern.endswith('$'):
            pattern += r'$'
        return re.compile(pattern), handler

    def get_method_queue(self, method):
        """
        获取请求方式的路由队列
        :param method:
        :return:
        """
        return self._router.get(method, [])
