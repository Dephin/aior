import asyncio
import json
import logging
import ssl
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, List, Tuple, Type, Dict, get_type_hints, Optional, Union

from aiohttp import web
from aiohttp.typedefs import PathLike, JSONEncoder
from aiohttp.web_runner import GracefulExit
from pydantic import BaseModel

from aior.components.http_handler import BaseHTTPHandler
from aior.components.stdin_handler import BaseStandardInputHandler
from aior.constants import METHODS_ALL, Environment, DEFAULT_LOGGING_FORMAT, DEFAULT_LOGGING_FILE_INTERVAL, \
    DEFAULT_LOGGING_FILE_ENCODING, DEFAULT_LOGGING_FILE_DELAY, DEFAULT_LOGGING_FILE_WHEN, DEFAULT_LOGGING_LEVEL
from aior.docs import DocsHandler, OpenapiSchemaHandler, get_openapi, RedocHandler
from aior.log import server_logger, web_logger, access_logger, client_logger, ws_logger
from aior.utils import gen_deserializers

__all__ = ('AiorApplication', 'LoggingConfig')

_LOGGERS = {
    'access': access_logger,
    'client': client_logger,
    'internal': client_logger,
    'server': server_logger,
    'web': web_logger,
    'websocket': ws_logger,
}


class LoggingConfig(BaseModel):
    class LoggingFileConfig(BaseModel):
        path: PathLike
        when: str = DEFAULT_LOGGING_FILE_WHEN
        interval: int = DEFAULT_LOGGING_FILE_INTERVAL
        delay: bool = DEFAULT_LOGGING_FILE_DELAY
        encoding: str = DEFAULT_LOGGING_FILE_ENCODING

    adding_stream: bool = True
    format: str = DEFAULT_LOGGING_FORMAT
    level: int = DEFAULT_LOGGING_LEVEL
    file: Optional[LoggingFileConfig] = None


