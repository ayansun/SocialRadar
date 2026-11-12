"""Business errors raised by services.

Services do not know about HTTP. They raise one of these exceptions and
`main.py` converts it into a JSON response with the right status code.
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """The requested resource does not exist -> 404."""

    status_code = 404


class ConflictError(AppError):
    """The request conflicts with the current state -> 409."""

    status_code = 409


class BusinessRuleError(AppError):
    """The data is well-formed but breaks a business rule -> 422."""

    status_code = 422
