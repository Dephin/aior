from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp.web_response import Response as OriginResponse
from pydantic import Field, BaseModel

from aior.application import AiorApplication
from aior.components import (
    BaseHTTPHandler,
    NoContentResponse,
    JSONResponse,
    JSONBody, Queries, Headers, PathArgs)


class Item(BaseModel):
    name: str


class CustomerRequestBody(BaseModel):
    name: str


class CustomerQuery(BaseModel):
    q: str


class CustomerPath(BaseModel):
    test_id: int


class CustomerResponseBody(BaseModel):
    name: str


class EmptyHandler(BaseHTTPHandler):
    @staticmethod
    async def get():
        return JSONResponse()

    @staticmethod
    async def post():
        return NoContentResponse()

    @staticmethod
    async def put():
        return OriginResponse()


class JSONHandler(BaseHTTPHandler):
    @staticmethod
    async def get():
        return JSONResponse("Hello world")

    @staticmethod
    async def post():
        return JSONResponse(1)

    @staticmethod
    async def put():
        return JSONResponse(0.5)

    @staticmethod
    async def delete():
        return JSONResponse(True)

    @staticmethod
    async def patch():
        return JSONResponse({"name": "Jane"})


class JSONArrayHandler(BaseHTTPHandler):
    @staticmethod
    async def get():
        return JSONResponse(["x", "y", "z"])

    @staticmethod
    async def post():
        return JSONResponse([1, 2, 3])

    @staticmethod
    async def put():
        return JSONResponse([0.5, 1, 3.5])

    @staticmethod
    async def delete():
        return JSONResponse([True, False])

    @staticmethod
    async def patch():
        return JSONResponse([
            {"name": "Jane"},
            {"name": "Jim"},
        ])


class JSONModelHandler(BaseHTTPHandler):
    @staticmethod
    async def get():
        return JSONResponse(Item(name="Phone"))

    @staticmethod
    async def post():
        return JSONResponse([
            Item(name="Phone"),
            Item(name="TV"),
        ])


