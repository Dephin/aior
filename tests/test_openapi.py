import unittest
from typing import List, Optional, Union

from aiohttp.test_utils import unittest_run_loop, AioHTTPTestCase
from pydantic import BaseModel

from aior.application import AiorApplication
from aior.components import BaseHTTPHandler, JSONResponse, BadRequestError, CreatedStatus, \
    OriginResponse, NoContentResponse, JSONBody, Queries, PathArgs

expected_openapi_schema = {'components': {'schemas': {'Address': {'properties': {'city': {'title': 'City',
                                                                                          'type': 'string'},
                                                                                 'province': {'title': 'Province',
                                                                                              'type': 'string'}},
                                                                  'required': ['province', 'city'],
                                                                  'title': 'Address',
                                                                  'type': 'object'},
                                                      'Item': {'properties': {
                                                          'address': {'$ref': '#/components/schemas/Address'},
                                                          'description': {'title': 'Description',
                                                                          'type': 'string'},
                                                          'name': {'title': 'Name',
                                                                   'type': 'string'},
                                                          'price': {'title': 'Price',
                                                                    'type': 'number'},
                                                          'tax': {'title': 'Tax',
                                                                  'type': 'number'}},
                                                               'required': ['name', 'price', 'address'],
                                                               'title': 'Item',
                                                               'type': 'object'},
                                                      'LoginUser': {'properties': {'password': {'title': 'Password',
                                                                                                'type': 'string'},
                                                                                   'username': {'title': 'Username',
                                                                                                'type': 'string'}},
                                                                    'required': ['username', 'password'],
                                                                    'title': 'LoginUser',
                                                                    'type': 'object'},
                                                      'Shop': {'properties': {
                                                          'items': {'items': {'$ref': '#/components/schemas/Item'},
                                                                    'title': 'Items',
                                                                    'type': 'array'}},
                                                               'required': ['items'],
                                                               'title': 'Shop',
                                                               'type': 'object'},
                                                      'SignUpUser': {'properties': {
                                                          'address': {'$ref': '#/components/schemas/Address'},
                                                          'password': {'title': 'Password',
                                                                       'type': 'string'},
                                                          'username': {'title': 'Username',
                                                                       'type': 'string'}},
                                                                     'required': ['username',
                                                                                  'password',
                                                                                  'address'],
                                                                     'title': 'SignUpUser',
                                                                     'type': 'object'},
                                                      'UserInfo': {'properties': {'user_name': {'title': 'User '
                                                                                                         'Name',
                                                                                                'type': 'string'}},
                                                                   'required': ['user_name'],
                                                                   'title': 'UserInfo',
                                                                   'type': 'object'},
                                                      'UserNameQuery': {'properties': {'q': {'title': 'Q',
                                                                                             'type': 'string'}},
                                                                        'required': ['q'],
                                                                        'title': 'UserNameQuery',
                                                                        'type': 'object'},
                                                      'UserPath': {'properties': {'user_id': {'title': 'User '
                                                                                                       'Id',
                                                                                              'type': 'integer'}},
                                                                   'required': ['user_id'],
                                                                   'title': 'UserPath',
                                                                   'type': 'object'}}},
                           'info': {'title': 'Aior API', 'version': '0.1.0'},
                           'openapi': '3.0.2',
                           'paths': {'/users/sessions': {'delete': {'operationId': 'users_sessions__delete',
                                                                    'requestBody': {'content': {'application/json': {
                                                                        'schema': {
                                                                            '$ref': '#/components/schemas/LoginUser'}}},
                                                                                    'required': True},
                                                                    'responses': {'200': {'description': 'OK'}},
                                                                    'summary': 'Delete User Session'},
                                                         'get': {'operationId': 'users_sessions__get',
                                                                 'summary': 'Get User Session'},
                                                         'patch': {'operationId': 'users_sessions__patch',
                                                                   'requestBody': {'content': {'application/json': {
                                                                       'schema': {
                                                                           '$ref': '#/components/schemas/LoginUser'}}},
                                                                                   'required': True},
                                                                   'responses': {'200': {'content': {
                                                                       'application/json; charset=utf-8': {'schema': {
                                                                           '$ref': '#/components/schemas/UserInfo'}}},
                                                                                         'description': 'OK'}},
                                                                   'summary': 'Patch User Session'},
                                                         'post': {'operationId': 'users_sessions__post',
                                                                  'requestBody': {'content': {'application/json': {
                                                                      'schema': {
                                                                          '$ref': '#/components/schemas/LoginUser'}}},
                                                                                  'required': True},
                                                                  'summary': 'Post User Session'},
                                                         'put': {'operationId': 'users_sessions__put',
                                                                 'requestBody': {'content': {'application/json': {
                                                                     'schema': {
                                                                         '$ref': '#/components/schemas/LoginUser'}}},
                                                                                 'required': True},
                                                                 'summary': 'Put User Session'}},
                                     '/users/sessions2': {'get': {'operationId': 'users_sessions2__get',
                                                                  'requestBody': {'content': {'application/json': {
                                                                      'schema': {
                                                                          '$ref': '#/components/schemas/LoginUser'}}},
                                                                                  'required': True},
                                                                  'summary': 'Get User Session2'},
                                                          'post': {'operationId': 'users_sessions2__post',
                                                                   'parameters': [{'in': 'query',
                                                                                   'name': 'queries',
                                                                                   'required': False,
                                                                                   'schema': {'properties': {
                                                                                       'q': {'title': 'Q',
                                                                                             'type': 'string'}},
                                                                                              'title': 'UserNameQuery',
                                                                                              'type': 'object'}}],
                                                                   'requestBody': {'content': {'application/json': {
                                                                       'schema': {
                                                                           '$ref': '#/components/schemas/LoginUser'}}},
                                                                                   'required': True},
                                                                   'summary': 'Post User Session2'}},
                                     '/users/{user_id}': {'get': {'operationId': 'users__user_id__get',
                                                                  'parameters': [{'in': 'query',
                                                                                  'name': 'path',
                                                                                  'required': False,
                                                                                  'schema': {'properties': {
                                                                                      'user_id': {'title': 'User '
                                                                                                           'Id',
                                                                                                  'type': 'integer'}},
                                                                                             'title': 'UserPath',
                                                                                             'type': 'object'}}],
                                                                  'requestBody': {'content': {'application/json': {
                                                                      'schema': {
                                                                          '$ref': '#/components/schemas/SignUpUser'}}},
                                                                                  'required': True},
                                                                  'responses': {'200': {'content': {
                                                                      'application/json; charset=utf-8': {'schema': {
                                                                          '$ref': '#/components/schemas/Item'}}},
                                                                                        'description': 'OK'}},
                                                                  'summary': 'Get User Info'},
                                                          'post': {'operationId': 'users__user_id__post',
                                                                   'parameters': [{'in': 'query',
                                                                                   'name': 'path',
                                                                                   'required': False,
                                                                                   'schema': {'properties': {
                                                                                       'user_id': {'title': 'User '
                                                                                                            'Id',
                                                                                                   'type': 'integer'}},
                                                                                              'title': 'UserPath',
                                                                                              'type': 'object'}}],
                                                                   'requestBody': {'content': {'application/json': {
                                                                       'schema': {
                                                                           '$ref': '#/components/schemas/SignUpUser'}}},
                                                                                   'required': True},
                                                                   'responses': {'200': {'content': {
                                                                       'application/json; charset=utf-8': {'schema': {
                                                                           '$ref': '#/components/schemas/Shop'}}},
                                                                                         'description': 'OK'}},
                                                                   'summary': 'Post User Info'}}}}


