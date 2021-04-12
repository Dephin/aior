from typing import TypeVar, Union

from pydantic import BaseModel

sentinel = object()
Url = str
JsonType = Union[int, str, bool, list, dict]

T = TypeVar('T')
T_body = TypeVar('T_body', BaseModel, int, str, bool, covariant=True)
T_json_obj = TypeVar('T_json_obj', BaseModel, list, int, str, bool, covariant=True)
T_headers = TypeVar('T_headers', BaseModel, dict, float, int, str, bool, covariant=True)
T_queries = TypeVar('T_queries', BaseModel, dict, float, int, str, bool, covariant=True)
T_path_args = TypeVar('T_path_args', BaseModel, dict, float, int, str, bool, covariant=True)
T_json = TypeVar('T_json', list, int, str, bool, covariant=True)
T_model = TypeVar('T_model', bound=BaseModel)
T_client = TypeVar("T_client")

NoneType = type(None)
JSONType = Union[int, float, str, bool, dict, list, BaseModel]

Token = str

StrOrBytesMsg = Union[str, bytes]
JsonMsg = Union[int, str, bool, dict]
EventData = MsgDict = dict
RpcID = SequenceID = EventName = MsgID = MsgStr = str
SeqNum = int
