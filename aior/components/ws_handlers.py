import asyncio
import base64
import binascii
import hashlib
import json
import os
from ssl import SSLContext
from typing import Optional, Tuple, Iterable, Any
from typing import Type, Union, Dict

import aiohttp
import async_timeout
from aiohttp import (
    hdrs,
    FlowControlDataQueue,
    EofStream,
    Fingerprint,
    ClientSession,
    WSServerHandshakeError,
)
from aiohttp.abc import AbstractStreamWriter
# noinspection PyProtectedMember
from aiohttp.client_reqrep import _merge_ssl_params
# noinspection PyProtectedMember
from aiohttp.helpers import set_result, BasicAuth
from aiohttp.http import (
    WS_KEY,
    WebSocketWriter,
)
from aiohttp.http import ws_ext_gen, ws_ext_parse
# noinspection PyProtectedMember
from aiohttp.http_websocket import (
    WebSocketReader,
    WS_CLOSING_MESSAGE,
    WS_CLOSED_MESSAGE,
    WSMessage,
    WebSocketError,
    WSMsgType,
    WSHandshakeError,
)
from aiohttp.log import ws_logger
from aiohttp.typedefs import LooseHeaders, StrOrURL, JSONEncoder
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_request import BaseRequest
from aiohttp.web_response import StreamResponse
from aiohttp.web_urldispatcher import View
# noinspection PyProtectedMember
from aiohttp.web_ws import THRESHOLD_CONNLOST_ACCESS
from multidict import CIMultiDict
from pydantic import BaseModel

from aior.components import InternalServerError, UnauthorizedError
from aior.typedefs import JSONType, NoneType

__all__ = (
    'BaseWebSocketHandler',
    'BaseClientWebSocketHandler',
    'WebSocketClient',
)


