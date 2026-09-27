"""Target scope and authorization boundaries.

This module deliberately performs no network requests. It only validates whether a
requested target/action is inside an explicitly configured scope.
"""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from urllib.parse import urlparse


class ScopeError(ValueError):
    pass


@dataclass(frozen=True)
class Scope:
    program: str
    allowed_hosts: tuple[str, ...]
    excluded_hosts: tuple[str, ...] = ()
    allowed_paths: tuple[str, ...] = ("/",)
    excluded_paths: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self):
        if not self.program.strip():
            raise ScopeError("program name is required")
        if not self.allowed_hosts:
            raise ScopeError("at least one allowed host is required")

    @staticmethod
    def _host(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ScopeError("target must be an absolute HTTP(S) URL")
        return parsed.hostname.lower().rstrip(".")

    @staticmethod
    def _path(url: str) -> str:
        return urlparse(url).path or "/"

    def contains(self, url: str) -> bool:
        host = self._host(url)
        path = self._path(url)

        if any(fnmatch(host, pattern.lower()) for pattern in self.excluded_hosts):
            return False
        if not any(fnmatch(host, pattern.lower()) for pattern in self.allowed_hosts):
            return False
        if any(fnmatch(path, pattern) for pattern in self.excluded_paths):
            return False
        return any(fnmatch(path, pattern) for pattern in self.allowed_paths)

    def require(self, url: str) -> None:
        if not self.contains(url):
            raise ScopeError(f"target is outside configured scope: {url}")

    def as_dict(self) -> dict:
        return {
            "program": self.program,
            "allowed_hosts": list(self.allowed_hosts),
            "excluded_hosts": list(self.excluded_hosts),
            "allowed_paths": list(self.allowed_paths),
            "excluded_paths": list(self.excluded_paths),
            "notes": self.notes,
        }
