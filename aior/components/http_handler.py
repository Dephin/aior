import json
from json import JSONEncoder
from typing import Type, Any, Union, overload, List

from aiohttp import web, hdrs
from aiohttp.abc import Request
from aiohttp.typedefs import LooseHeaders
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_response import Response
from pydantic import BaseModel, ValidationError

from aior.components.http_exceptions import BadRequestError
from aior.constants import (
    DEFAULT_JSON_HEADERS, NoneType)
from aior.typedefs import (
    T, T_headers,
    T_queries, T_path_args, T_body, T_model
)

__all__ = (
    'BaseHTTPHandler',
    'PlainBody',
    'JSONBody',
    'BytesBody',
    'IntBody',
    'FloatBody',
    'BooleanBody',
    'Header',
    'Headers',
    'PathArg',
    'PathArgs',
    'Query',
    'Queries',
    'JSONResponse',
    'NoContentResponse',
    'OriginResponse',
)

from typing import Generic

PlainBody = str
BytesBody = bytes
IntBody = int
FloatBody = float
BooleanBody = bool


class _JSONBody(Generic[T]):
    def __getitem__(self, item: T) -> T:
        return 'json_body', item


JSONBody = _JSONBody()


class _XMLBody(Generic[T]):
    def __getitem__(self, item: T) -> T:
        return 'xml_body', item


XMLBody = _XMLBody()


class _Header(Generic[T]):
    def __getitem__(self, item: T) -> T:
        return 'header', item


Header = _Header()


class _Headers(Generic[T_headers]):
    def __getitem__(self, item: T_headers) -> T_headers:
        return 'headers', item


Headers = _Headers()


class _PathArg(Generic[T]):
    def __getitem__(self, item: T) -> T:
        return 'path_arg', item


PathArg = _PathArg()


class _PathArgs(Generic[T_path_args]):
    def __getitem__(self, item: T_path_args) -> T_path_args:
        return 'path_args', item


PathArgs = _PathArgs()


class _Query(Generic[T_headers]):
    def __getitem__(self, item: T) -> T:
        return 'query', item


Query = _Query()


class _Queries(Generic[T_queries]):
    def __getitem__(self, item: T_queries) -> T_queries:
        return 'queries', item


Queries = _Queries()

try:
    from sqlalchemy.ext.asyncio.session import AsyncSession
except ImportError:
    AsyncSession = NoneType


class BaseHTTPHandler(web.View):
    __cors__ = True

    def __init__(self, request: Request):
        super().__init__(request)
        self.db_session = None  # type: AsyncSession

    async def on_start(self):
        """
        Overwrite this function to customize operation
            on starting of processing request, such as authorization
        """

    async def _iter(self):
        if self.request.method not in hdrs.METH_ALL:
            self._raise_allowed_methods()
        method = getattr(self, self.request.method.lower(), None)
        if method is None:
            self._raise_allowed_methods()

        await self.on_start()

        deserializer = getattr(method, '__deserializer__', None)
        if deserializer is not None:
            try:
                kwargs = {name: await callback(self.request)
                          for name, callback in deserializer.items()}
            except ValidationError as e:
                return JSONResponse(e.errors(), status=400)
            except Exception as e:
                raise HTTPBadRequest from e
            resp = await method(**kwargs)
        else:
            resp = await method()

        return resp

    @overload
    async def load_body(self) -> Union[dict, str, int, bool]:
        ...

    @overload
    async def load_body(self, req_cls: Type[T_body]) -> T_body:
        ...

    @overload
    async def load_body(self, req_cls: List[Type[T_body]]) -> List[T_body]:
        ...

    async def load_body(self, req_cls: Type[T_body] = None) -> T_body:
        try:
            if req_cls:
                if isinstance(req_cls, list):
                    return [req_cls[0](**d) for d in await self.request.json()]
                return req_cls(**await self.request.json())

            return await self.request.json()
        except ValidationError as e:
            raise BadRequestError(e.json())

    @overload
    async def load_headers(self) -> Union[dict, str, int, bool]:
        ...

    @overload
    async def load_headers(self, req_cls: Type[T_model]) -> T_model:
        ...

    async def load_headers(self, req_cls=None):
        if req_cls:
            return req_cls(**self.request.headers)
        return self.request.headers

    @overload
    async def load_query(self) -> Union[dict, str, int, bool]:
        ...

    @overload
    async def load_query(self, req_cls: Type[T_model]) -> T_model:
        ...

    async def load_query(self, req_cls=None):
        if req_cls:
            return req_cls(**self.request.query)
        return self.request.query

    @overload
    async def load_path(self) -> Union[dict, str, int, bool]:
        ...

    @overload
    async def load_path(self, req_cls: Type[T_model]) -> T_model:
        ...

    async def load_path(self, req_cls=None):
        if req_cls:
            return req_cls(**dict(self.request.match_info))
        return dict(self.request.match_info)


OriginResponse = Response


class BaseResponse(OriginResponse, Generic[T]):
    status = None
    reason = ''

    def __init__(self,
                 text: T = None, *,
                 headers: LooseHeaders = DEFAULT_JSON_HEADERS,
                 encoder: Type[JSONEncoder] = JSONEncoder,
                 **kwargs: Any,
                 ) -> None:
        if text is not None and not isinstance(text, str):
            if isinstance(text, list):
                data = [i.dict() if isinstance(i, BaseModel) else i
                        for i in text]
            else:
                data = text.dict() if isinstance(text, BaseModel) else text
            text = encoder().encode(data)

        super().__init__(text=text,
                         status=self.status,
                         reason=self.reason,
                         headers=headers,
                         **kwargs)


class OKResponse(BaseResponse, Generic[T]):
    status = 200
    reason = 'OK'


class CreatedResponse(BaseResponse, Generic[T]):
    status = 201
    reason = 'Created'


class NoContentResponse(BaseResponse, Generic[T]):
    status = 204
    reason = 'No Content'


class JSONResponse(OriginResponse, Generic[T]):

    def __init__(self,
                 text: T = None, *,
                 status: int = 200,
                 reason: str = 'OK',
                 headers: LooseHeaders = DEFAULT_JSON_HEADERS,
                 encoder: Type[JSONEncoder] = JSONEncoder,
                 **kwargs: Any,
                 ) -> None:
        if text is not None and not isinstance(text, str):
            if isinstance(text, list):
                data = [i.dict() if isinstance(i, BaseModel) else i
                        for i in text]
            else:
                data = text.dict() if isinstance(text, BaseModel) else text
            text = encoder().encode(data)

        super().__init__(text=text,
                         status=status,
                         reason=reason,
                         headers=headers,
                         **kwargs)


class NoContentResponse(JSONResponse, Generic[T]):
    def __init__(self,
                 status: int = 204,
                 reason: str = 'No Content',
                 headers: LooseHeaders = DEFAULT_JSON_HEADERS,
                 **kwargs: Any,
                 ):
        super().__init__(status=status,
                         reason=reason,
                         headers=headers,
                         **kwargs)
