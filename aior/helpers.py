import asyncio
import logging
import random
from typing import Any, Callable, Coroutine

__all__ = ('app_log', 'PeriodicCallback', 'PLDFilter')

app_log = logging.getLogger()


class PeriodicCallback:
    def __init__(self,
                 fn: Callable[..., Coroutine],
                 *args: Any,
                 interval: float = 1.0,
                 **kwargs: Any
                 ):
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._interval = interval
        self._is_running = False
        self._task = None

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.ensure_future(self._run())

    def stop(self):
        if self._is_running:
            self._is_running = False
            if not self._task.cancelled():
                self._task.cancel()
            # with suppress(asyncio.CancelledError):
            #     await self._task

    async def _run(self):
        while True:
            await self._fn(*self._args, **self._kwargs)
            await asyncio.sleep(self._interval)

    @property
    def is_running(self) -> bool:
        return self._is_running


"""
## PLD模式
**为了模拟测试网络通讯场景，在最终发送消息时加上write_hook方法，根据概率触发 延时、丢包、断开连接等情况**
"""


class PLDFilter:

    def __init__(self,
                 p_drop=0,
                 p_order=0,
                 max_order=1,
                 p_delay=0,
                 max_delay=10 * 1000,
                 p_corrupt=0,
                 seed=10):
        self.p_drop = p_drop
        self.p_order = p_order
        self.max_order = max_order
        self.p_delay = p_delay
        self.max_delay = max_delay
        self.p_corrupt = p_corrupt
        random.seed(seed)
        self.event = None

    async def __call__(self, handler, msg):
        self.event = 'Send'
        await self._judge(handler, msg)
        app_log.debug(f"PLD filter:{self.event}: {msg}")

    async def _judge(self, handler, message):
        p = random.random()
        if p <= self.p_drop:
            self.event = 'Drop'
            return

        p = random.random()
        if p <= self.p_corrupt:
            self.event = 'Corrupt'
            handler.close()
            return

        p = random.random()
        if p <= self.p_delay:
            self.event = 'Delay'
            p = random.random()
            await asyncio.sleep(p * self.max_delay / 1000)

        await handler.write_message(message)
