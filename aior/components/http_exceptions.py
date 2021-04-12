import json
from typing import Any, Optional

from aiohttp.typedefs import LooseHeaders
from aiohttp.web_exceptions import HTTPError

from aior.constants import DEFAULT_JSON_HEADERS

__all__ = (
    'BadRequestError',
    'UnauthorizedError',
    'PaymentRequiredError',
    'ForbiddenError',
    'NotFoundError',
    'MethodNotAllowedError',
    'NotAcceptableError',
    'ProxyAuthenticationRequiredError',
    'RequestTimeoutError',
    'ConflictError',
    'GoneError',
    'LengthRequiredError',
    'PreconditionFailedError',
    'RequestEntityTooLargeError',
    'RequestURITooLongError',
    'UnsupportedMediaTypeError',
    'RequestRangeNotSatisfiableError',
    'ExpectationFailedError',
    'UnprocessableEntityError',
    'FailedDependencyError',
    'UpgradeRequiredError',
    'PreconditionRequiredError',
    'TooManyRequestsError',
    'RequestHeaderFieldsTooLargeError',
    'UnavailableForLegalReasonsError',
    'InternalServerError',
    'BadGatewayError',
    'ServiceUnavailableError',
    'GatewayTimeoutError',
    'VersionNotSupportedError',
    'VariantAlsoNegotiatesError',
    'InsufficientStorageError',
    'NotExtendedError',
    'NetworkAuthenticationRequiredError',
)


class AiorHTTPError(HTTPError):
    def __init__(self,
                 details: Any = None,
                 text: Optional[str] = None,
                 headers: LooseHeaders = DEFAULT_JSON_HEADERS,
                 **kwargs: Any,
                 ) -> None:
        if text is None:
            text = json.dumps({'errors': details})
        super().__init__(text=text, headers=headers, **kwargs)


class BadRequestError(AiorHTTPError):
    status_code = 400

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Bad Request',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class UnauthorizedError(AiorHTTPError):
    status_code = 401

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Unauthorized',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class PaymentRequiredError(AiorHTTPError):
    status_code = 402

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Payment Required',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class ForbiddenError(AiorHTTPError):
    status_code = 403

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Forbidden',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class NotFoundError(AiorHTTPError):
    status_code = 404

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Not Found',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class MethodNotAllowedError(AiorHTTPError):
    status_code = 405

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Method Not Allowed',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class NotAcceptableError(AiorHTTPError):
    status_code = 406

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Not Acceptable',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class ProxyAuthenticationRequiredError(AiorHTTPError):
    status_code = 407

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Proxy Authentication',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class RequestTimeoutError(AiorHTTPError):
    status_code = 408

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Request Timeout',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class ConflictError(AiorHTTPError):
    status_code = 409

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Conflict',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class GoneError(AiorHTTPError):
    status_code = 410

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Gone',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class LengthRequiredError(AiorHTTPError):
    status_code = 411

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Length Required',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class PreconditionFailedError(AiorHTTPError):
    status_code = 412

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Precondition Failed',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class RequestEntityTooLargeError(AiorHTTPError):
    status_code = 413

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Request Entity',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class RequestURITooLongError(AiorHTTPError):
    status_code = 414

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Request URI Too Long',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class UnsupportedMediaTypeError(AiorHTTPError):
    status_code = 415

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Unsupported Media Type',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class RequestRangeNotSatisfiableError(AiorHTTPError):
    status_code = 416

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Request Range Not Satisfiable',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class ExpectationFailedError(AiorHTTPError):
    status_code = 417

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Expectation Failed',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class UnprocessableEntityError(AiorHTTPError):
    status_code = 422

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Unprocessable Entity',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class FailedDependencyError(AiorHTTPError):
    status_code = 424

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Failed Dependency',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class UpgradeRequiredError(AiorHTTPError):
    status_code = 426

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Upgrade Required',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class PreconditionRequiredError(AiorHTTPError):
    status_code = 428

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Precondition Required',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class TooManyRequestsError(AiorHTTPError):
    status_code = 429

    def __init__(self,
                 details: Any = None,
                 reason: str = 'TooMany Requests',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class RequestHeaderFieldsTooLargeError(AiorHTTPError):
    status_code = 431

    def __init__(self,
                 details: Any = None,
                 reason: str = '',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class UnavailableForLegalReasonsError(AiorHTTPError):
    status_code = 451

    def __init__(self,
                 details: Any = None,
                 reason: str = '',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class InternalServerError(AiorHTTPError):
    status_code = 500

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Internal Server',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class BadGatewayError(AiorHTTPError):
    status_code = 502

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Bad Gateway',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class ServiceUnavailableError(AiorHTTPError):
    status_code = 503

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Service Unavailable',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class GatewayTimeoutError(AiorHTTPError):
    status_code = 504

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Gateway Timeout',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class VersionNotSupportedError(AiorHTTPError):
    status_code = 505

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Version Not Supported',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class VariantAlsoNegotiatesError(AiorHTTPError):
    status_code = 506

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Variant Also Negotiates',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class InsufficientStorageError(AiorHTTPError):
    status_code = 507

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Insufficient Storage',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class NotExtendedError(AiorHTTPError):
    status_code = 510

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Not Extended',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)


class NetworkAuthenticationRequiredError(AiorHTTPError):
    status_code = 511

    def __init__(self,
                 details: Any = None,
                 reason: str = 'Network Authentication Required',
                 **kwargs: Any
                 ) -> None:
        super().__init__(details=details,
                         reason=reason,
                         **kwargs)