class LoginUser(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    user_name: str


class UserPath(BaseModel):
    user_id: int


class Address(BaseModel):
    province: str
    city: str


class UserNameQuery(BaseModel):
    q: str


class SignUpUser(LoginUser):
    address: Address


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None
    address: Address


class Shop(BaseModel):
    items: List[Item]


class UserSessionHandler(BaseHTTPHandler):
    async def get(self) -> OriginResponse:
        ...

    async def post(self, body: JSONBody[LoginUser]) -> NoContentResponse:
        ...

    async def put(self, body: JSONBody[LoginUser]) -> NoContentResponse:
        ...

    async def delete(self, body: JSONBody[LoginUser]) -> JSONResponse[None]:
        ...

    async def patch(self, body: JSONBody[LoginUser]) -> JSONResponse[UserInfo]:
        ...


class UserSession2Handler(BaseHTTPHandler):
    async def get(
            self, body: JSONBody[LoginUser]
    ) -> JSONResponse[
        Union[UserInfo, BadRequestError]
    ]:
        ...

    async def post(
            self, body: JSONBody[LoginUser], queries: Queries[UserNameQuery]
    ) -> JSONResponse[
        Union[UserInfo, CreatedStatus, BadRequestError]
    ]:
        ...


class UserInfoHandler(BaseHTTPHandler):
    async def get(self, body: JSONBody[SignUpUser], path: PathArgs[UserPath]) -> JSONResponse[Item]:
        ...

    async def post(self, body: JSONBody[SignUpUser], path: PathArgs[UserPath]) -> JSONResponse[Shop]:
        ...


# TODO: test swagger ui html
class TestWithoutTypeHintHTTPTestCase(AioHTTPTestCase):

    def get_app(self) -> AiorApplication:
        return AiorApplication(routes=[
            ("/users/{user_id}", UserInfoHandler),
            ("/users/sessions", UserSessionHandler),
            ("/users/sessions2", UserSession2Handler),
        ])

    @unittest_run_loop
    async def test_01_request_model(self):
        schema = self.app.openapi()
        import pprint
        pprint.pprint(schema)
        self.assertDictEqual(expected_openapi_schema, schema)


if __name__ == '__main__':
    unittest.main()
