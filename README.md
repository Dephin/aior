## Intruduction

---

Aior is a async, fast server/client framework based on aiohttp, which provides many out-of-box components for quickly developing restful http api and so on.

**Key features:**

- Easy configuration for environment, logging and ssl of application.
- Auto serialize/deserialize http data
- Auto-generated interactive api doc(to be perfected)
- Async database components
- Websocket handler 
- Standard input handler


## Requirements
---

Python 3.7+


## Installation
```bash
pip3 install aior
```


## Examples
---

#### Simple HTTP

```python
"""
simple http service, just like original aiohttp
"""
from torna.application import TornaApplication
from torna.components import BaseHTTPHandler, JSONResponse


class DemoHTTPHandler(BaseHTTPHandler):
    def get(self):
        return JSONResponse("Hello world")


def main():
    """
    bind handler to url http://localhost:8400/
    """
    app = TornaApplication(
        port=8400,
        routes=[("/", DemoHTTPHandler)],
    )
    app.run()


if __name__ == '__main__':
    main()
```



#### RESTful API

```python
"""
Use Serializer to validate request&response data
"""
from typing import List, Optional

from pydantic import PositiveInt, BaseModel

from aior.application import AiorApplication
# Define Dataclasses
from aior.components import (
    BaseHTTPHandler,
    JSONResponse,
    NoContentResponse,
    OriginResponse,
    NotFoundError,
    Queries,
    JSONBody,
)


class Filter(BaseModel):
    """
    query params: ?limit=&offset=&keyword=
    """
    limit: int = 10
    offset: int = 0
    keyword: Optional[str]

    def get_slice(self):
        return slice(self.offset, self.offset + self.limit)


class Book(BaseModel):
    id: PositiveInt
    name: str
    authors: List[str]


class BookInfo(BaseModel):
    name: str
    authors: List[str]


class UrlParam(BaseModel):
    book_id: PositiveInt


# Initialize Book storage
index = 4
books = {i: Book(id=i, name=f"book_{i}", authors=[f"author_{i}"]) for i in range(1, index)}


# Inherit `BaseHTTPHandler` to use Dataclass type hint
class BooksHandler(BaseHTTPHandler):

    @staticmethod
    async def get(query: Queries[Filter]) -> JSONResponse[List[Book]]:
        """
        Classes of type hint in BaseHTTPHandler inherit follow types:
            {"Query", "Queries", "Header", "Headers", "PathArg", "PathArgs",
            "JSONBody", "PlainBody", "BytesBody", 
            "JSONResponse", "NoContentResponse", "OriginResponse"}

        Deserialized data will be passed into annotated arguments:
            arg: int <=> arg = int(json.loads(self.request.body)) <=> self.load_body(int)
        Any invalid request data will trigger a 400 BadRequest Error

        The return type `JSONResponse[List[Book]]` means return a json type response
            which body should be a list of `Book` object, and it will be serialized
            and json encoded automatically before being written out
        """
        if query.keyword:
            results = []
            for book in books.values():
                if query.keyword in book.name:
                    results.append(book)
        else:
            results = list(books.values())

        return JSONResponse(results[query.get_slice()])

    async def post(self, book_info: JSONBody[BookInfo]) -> OriginResponse:
        global index

        book_info = book_info.dict()
        book_info["id"] = index
        books[index] = Book(**book_info)
        index += 1

        # Original methods of `RequestHandler` can still be used
        return OriginResponse(status=201, reason="Created")


class BookHandler(BaseHTTPHandler):

    @staticmethod
    async def get(url_params: PathArgs[UrlParam]) -> JSONResponse[Book]:
        r"""
        URL parameters come from the values matched by the regex in the route
        """
        book_id = url_params.book_id

        book = books.get(book_id, None)
        if book is None:
            raise NotFoundError("Book is not found")
        return JSONResponse(book)

    @staticmethod
    async def put(json_body: JSONBody[BookInfo], book_id: PathArg[int]) -> NoContentResponse:
        """
        return type `NoContentResponse` indicate that response is `204 No Content`
        """

        book = books.get(book_id, None)
        if book is None:
            raise NotFoundError("Book is not found")
        book_info = json_body.dict()
        book_info["id"] = book_id
        books[book_id] = Book(**book_info)

        return NoContentResponse()

    @staticmethod
    async def delete(url_params: PathArgs[UrlParam]) -> NoContentResponse:
        book_id = url_params.book_id
        book = books.get(book_id, None)
        if book is None:
            raise NotFoundError("Book is not found")
        del books[book_id]

        return NoContentResponse()


def main():
    app = AiorApplication(
        port=8400,
        routes=[
            (r"/books/{book_id}", BookHandler),
            (r"/books", BooksHandler)
        ],
    )
    app.run()


if __name__ == '__main__':
    main()
```