class WebsocketStream:
    default_encoder = None  # type: JSONEncoder

    def __init__(self,
                 receive_timeout: Optional[float] = None,
                 timeout: float = 10.0,
                 autoclose: bool = True,
                 autoping: bool = True,
                 loop: asyncio.AbstractEventLoop = None
                 ) -> None:
        self._writer = None  # type: Optional[WebSocketWriter]
        self._reader = None  # type: Optional[FlowControlDataQueue[WSMessage]]
        self._stream = None  # type: Optional[AbstractStreamWriter]
        self._closed = False
        self._closing = False
        self._conn_lost = 0
        self._close_code = None  # type: Optional[int]
        self._waiting = None  # type: Optional[asyncio.Future[bool]]
        self._exception = None  # type: Optional[BaseException]
        self._autoclose = autoclose
        self._timeout = timeout
        self._autoping = autoping
        self._receive_timeout = receive_timeout
        self._loop = asyncio.get_event_loop() \
            if loop is None else loop

    # noinspection PyAsyncCall
    async def start(self) -> None:
        # don't let `on_open()` affect receive message
        asyncio.ensure_future(
            self.on_open(), loop=self._loop)
        while True:
            msg = await self.receive()
            if msg.type == aiohttp.WSMsgType.text:
                asyncio.ensure_future(
                    self.handle_on_message(msg.data), loop=self._loop)
            else:
                break

    async def handle_on_message(self, msg: Union[str, bytes]):
        try:
            await self.on_message(msg)
        except Exception as e:
            await self.on_error(msg, e)

    async def receive(self, timeout: Optional[float] = None) -> WSMessage:
        if self._reader is None:
            raise RuntimeError('Call .prepare() first')

        loop = self._loop
        assert loop is not None
        while True:
            if self._waiting is not None:
                raise RuntimeError(
                    'Concurrent call to receive() is not allowed')

            if self._closed:
                self._conn_lost += 1
                if self._conn_lost >= THRESHOLD_CONNLOST_ACCESS:
                    raise RuntimeError('WebSocket connection is closed.')
                return WS_CLOSED_MESSAGE
            elif self._closing:
                return WS_CLOSING_MESSAGE

            try:
                self._waiting = loop.create_future()
                try:
                    with async_timeout.timeout(
                            timeout or self._receive_timeout, loop=loop):
                        msg = await self._reader.read()
                    # self._reset_heartbeat()
                finally:
                    waiter = self._waiting
                    set_result(waiter, True)
                    self._waiting = None
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._close_code = 1006
                raise
            except EofStream:
                self._close_code = 1000
                await self.on_eof()
                await self.close()
                return WSMessage(WSMsgType.CLOSED, None, None)
            except WebSocketError as exc:
                self._close_code = exc.code
                await self.close(code=exc.code)
                return WSMessage(WSMsgType.ERROR, exc, None)
            except Exception as exc:
                self._exception = exc
                self._closing = True
                self._close_code = 1006
                await self.close()
                return WSMessage(WSMsgType.ERROR, exc, None)

            if msg.type == WSMsgType.CLOSE:
                self._closing = True
                self._close_code = msg.data
                if not self._closed and self._autoclose:
                    await self.close()
            elif msg.type == WSMsgType.CLOSING:
                self._closing = True
            elif msg.type == WSMsgType.PING and self._autoping:
                await self.on_ping(msg.data)
                continue
            elif msg.type == WSMsgType.PONG and self._autoping:
                await self.on_pong(msg.data)
                continue

            return msg

    async def close(self, *, code: int = 1000, message: bytes = b'') -> bool:
        await self.on_close()

        if self._writer is None:
            raise RuntimeError('Call .prepare() first')

        # self._cancel_heartbeat()
        reader = self._reader
        assert reader is not None

        # we need to break `receive()` cycle first,
        # `close()` may be called from different task
        if self._waiting is not None and not self._closed:
            reader.feed_data(WS_CLOSING_MESSAGE, 0)
            await self._waiting

        if not self._closed:
            self._closed = True
            try:
                await self._writer.close(code, message)
                writer = self._stream
                assert writer is not None
                await writer.drain()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._close_code = 1006
                raise
            except Exception as exc:
                self._close_code = 1006
                self._exception = exc
                return True

            if self._closing:
                return True

            reader = self._reader
            assert reader is not None
            try:
                with async_timeout.timeout(self._timeout, loop=self._loop):
                    msg = await reader.read()
            except asyncio.CancelledError:
                self._close_code = 1006
                raise
            except Exception as exc:
                self._close_code = 1006
                self._exception = exc
                return True

            if msg.type == WSMsgType.CLOSE:
                self._close_code = msg.data
                return True

            self._close_code = 1006
            self._exception = asyncio.TimeoutError()
            return True
        else:
            return False

    async def send(self, data: JSONType,
                   encoder: JSONEncoder = None,
                   compress: Optional[bool] = None) -> None:
        if self._writer is None:
            raise RuntimeError('writer is not prepared')
        if isinstance(data, BaseModel):
            if encoder is None:
                encoder = self.default_encoder
            data = data.json(encoder=encoder)
            binary = False
        elif isinstance(data, dict):
            if encoder is None:
                encoder = self.default_encoder
            data = json.dumps(data, default=encoder)
            binary = False
        elif isinstance(data, str):
            binary = False
        elif isinstance(data, (bytes, bytearray, memoryview)):
            binary = True
        else:
            raise TypeError('data argument must be str or byte-ish (%r)' %
                            type(data))
        await self._writer.send(data, binary=binary, compress=compress)

    async def send_str(self, data: str, compress: Optional[bool] = None) -> None:
        if self._writer is None:
            raise RuntimeError('Call .prepare() first')
        if not isinstance(data, str):
            raise TypeError('data argument must be str (%r)' % type(data))
        await self._writer.send(data, binary=False, compress=compress)

    async def send_bytes(self, data: bytes,
                         compress: Optional[bool] = None) -> None:
        if self._writer is None:
            raise RuntimeError('Call .prepare() first')
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError('data argument must be byte-ish (%r)' %
                            type(data))
        await self._writer.send(data, binary=True, compress=compress)

    async def on_message(self, msg: Union[str, bytes]) -> None:
        pass

    async def on_open(self) -> None:
        pass

    async def on_close(self) -> None:
        pass

    async def on_error(self, msg: Union[str, bytes], exc: Exception) -> None:
        pass

    async def on_eof(self) -> None:
        pass

    async def on_ping(self, data: Union[str, bytes]) -> None:
        pass

    async def on_pong(self, data: Union[str, bytes]) -> None:
        pass


