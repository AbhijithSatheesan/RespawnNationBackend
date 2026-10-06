from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: dict | None = None

    @classmethod
    def ok(cls, data=None):
        return cls(
            success=True,
            data=data
        )

    @classmethod
    def fail(
        cls,
        code: str,
        message: str,
        retryable: bool = False
    ):
        return cls(
            success=False,
            error={
                "code": code,
                "message": message,
                "retryable": retryable,
            }
        )