#### Config SSL

```python
from aior.application import AiorApplication

def main():
    AiorApplication(
        port=8400,
        routes=[],
        ssl_crt="{your_ssl_crt_path}",
        ssl_key="{your_ssl_key_path}"
    ).run()
    
    
if __name__ == '__main__':
    main()
```


#### HTTP Handler Using CORS

```python
from aior.application import AiorApplication
from aior.components import BaseHTTPHandler, JSONResponse


class EnableCorsHandler(BaseHTTPHandler):
    async def post(self):
        return JSONResponse()


class DisableCorsHandler(BaseHTTPHandler):
    __cors__ = False

    async def post(self):
        return JSONResponse()


def main():
    """
    bind handler to url http://localhost:8400/
    """
    app = AiorApplication(
        port=8400,
        routes=[
            ("/foo", EnableCorsHandler),
            ("/", DisableCorsHandler),
        ],
        enable_cors=True
    )
    app.run()


if __name__ == '__main__':
    main()
```


#### Simple Websocket Server

```python
from typing import Union

from aior.application import AiorApplication
from aior.components import BaseWebSocketHandler


class DemoWSHandler(BaseWebSocketHandler):
    async def on_message(self, msg: Union[str, bytes]):
        print(msg)
        await self.send("Hi, Client!")


def main():
    AiorApplication(
        port=8400,
        routes=[
            ("/ws", DemoWSHandler),
        ]
    ).run()


if __name__ == '__main__':
    main()
```

#### Simple Websocket Client
```python
import asyncio
from typing import Union

from aior.components import WebSocketClient, BaseClientWebSocketHandler


class DemoWSClientHandler(BaseClientWebSocketHandler):
    async def on_open(self):
        await self.send({"msg": "Hi,server!"})

    async def on_message(self, msg: Union[str, bytes]):
        print(msg)


def main():
    WebSocketClient(
        "ws://localhost:8400/ws",
        DemoWSClientHandler
    ).connect()
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
```

#### Websocket Server Using Authorization

```python
from typing import Union

from aior.application import AiorApplication
from aior.components import BaseWebSocketHandler, UnauthorizedError


class DemoWSHandler(BaseWebSocketHandler):
    async def authorize(self):
        token = self.request.query.get('token')
        if token != 'test':
            raise UnauthorizedError

    async def on_message(self, msg: Union[str, bytes]):
        print(msg)
        await self.send("Hi, Client!")


def main():
    AiorApplication(
        port=8400,
        routes=[
            ("/ws", DemoWSHandler),
        ]
    ).run()


if __name__ == '__main__':
    main()
```

#### Websocket Client Using Authorization

```python
import asyncio

from aior.components import WebSocketClient, BaseClientWebSocketHandler


class DemoWSClientHandler(BaseClientWebSocketHandler):
    async def on_open(self):
        print("open connection")
        await self.send("Hi, server!")

    async def on_close(self):
        print("close connection")


def main():
    WebSocketClient(
        "ws://localhost:8400/ws?token=test",
        DemoWSClientHandler
    ).connect()
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
```


## Auto-generated API Document

---

#### Interactive API docs

Now go to http://127.0.0.1:8000/docs.

You will see the automatic interactive API documentation (provided by [Swagger UI](https://github.com/swagger-api/swagger-ui)):

#### **Alternative API docs** 

And now, go to http://127.0.0.1:8000/redoc.

You will see the alternative automatic documentation (provided by [ReDoc](https://github.com/Rebilly/ReDoc)):


## Build Wheel Package
```bash
rm -r build/lib/*
rm -r aior.egg-info
python setup.py bdist_wheel
```


## Deployment

---

```bash
python3 example.py -e dev -p 8400 --docs
```

**Application arguments:**

- **-e/--env**: define environment
- **-H/--port**: define server host
- **-p/--port**: define server port
- **-D/--docs:** enable auto generate docs



## License

---

[MIT](http://opensource.org/licenses/MIT)

Copyright (c) 2021-present