class AiorApplication(web.Application):
    def __init__(self, *,
                 routes: List[Union[Tuple[str, Type[web.View]],
                                    Tuple[str, Type[web.View], Dict]]],
                 app_name='aior',
                 env: str = Environment.LOCAL,
                 host: str = '0.0.0.0',
                 port: int = 8400,
                 config_file: Optional[PathLike] = None,
                 logging_config: Union[LoggingConfig, Dict[str, LoggingConfig]] = None,
                 default_json_encoder: JSONEncoder = json.JSONEncoder,
                 ssl_crt: PathLike = None,
                 ssl_key: PathLike = None,
                 ssl_context: ssl.SSLContext = None,
                 enable_cors: bool = False,
                 enable_docs: bool = False,
                 docs_title: str = '{app_name} API',
                 docs_version: str = '0.1.0',
                 openapi_url: str = '/openapi.json',
                 openapi_version: str = '3.0.2',
                 docs_url_prefix: str = '',
                 swagger_docs_url: str = '/docs',
                 swagger_ui_favicon_url: str = 'https://docs.aiohttp.org/en/stable/_static/favicon.ico',
                 swagger_ui_js_url: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js',
                 swagger_ui_css_url: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css',
                 redoc_docs_url: str = '/redoc',
                 redoc_ui_favicon_url: str = 'https://docs.aiohttp.org/en/stable/_static/favicon.ico',
                 redoc_ui_js_url: str = 'https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js',
                 loop: asyncio.AbstractEventLoop = None,
                 **kwargs: Any,
                 ) -> None:
        super().__init__(**kwargs)
        self._app_name = app_name
        self._env = env
        self._host = host
        self._port = port
        self._routes = routes
        self._enable_cors = enable_cors
        self._enable_docs = enable_docs
        self._config = {}  # type: Dict[str, Any]
        self._logging_config = logging_config
        self._ssl_context = ssl_context
        self._ssl_key = ssl_key
        self._ssl_crt = ssl_crt
        self._openapi_url = f'{docs_url_prefix}{openapi_url}'
        self._docs_title = docs_title.format(app_name=app_name)
        self._docs_version = docs_version
        self._openapi_version = openapi_version
        self._swagger_docs_url = f'{docs_url_prefix}{swagger_docs_url}'
        self._swagger_ui_favicon_url = swagger_ui_favicon_url
        self._swagger_ui_js_url = swagger_ui_js_url
        self._swagger_ui_css_url = swagger_ui_css_url
        self._redoc_docs_url = f'{docs_url_prefix}{redoc_docs_url}'
        self._redoc_ui_favicon_url = redoc_ui_favicon_url
        self._redoc_ui_js_url = redoc_ui_js_url
        self._openapi_schema = None  # type: Dict[str, Any]
        self._default_json_encoder = default_json_encoder
        self._runner = web.AppRunner(self, handle_signals=True)

        self._loop = asyncio.get_event_loop() if loop is None else loop

        self._init_sys_argv()

        if config_file is not None:
            self._init_config(config_file)

        self.setup()

    def _init_logging(self) -> None:
        configs = self._config.get('logging', self._logging_config)

        if not configs:
            configs = {'server': LoggingConfig()}
        elif isinstance(configs, LoggingConfig):
            configs = {'server': configs}

        for name, logger in _LOGGERS.items():
            logger.name = f'{self._app_name}.{name}'

            cfg = configs.get(name, None)
            if not cfg:
                cfg = LoggingConfig()
            elif isinstance(cfg, dict):
                cfg = LoggingConfig(**cfg)

            formatter = logging.Formatter(cfg.format)

            if cfg.adding_stream:
                hdr = logging.StreamHandler()
                hdr.setFormatter(formatter)
                logger.addHandler(hdr)

            if cfg.file:
                if isinstance(cfg.file.path, Path):
                    file_path = cfg.file.path
                    file_path_str = str(file_path.resolve())
                else:
                    file_path = Path(cfg.file.path)
                    file_path_str = cfg.file.path
                if not file_path.exists():
                    file_path.open('a').close()
                hdr = TimedRotatingFileHandler(
                    file_path_str,
                    when=cfg.file.when,
                    interval=cfg.file.interval,
                    encoding=cfg.file.encoding,
                    delay=cfg.file.delay,
                )
                hdr.setFormatter(formatter)
                logger.addHandler(hdr)

            logger.setLevel(cfg.level)

    def _init_config(self, config_file: PathLike) -> None:
        if isinstance(config_file, str):
            config_file = Path(config_file)

        config_file = config_file.parent / config_file.name.format(env=self._env)

        suf = config_file.suffix
        if suf == '.ini':
            config_parser = ConfigParser()
            config_parser.read(str(config_file.resolve()))
            for section in config_parser.sections():
                self._config[section] = {}
                for option in config_parser.options(section):
                    self._config[section][option] = config_parser.get(section, option)
        elif suf in ('.yml', '.yaml'):
            with config_file.open() as f:
                import yaml
                self._config = yaml.safe_load(f)
        else:
            raise RuntimeError('not supported config file type')

    def _init_sys_argv(self) -> None:
        argv = sys.argv[1:]
        arg_parser = ArgumentParser(
            description=f'{self._app_name.capitalize()} application server',
        )
        arg_parser.add_argument(
            '-e', '--env',
            help='Config environment to serve on (default: %(default)r)',
            default=self._env
        )
        arg_parser.add_argument(
            '-H', '--host',
            help='TCP/IP host to serve on (default: %(default)r)',
            default=self._host
        )
        arg_parser.add_argument(
            '-p', '--port',
            help='TCP/IP port to serve on (default: %(default)r)',
            type=int,
            default=self._port
        )
        arg_parser.add_argument(
            '-D', '--docs',
            help='Enable api doc page',
            action='store_true',
            default=self._enable_docs
        )
        args, extra_argv = arg_parser.parse_known_args(argv)
        self._host = args.host
        self._port = args.port
        self._env = args.env
        self._enable_docs = args.docs
        self.init_extra_sys_argv(extra_argv)

    def init_extra_sys_argv(self, extra_args: List[str]) -> None:
        """
        override to custom system arguments value
        """

    def _init_ssl(self) -> None:
        self._ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_crt = (self._ssl_crt if isinstance(self._ssl_crt, str)
                   else str(self._ssl_crt.resolve().absolute()))
        ssl_key = (self._ssl_key if isinstance(self._ssl_crt, str)
                   else str(self._ssl_key.resolve().absolute()))
        self._ssl_context.load_cert_chain(ssl_crt, ssl_key)

    def _init_routes(self) -> None:
        cooked_routes = []
        for route in self._routes:
            path = route[0]
            handler_cls = route[1]
            kwargs = route[2] if len(route) > 2 else {}
            handler_cls.default_json_encoder = self._default_json_encoder
            if issubclass(handler_cls, BaseHTTPHandler):
                for m in METHODS_ALL:
                    method = getattr(handler_cls, m.lower(), None)
                    if method is not None:
                        hints = get_type_hints(method)
                        hints.pop('return', None)
                        if hints:
                            method.__deserializer__ = gen_deserializers(hints)
            elif issubclass(handler_cls, BaseStandardInputHandler):
                handler_cls().connect()
                continue

            cooked_routes.append((path, handler_cls, kwargs))

        if self._enable_cors:
            self._handle_cors_routes(cooked_routes)
        else:
            for path, handler_cls, kwargs in cooked_routes:
                self.router.add_route('*', path, handler_cls, **kwargs)

    def _handle_cors_routes(self, raw_routes: List[Tuple[str, Type[web.View], Dict]]) -> None:
        import aiohttp_cors
        cors = aiohttp_cors.setup(self, defaults={
            '*': aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers='*',
                allow_headers='*',
            )
        })

        from aiohttp_cors import CorsViewMixin

        def gen_cors_handler(base):
            class CorsHandler(base, CorsViewMixin):
                ...

            return CorsHandler

        for path, handler_cls, kwargs in raw_routes:
            if getattr(handler_cls, '__cors__', False):
                route = self.router.add_route(
                    '*', path, gen_cors_handler(handler_cls), **kwargs)
                cors.add(route)
            else:
                self.router.add_route('*', path, handler_cls, **kwargs)

    def _init_docs(self) -> None:
        self._docs_title = self._docs_title.format(
            app_name=self._app_name)
        self._openapi_schema = self.openapi()
        self._routes.insert(0, (self._swagger_docs_url, DocsHandler))
        self._routes.insert(0, (self._redoc_docs_url, RedocHandler))
        self._routes.insert(0, (self._openapi_url, OpenapiSchemaHandler))

    def openapi(self) -> Dict:
        routes = []
        for path, handler_cls in self._routes:
            if not issubclass(handler_cls, BaseHTTPHandler):
                continue

            handler_hints = {}
            for m in METHODS_ALL:
                method_name = m.lower()
                method_func = getattr(handler_cls, method_name, None)
                if method_func is not None:
                    hints = get_type_hints(method_func)
                    if 'return' in hints:
                        handler_hints.update({method_name: hints})
                    else:
                        self.logger.warning(f'handler:{handler_cls.__name__}:function:{method_name}: '
                                            f'does not define return type')

            if handler_hints:
                routes.append((path, handler_cls, handler_hints))

        info = {'title': f'{self._app_name.capitalize()} API', 'version': self._docs_version}
        return get_openapi(routes=routes, info=info, openapi_version=self._openapi_version)

    async def on_start(self) -> None:
        """
        override to custom function on application starting up
        """

    def setup(self):
        self._init_logging()

        if (self._ssl_context is not None
                and self._ssl_key is not None
                and self._ssl_crt is not None):
            self._init_ssl()

        if self._enable_docs:
            self._init_docs()

        self._init_routes()

    def run(self):
        self._loop.run_until_complete(self.start_runner())

        self.logger.info('Server start.')
        try:
            self._loop.run_forever()
        except (GracefulExit, KeyboardInterrupt):  # pragma: no cover
            self.logger.info('Process interrupted.')
        finally:
            self._loop.run_until_complete(self._runner.cleanup())
            self.logger.info('Runner cleaned up.')
            for task in asyncio.Task.all_tasks(self._loop):
                task.cancel()
            if sys.version_info >= (3, 6):  # don't use PY_36 to pass mypy
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
            server_logger.info('Server stop.')

    async def start_runner(self) -> None:
        await self.on_start()
        await self._runner.setup()
        site = web.TCPSite(self._runner,
                           self._host,
                           self._port,
                           ssl_context=self._ssl_context)
        await site.start()

    @property
    def openapi_url(self):
        return self._openapi_url

    @property
    def openapi_schema(self):
        return self._openapi_schema

    @property
    def docs_title(self):
        return self._docs_title

    @property
    def swagger_ui_js_url(self):
        return self._swagger_ui_js_url

    @property
    def swagger_docs_url(self):
        return self._swagger_docs_url

    @property
    def swagger_ui_css_url(self):
        return self._swagger_ui_css_url

    @property
    def swagger_ui_favicon_url(self):
        return self._swagger_ui_favicon_url

    @property
    def redoc_ui_js_url(self):
        return self._redoc_ui_js_url

    @property
    def redoc_ui_favicon_url(self):
        return self._redoc_ui_favicon_url


if __name__ == '__main__':
    from aior.components import JSONResponse


    class DemoHandler(BaseHTTPHandler):
        async def get(self):
            return JSONResponse('Hello, world')


    AiorApplication(routes=[('/', DemoHandler)]).run()
