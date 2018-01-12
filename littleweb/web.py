# Created by lujin at 11/12/2017
import asyncio

from littleweb.protocol import HttpProtocol
from littleweb.router import Router


class Application(object):
    def __init__(self, router=None):
        if router is None:
            router = Router()
        self._router = router

    @property
    def router(self):
        return self._router

    def run(self, host='127.0.0.1', port=8080, debug=True):
        loop = asyncio.get_event_loop()
        coro = loop.create_server(lambda: HttpProtocol(router=self._router, loop=loop), host, port)
        server = loop.run_until_complete(coro)
        print('* Serving on {}'.format(server.sockets[0].getsockname()))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
