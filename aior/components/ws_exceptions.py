__all__ = ('WebSocketException',)


class WebSocketException(Exception):
    def __init__(self, info: str = None):
        self._info = info

    def __str__(self):
        return f'{"error": "{self._info}"}'
