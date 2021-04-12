import re
import sys
import typing
import uuid
from functools import partial
from json import JSONEncoder
from typing import Text, Any, Type, Optional, Tuple

from pydantic import BaseModel

from aior.components import BadRequestError
from aior.components.http_handler import PlainBody, BytesBody
from aior.typedefs import JSONType


def add_space_in_front_of_capital_letter(s: Text) -> Text:
    result = re.sub("[A-Z]", lambda x: " " + x.group(0), s)
    return result.lstrip(" ")


def get_generic_origin_type(typ: Any) -> Optional[Type]:
    if sys.version_info >= (3, 7):
        return getattr(typ, "__origin__", None)
    else:
        return getattr(typ, "__extra__", None)


def get_generic_type_args(typ: Any) -> Tuple:
    if sys.version_info >= (3, 8):
        return typing.get_args(typ)
    else:
        return getattr(typ, "__args__", ())


def serialize_json_data(data: JSONType,
                        encoder: Type[JSONEncoder]
                        ) -> str:
    if isinstance(data, str):
        return data

    if isinstance(data, list):
        data = [d.dict() if isinstance(d, BaseModel)
                else d for d in data]
    elif isinstance(data, BaseModel):
        data = data.dict()

    return encoder().encode(data)


def gen_id() -> str:
    return str(uuid.uuid4())


def gen_deserializers(type_hints) -> typing.Dict:
    return {name: gen_deserializer(name, hint)
            for name, hint in type_hints.items()}


def gen_deserializer(name, hint):
    if hint is PlainBody:
        async def deserialize(request):
            return await request.text()

        return deserialize

    if hint in (BytesBody, int, float, bool):
        async def deserialize(typ, request):
            return typ(await request.text())

        return partial(deserialize, hint)

    if hint is dict:
        async def deserialize(request):
            return await request.json()

        return deserialize

    if isinstance(hint, tuple):
        type_name, type_value = hint
        if type_name == "json_body":
            if type_value is str:
                async def deserialize(req):
                    return await req.text()

                return deserialize
            if type_value in (int, float, bool):
                async def deserialize(t, req):
                    return t(await req.text())

                return deserialize
            if issubclass(type_value, BaseModel):
                async def deserialize(model, request):
                    return model(**await request.json())

                return partial(deserialize, type_value)
        elif type_name == "query":
            async def deserialize(n, t, req):
                ret = req.query.get(n, None)
                if ret is None:
                    raise BadRequestError(f"query argument({n}) were not found")
                return t(ret)

            return partial(deserialize, name, type_value)
        elif type_name == "queries":
            if issubclass(type_value, BaseModel):
                async def deserialize(model, req):
                    return model(**req.query)

                return partial(deserialize, type_value)
            else:
                async def deserialize(req):
                    return req.query

                return deserialize
        elif type_name == "header":
            async def deserialize(n, t, req):
                ret = req.headers.get(n, None)
                if ret is None:
                    raise BadRequestError(f"header argument({n}) were not found")

                return t(ret)

            return partial(deserialize, name, type_value)
        elif type_name == "headers":
            if issubclass(type_value, BaseModel):
                async def deserialize(model, req):
                    return model(**req.headers)

                return partial(deserialize, type_value)
            else:
                async def deserialize(req):
                    return req.headers

                return deserialize
        elif type_name == "path_arg":
            async def deserialize(n, t, req):
                ret = req.match_info.get(n, None)
                if ret is None:
                    raise BadRequestError(f"path argument({n}) were not found")
                return t(ret)

            return partial(deserialize, name, type_value)
        elif type_name == "path_args":
            if issubclass(type_value, BaseModel):
                async def deserialize(model, req):
                    return model(**dict(req.match_info))

                return partial(deserialize, type_value)
            else:
                async def deserialize(req):
                    return dict(req.match_info)

                return deserialize

    raise ValueError(f"not supported type: {hint}")


def get_json_type(clazz: Type) -> str:
    if issubclass(clazz, str):
        return 'string'
    elif issubclass(clazz, (int, float)):
        return 'number'
    elif issubclass(clazz, bool):
        return 'boolean'
    elif issubclass(clazz, (BaseModel, dict)):
        return 'object'
    else:
        raise ValueError('not supported type')
