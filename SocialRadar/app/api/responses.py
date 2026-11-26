"""Error responses shown in Swagger for each endpoint."""

from app.schemas.common import ErrorResponse

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource not found"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Conflict with current state"}}
