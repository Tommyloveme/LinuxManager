from __future__ import annotations

from fastapi import HTTPException, status


class CedarError(Exception):
    def __init__(self, message: str, code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def as_http(self) -> HTTPException:
        return HTTPException(status_code=self.code, detail=self.message)


class NotFoundError(CedarError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ForbiddenError(CedarError):
    def __init__(self, message: str = "没有权限执行该操作") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class AuthError(CedarError):
    def __init__(self, message: str = "认证失败") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)
