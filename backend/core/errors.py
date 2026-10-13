class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def require(condition, status=403, code="forbidden", message="Access denied"):
    if not condition:
        raise ApiError(status, code, message)


def missing():
    return ApiError(404, "not_found", "Resource unavailable")