# noinspection PyProtectedMember
class WebSocketResponse(StreamResponse):
    def __init__(self,
                 protocols: Iterable[str] = (),
                 compress: bool = True,
                 max_msg_size: int = 4 * 1024 * 1024,
                 ) -> None:
        super().__init__(status=101)
        self._loop = None  # type: Optional[asyncio.AbstractEventLoop]
        self._protocols = protocols
        self._ws_protocol = None  # type: str
        self._compress = compress
        self._max_msg_size = max_msg_size
        self._payload_writer = None  # type: AbstractStreamWriter

    async def prepare(self, request: BaseRequest) -> Union[NoneType,
                                                           AbstractStreamWriter,
                                                           Tuple[FlowControlDataQueue,
                                                                 WebSocketWriter,
                                                                 AbstractStreamWriter]]:
        if self._eof_sent:
            return None
        if self._payload_writer is not None:
            return self._payload_writer

        protocol, writer = self._pre_start(request)
        payload_writer = await super().prepare(request)
        assert payload_writer is not None
        reader = self._post_start(request, protocol)
        await payload_writer.drain()

        return reader, writer, payload_writer

    def _pre_start(self, request: BaseRequest) -> Tuple[str, WebSocketWriter]:
        self._loop = request._loop

        headers, protocol, compress, notakeover = self._handshake(
            request)

        # self._reset_heartbeat()

        self.set_status(101)
        self.headers.update(headers)
        self.force_close()
        self._compress = compress
        transport = request._protocol.transport
        assert transport is not None
        writer = WebSocketWriter(request._protocol,
                                 transport,
                                 compress=compress,
                                 notakeover=notakeover)

        return protocol, writer

    def _post_start(self, request: BaseRequest, protocol: str) -> FlowControlDataQueue:
        self._ws_protocol = protocol
        loop = self._loop
        assert loop is not None
        reader = FlowControlDataQueue(
            request._protocol, limit=2 ** 16, loop=loop)
        request.protocol.set_parser(WebSocketReader(
            reader, self._max_msg_size, compress=self._compress))
        # disable HTTP keepalive for WebSocket
        request.protocol.keep_alive(False)

        return reader

    def _handshake(self, request: BaseRequest) -> Tuple[CIMultiDict[str], str, bool, bool]:
        headers = request.headers
        if 'websocket' != headers.get(hdrs.UPGRADE, '').lower().strip():
            raise HTTPBadRequest(
                text=('No WebSocket UPGRADE hdr: {}\n Can '
                      '"Upgrade" only to "WebSocket".').format(headers.get(hdrs.UPGRADE)))

        if 'upgrade' not in headers.get(hdrs.CONNECTION, '').lower():
            raise HTTPBadRequest(
                text='No CONNECTION upgrade hdr: {}'.format(
                    headers.get(hdrs.CONNECTION)))

        # find common sub-protocol between client and server
        protocol = None
        if hdrs.SEC_WEBSOCKET_PROTOCOL in headers:
            req_protocols = [str(proto.strip()) for proto in
                             headers[hdrs.SEC_WEBSOCKET_PROTOCOL].split(',')]

            for proto in req_protocols:
                if proto in self._protocols:
                    protocol = proto
                    break
            else:
                # No overlap found: Return no protocol as per spec
                ws_logger.warning(
                    'Client protocols %r don’t overlap server-known ones %r',
                    req_protocols, self._protocols)

        # check supported version
        version = headers.get(hdrs.SEC_WEBSOCKET_VERSION, '')
        if version not in ('13', '8', '7'):
            raise HTTPBadRequest(
                text='Unsupported version: {}'.format(version))

        # check client handshake for validity
        key = headers.get(hdrs.SEC_WEBSOCKET_KEY)
        try:
            if not key or len(base64.b64decode(key)) != 16:
                raise HTTPBadRequest(
                    text='Handshake error: {!r}'.format(key))
        except binascii.Error:
            raise HTTPBadRequest(
                text='Handshake error: {!r}'.format(key)) from None

        accept_val = base64.b64encode(
            hashlib.sha1(key.encode() + WS_KEY).digest()).decode()
        response_headers = CIMultiDict(  # type: ignore
            {hdrs.UPGRADE: 'websocket',
             hdrs.CONNECTION: 'upgrade',
             hdrs.SEC_WEBSOCKET_ACCEPT: accept_val})

        notakeover = False
        compress = 0
        if self._compress:
            extensions = headers.get(hdrs.SEC_WEBSOCKET_EXTENSIONS)
            # Server side always get return with no exception.
            # If something happened, just drop compress extension
            compress, notakeover = ws_ext_parse(extensions, isserver=True)
            if compress:
                enabledext = ws_ext_gen(compress=compress, isserver=True,
                                        server_notakeover=notakeover)
                response_headers[hdrs.SEC_WEBSOCKET_EXTENSIONS] = enabledext

        if protocol:
            response_headers[hdrs.SEC_WEBSOCKET_PROTOCOL] = protocol
        return (response_headers,  # type: ignore
                protocol,
                compress,
                notakeover)