class TestSerializeResponse(AioHTTPTestCase):

    def get_app(self) -> AiorApplication:
        return AiorApplication(routes=[
            ("/json_array", JSONArrayHandler),
            ("/json", JSONHandler),
            ("/empty", EmptyHandler),
        ])

    @unittest_run_loop
    async def test_01_empty_json_response(self):
        response = await self.client.get("/empty")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8", response.headers["Content-Type"])
        res = await response.text()
        self.assertEqual("", res)

    @unittest_run_loop
    async def test_02_no_content_response(self):
        response = await self.client.post("/empty")
        self.assertEqual(204, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.text()
        self.assertEqual("", res)

    @unittest_run_loop
    async def test_03_origin_response(self):
        response = await self.client.put("/empty")
        self.assertEqual(200, response.status)
        self.assertEqual("application/octet-stream",
                         response.headers["Content-Type"])
        res = await response.text()
        self.assertEqual("", res)

    @unittest_run_loop
    async def test_04_response_str(self):
        response = await self.client.get("/json")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.text()
        self.assertEqual("Hello world", res)

    @unittest_run_loop
    async def test_05_response_int(self):
        response = await self.client.post("/json")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.text()
        self.assertEqual("1", res)

    @unittest_run_loop
    async def test_06_response_float(self):
        response = await self.client.put("/json")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.text()
        self.assertEqual("0.5", res)

    @unittest_run_loop
    async def test_07_response_bool(self):
        response = await self.client.delete("/json")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.json()
        self.assertEqual(True, res)

    @unittest_run_loop
    async def test_08_response_dict(self):
        response = await self.client.patch("/json")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.json()
        self.assertDictEqual({"name": "Jane"}, res)

    @unittest_run_loop
    async def test_09_response_str_list(self):
        response = await self.client.get("/json_array")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.json()
        self.assertListEqual(["x", "y", "z"], res)

    @unittest_run_loop
    async def test_10_response_int_list(self):
        response = await self.client.post("/json_array")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.json()
        self.assertListEqual([1, 2, 3], res)

    @unittest_run_loop
    async def test_11_response_number_list(self):
        response = await self.client.put("/json_array")
        self.assertEqual(200, response.status)
        self.assertEqual("application/json; charset=utf-8",
                         response.headers["Content-Type"])
        res = await response.json()
        self.assertEqual([0.5, 1, 3.5], res)

    @unittest_run_loop
    async def test_12_response_bool_list(self):
        response = await self.client.delete("/json_array")
        self.assertEqual(200, response.status)
        res = await response.json()
        self.assertListEqual([True, False], res)

    @unittest_run_loop
    async def test_13_response_dict_list(self):
        response = await self.client.patch("/json_array")
        self.assertEqual(200, response.status)
        res = await response.json()
        self.assertListEqual([{'name': 'Jane'}, {'name': 'Jim'}], res)


class ItemQuery(BaseModel):
    q: str


class PlainHeaders(BaseModel):
    content_type: str = Field(..., alias="Content-Type")


class ItemPath(BaseModel):
    item_id: int


class ItemsHandler(BaseHTTPHandler):
    @staticmethod
    async def get(item: JSONBody[Item]):
        return JSONResponse(item)

    @staticmethod
    async def post(item: JSONBody[Item], queries: Queries[ItemQuery]):
        d = item.dict()
        d.update({"q": queries.q})
        return JSONResponse(d)

    @staticmethod
    async def put(item: JSONBody[Item], queries: Queries[ItemQuery], headers: Headers[PlainHeaders]):
        d = item.dict()
        d.update({"q": queries.q})
        d.update({"Content-Type": headers.content_type})
        return JSONResponse(d)


class ItemInfoHandler(BaseHTTPHandler):
    @staticmethod
    async def get(item: JSONBody[Item], queries: Queries[ItemQuery],
                  headers: Headers[PlainHeaders], path_args: PathArgs[ItemPath]):
        d = item.dict()
        d.update({"q": queries.q})
        d.update({"Content-Type": headers.content_type})
        d.update({"item_id": path_args.item_id})
        return JSONResponse(d)


class TestDeserializeRequest(AioHTTPTestCase):

    def get_app(self) -> AiorApplication:
        return AiorApplication(routes=[
            ("/items/{item_id}", ItemInfoHandler),
            ("/items", ItemsHandler),
        ])

    @unittest_run_loop
    async def test_01_deserialize_body(self):
        response = await self.client.get("/items",
                                         json={"name": "Phone"})
        self.assertEqual(200, response.status)
        res = await response.json()
        self.assertDictEqual({'name': 'Phone'}, res)

    @unittest_run_loop
    async def test_02_deserialize_body_and_query(self):
        response = await self.client.post("/items",
                                          json={"name": "Phone"},
                                          params={"q": "one"})
        self.assertEqual(200, response.status)
        res = await response.json()
        self.assertDictEqual({'name': 'Phone', 'q': 'one'}, res)

    @unittest_run_loop
    async def test_03_response_body_and_query_and_headers(self):
        response = await self.client.put("/items",
                                         json={"name": "Phone"},
                                         params={"q": "one"},
                                         headers={"Content-Type": "text/plain"})
        self.assertEqual(200, response.status)
        res = await response.json()
        self.assertDictEqual({'name': 'Phone', 'q': 'one', 'Content-Type': 'text/plain'}, res)

    @unittest_run_loop
    async def test_04_response_path_body_and_query_and_headers(self):
        response = await self.client.get("/items/1",
                                         json={"name": "Phone"},
                                         params={"q": "one"})
        self.assertEqual(200, response.status)
        res = await response.json()
        self.assertDictEqual({'name': 'Phone', 'q': 'one', 'Content-Type': 'application/json', 'item_id': 1}, res)


class ItemsTestHandler(BaseHTTPHandler):
    @staticmethod
    async def post(item: JSONBody[Item]):
        return JSONResponse(item)


class TestHTTPError(AioHTTPTestCase):
    def get_app(self) -> AiorApplication:
        return AiorApplication(routes=[
            ("/items", ItemsTestHandler),
        ])

    @unittest_run_loop
    async def test_01_bad_request(self):
        response = await self.client.post("/items",
                                          json={"nam": "Phone"})
        self.assertEqual(400, response.status)
        res = await response.json()
        expected_body = [{'loc': ['name'],
                          'msg': 'field required',
                          'type': 'value_error.missing'}]
        self.assertListEqual(expected_body, res)
