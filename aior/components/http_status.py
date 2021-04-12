class BaseStatus:
    code: int = None
    reason: str = None


class OKStatus(BaseStatus):
    code: int = 200
    reason = "OK"


class CreatedStatus(BaseStatus):
    code: int = 201
    reason = "Created"


class AcceptedStatus(BaseStatus):
    code: int = 202
    reason = "Accepted"


class NonAuthoritativeInformationStatus(BaseStatus):
    code: int = 203
    reason = "Non-Authoritative Information"


class NoContentStatus(BaseStatus):
    code: int = 204
    reason = "No Content"


class ResetContentStatus(BaseStatus):
    code: int = 205
    reason = "Reset Content"
