#!/usr/bin/python
# -*- coding: utf-8 -*-
# @File    : test_ws_handler.py
# @Author  : dephin
# @Time    : 2020-07-30
import asyncio
import json
from typing import Union

import pytest
from aiohttp.test_utils import make_mocked_coro

from aior.application import AiorApplication
from aior.components import BaseWebSocketHandler


@pytest.fixture
def ws_handler_class():
    class TestWebSocketHandler(BaseWebSocketHandler):
        pass

    TestWebSocketHandler.on_open = make_mocked_coro()
    TestWebSocketHandler.on_close = make_mocked_coro()
    TestWebSocketHandler.on_message = make_mocked_coro()
    TestWebSocketHandler.on_error = make_mocked_coro()
    TestWebSocketHandler.on_eof = make_mocked_coro()
    TestWebSocketHandler.on_ping = make_mocked_coro()
    TestWebSocketHandler.on_pong = make_mocked_coro()

    return TestWebSocketHandler


async def make_client(aiohttp_client, ws_handler_class):
    app = AiorApplication(routes=[('/', ws_handler_class)])
    return await aiohttp_client(app)


async def test_websocket_on_open(loop, aiohttp_client, ws_handler_class) -> None:
    client = await make_client(aiohttp_client, ws_handler_class)
    await client.ws_connect('/')

    assert ws_handler_class.on_open.called
    assert not ws_handler_class.on_close.called
    assert not ws_handler_class.on_message.called
    assert not ws_handler_class.on_error.called
    assert not ws_handler_class.on_eof.called
    assert not ws_handler_class.on_ping.called
    assert not ws_handler_class.on_pong.called


async def test_websocket_on_message(loop, aiohttp_client, ws_handler_class) -> None:
    client = await make_client(aiohttp_client, ws_handler_class)
    ws = await client.ws_connect('/')

    await ws.send_str("")
    await asyncio.sleep(2)

    assert ws_handler_class.on_open.called
    assert not ws_handler_class.on_close.called
    ws_handler_class.on_message.assert_called_with("")
    assert not ws_handler_class.on_error.called
    assert not ws_handler_class.on_eof.called
    assert not ws_handler_class.on_ping.called
    assert not ws_handler_class.on_pong.called


async def test_websocket_on_close(loop, aiohttp_client, ws_handler_class) -> None:
    client = await make_client(aiohttp_client, ws_handler_class)
    await client.ws_connect('/')
    await client.close()

    assert ws_handler_class.on_open.called
    assert ws_handler_class.on_close.called
    assert not ws_handler_class.on_message.called
    assert not ws_handler_class.on_error.called
    assert not ws_handler_class.on_eof.called
    assert not ws_handler_class.on_ping.called
    assert not ws_handler_class.on_pong.called


async def test_websocket_reply(loop, aiohttp_client) -> None:
    class JsonWebSocketHandler(BaseWebSocketHandler):
        async def on_message(self, msg: Union[str, bytes]):
            msg_json = json.loads(msg)
            answer = msg_json['test']
            await self.send_str(answer)

    client = await make_client(aiohttp_client, JsonWebSocketHandler)
    ws = await client.ws_connect('/')

    expected_value = 'value'
    payload = '{"test": "%s"}' % expected_value
    await ws.send_str(payload)

    resp = await ws.receive()
    assert resp.data == expected_value