class BaseWebSocketHandler(WebsocketStream, View):
    ESTABLISH_CONNECT_AFTER_AUTH = True

    def __init__(self, request: BaseRequest, **kwargs: Any):
        View.__init__(self, request)
        WebsocketStream.__init__(self, **kwargs)

    async def authorize(self) -> None:
        """
        Overwrite this function to achieve custom authorization,
        raising a `UnauthorizedError` exception when authorization fail.
        """

    async def get(self) -> WebSocketResponse:
        authorized = False
        unauthorized_code = None
        unauthorized_message = None

        try:
            await self.authorize()
            authorized = True
        except UnauthorizedError as e:
            unauthorized_code = e.status_code
            unauthorized_message = e.reason
        except Exception as e:
            raise InternalServerError(str(e)) from e

        try:
            if authorized:
                resp = await self.upgrade_connection()
                await self.start()
                return resp
            else:
                if self.ESTABLISH_CONNECT_AFTER_AUTH:
                    resp = await self.upgrade_connection()
                    await self.close(code=unauthorized_code,
                                     message=unauthorized_message.encode())
                    return resp
                else:
                    await self.close(code=unauthorized_code,
                                     message=unauthorized_message.encode())
                    return WebSocketResponse()
        except (asyncio.CancelledError, asyncio.TimeoutError):
            await self.close()

    async def upgrade_connection(self):
        resp = WebSocketResponse()
        self._reader, self._writer, self._stream = await resp.prepare(self.request)
        await self._stream.drain()
        return resp


class ClientWebSocketSession(ClientSession):
    async def ws_connect(
            self,
            url: StrOrURL, *,
            method: str = hdrs.METH_GET,
            protocols: Iterable[str] = (),
            timeout: float = 10.0,
            receive_timeout: Optional[float] = None,
            autoclose: bool = True,
            autoping: bool = True,
            heartbeat: Optional[float] = None,
            auth: Optional[BasicAuth] = None,
            origin: Optional[str] = None,
            headers: Optional[LooseHeaders] = None,
            proxy: Optional[StrOrURL] = None,
            proxy_auth: Optional[BasicAuth] = None,
            ssl: Union[SSLContext, bool, None, Fingerprint] = None,
            verify_ssl: Optional[bool] = None,
            fingerprint: Optional[bytes] = None,
            ssl_context: Optional[SSLContext] = None,
            proxy_headers: Optional[LooseHeaders] = None,
            compress: int = 0,
            max_msg_size: int = 4 * 1024 * 1024):
        if headers is None:
            real_headers = CIMultiDict()  # type: CIMultiDict[str]
        else:
            real_headers = CIMultiDict(headers)

        default_headers = {
            hdrs.UPGRADE: "websocket",
            hdrs.CONNECTION: "upgrade",
            hdrs.SEC_WEBSOCKET_VERSION: "13",
        }

        for key, value in default_headers.items():
            real_headers.setdefault(key, value)

        sec_key = base64.b64encode(os.urandom(16))
        real_headers[hdrs.SEC_WEBSOCKET_KEY] = sec_key.decode()

        if protocols:
            real_headers[hdrs.SEC_WEBSOCKET_PROTOCOL] = ",".join(protocols)
        if origin is not None:
            real_headers[hdrs.ORIGIN] = origin
        if compress:
            extstr = ws_ext_gen(compress=compress)
            real_headers[hdrs.SEC_WEBSOCKET_EXTENSIONS] = extstr

        ssl = _merge_ssl_params(ssl, verify_ssl, ssl_context, fingerprint)

        # send request
        resp = await self.request(method, url,
                                  headers=real_headers,
                                  read_until_eof=False,
                                  auth=auth,
                                  proxy=proxy,
                                  proxy_auth=proxy_auth,
                                  ssl=ssl,
                                  proxy_headers=proxy_headers)

        try:
            # check handshake
            if resp.status != 101:
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message='Invalid response status',
                    status=resp.status,
                    headers=resp.headers)

            if resp.headers.get(hdrs.UPGRADE, '').lower() != 'websocket':
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message='Invalid upgrade header',
                    status=resp.status,
                    headers=resp.headers)

            if resp.headers.get(hdrs.CONNECTION, '').lower() != 'upgrade':
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message='Invalid connection header',
                    status=resp.status,
                    headers=resp.headers)

            # key calculation
            key = resp.headers.get(hdrs.SEC_WEBSOCKET_ACCEPT, '')
            match = base64.b64encode(
                hashlib.sha1(sec_key + WS_KEY).digest()).decode()
            if key != match:
                raise WSServerHandshakeError(
                    resp.request_info,
                    resp.history,
                    message='Invalid challenge response',
                    status=resp.status,
                    headers=resp.headers)

            # websocket protocol
            protocol = None
            if protocols and hdrs.SEC_WEBSOCKET_PROTOCOL in resp.headers:
                resp_protocols = [
                    proto.strip() for proto in
                    resp.headers[hdrs.SEC_WEBSOCKET_PROTOCOL].split(',')]

                for proto in resp_protocols:
                    if proto in protocols:
                        protocol = proto
                        break

            # websocket compress
            notakeover = False
            if compress:
                compress_hdrs = resp.headers.get(hdrs.SEC_WEBSOCKET_EXTENSIONS)
                if compress_hdrs:
                    try:
                        compress, notakeover = ws_ext_parse(compress_hdrs)
                    except WSHandshakeError as exc:
                        raise WSServerHandshakeError(
                            resp.request_info,
                            resp.history,
                            message=exc.args[0],
                            status=resp.status,
                            headers=resp.headers)
                else:
                    compress = 0
                    notakeover = False

            conn = resp.connection
            assert conn is not None
            proto = conn.protocol
            assert proto is not None
            transport = conn.transport
            assert transport is not None
            reader = FlowControlDataQueue(
                proto, limit=2 ** 16, loop=self._loop)  # type: FlowControlDataQueue[WSMessage]  # noqa
            proto.set_parser(WebSocketReader(reader, max_msg_size), reader)
            writer = WebSocketWriter(
                proto, transport, use_mask=True,
                compress=compress, notakeover=notakeover)
        except BaseException:
            resp.close()
            raise
        else:
            return reader, writer, resp, protocol


