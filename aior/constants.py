import logging

from aiohttp import hdrs
from pydantic import BaseModel

DEFAULT_LOGGING_FORMAT = "[%(asctime)s]%(levelname)s:%(name)s:%(message)s"
DEFAULT_LOGGING_LEVEL = logging.DEBUG
DEFAULT_LOGGING_FILE_WHEN = "d"
DEFAULT_LOGGING_FILE_INTERVAL = False
DEFAULT_LOGGING_FILE_DELAY = False
DEFAULT_LOGGING_FILE_ENCODING = "utf-8"


class Environment:
    DEV = "dev"
    PRD = "prd"
    TEST = "tests"
    ALPHA = "alpha"
    BETA = "beta"
    LOCAL = "local"


PING = "ping"
PONG = "pong"
HEARTBEAT_INTERVAL = 30.0
MAX_PING_RETRY = 2
RECONNECT_INTERVAL = 1.0

METHODS_ALL = hdrs.METH_ALL
REF_PREFIX = "#/components/schemas/"
DEFAULT_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}
NONE_RESPONSE = {"204": {"description": "No content"}}
DEFAULT_JSON_RESPONSE = {"200": {'content': {'application/json': {'schema': {}}},
                                 'description': 'OK'}}

FUNERAL_DATE = 30 * 60.0
CHECK_ACK_INTERVAL = 2.0
ACK_TIMEOUT = 15.0

HEALTHY = 0x0
SICK = 0x1
DEAD = 0x2
BURIED = 0x3

RPC_TIMEOUT = 10

NoneType = type(None)

JSON_TYPES = (BaseModel, str, float, int, bool)


class DBDialect:
    MySQL = "mysql"
    SQLite = "sqlite"
