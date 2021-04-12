import asyncio
import sys
from asyncio import StreamReaderProtocol, AbstractEventLoop
from typing import Optional

__all__ = ('BaseStandardInputHandler',)


class BaseStandardInputHandler(StreamReaderProtocol):
    def __init__(self, loop: Optional[AbstractEventLoop] = None):
        self._loop = loop
        stream_reader = asyncio.StreamReader(loop=self._loop)
        super().__init__(stream_reader)

    def connect(self):
        self._loop.create_task(
            self._loop.connect_read_pipe(lambda: self, sys.stdin))

    def data_received(self, data: bytes):
        text = data.decode("utf-8").strip()
        self._loop.create_task(self.on_message(text))

    async def on_message(self, data: str):
        """
        overwrite this function to process input message
        """