class BaseClientWebSocketHandler(WebsocketStream):
    def __init__(self,
                 url: str,
                 connect_settings: Dict[str, Any],
                 ) -> None:
        super().__init__()
        self._url = url
        self._connect_settings = connect_settings

    async def connect_async(self):
        session = ClientWebSocketSession()
        self._reader, self._writer, self._stream = None, None, None
        try:
            self._reader, self._writer, self._stream, _ \
                = await session.ws_connect(self._url, **self._connect_settings)
            await self.start()
        finally:
            if self._stream is not None:
                self._stream.close()
            await session.close()

    def connect(self):
        self._loop.create_task(self.connect_async())


def WebSocketClient(url: str,
                    handler_class: Type[BaseClientWebSocketHandler],
                    method: str = hdrs.METH_GET,
                    timeout: float = 10.0,
                    receive_timeout: Optional[float] = None,
                    autoclose: bool = True,
                    autoping: bool = True,
                    heartbeat: Optional[float] = None,
                    auth: Optional[BasicAuth] = None,
                    origin: Optional[str] = None,
                    headers: Optional[LooseHeaders] = None,
                    proxy: Optional[StrOrURL] = None,
                    proxy_auth: Optional[BasicAuth] = None,
                    ssl: Union[SSLContext, bool, None, Fingerprint] = None,
                    verify_ssl: Optional[bool] = None,
                    fingerprint: Optional[bytes] = None,
                    ssl_context: Optional[SSLContext] = None,
                    proxy_headers: Optional[LooseHeaders] = None,
                    compress: int = 0,
                    max_msg_size: int = 4 * 1024 * 1024
                    ) -> BaseClientWebSocketHandler:
    connect_settings = dict(method=method,
                            timeout=timeout,
                            receive_timeout=receive_timeout,
                            autoclose=autoclose,
                            autoping=autoping,
                            heartbeat=heartbeat,
                            auth=auth,
                            origin=origin,
                            headers=headers,
                            proxy=proxy,
                            proxy_auth=proxy_auth,
                            ssl=ssl,
                            verify_ssl=verify_ssl,
                            fingerprint=fingerprint,
                            ssl_context=ssl_context,
                            proxy_headers=proxy_headers,
                            compress=compress,
                            max_msg_size=max_msg_size)
    return handler_class(url=url,
                         connect_settings=connect_settings)
