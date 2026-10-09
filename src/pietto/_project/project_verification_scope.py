"""Call-scoped verification marks.

Inside one top-level call on one thread, a memoized structural verifier runs its
complete check at most once for the same exact argument objects; every new
top-level call verifies again. A mark is the check and the identity of every
argument, recorded only after the complete check returned normally; the scope
keeps those arguments alive until it ends, so no identity is reused inside it.
Marks are never results, never keyed by content, equality or pin, never
persisted, and never shared across calls or threads. An execution owner's
attempt (`boundary`) always starts a fresh scope.
"""

from __future__ import annotations

import functools
import inspect
import threading
from collections.abc import Callable
from typing import ParamSpec, TypeVar

__all__: tuple[str, ...] = ()

_P = ParamSpec("_P")
_R = TypeVar("_R")

_local = threading.local()


def _plain(function: Callable[..., object]) -> None:
    if (
        inspect.isgeneratorfunction(function)
        or inspect.iscoroutinefunction(function)
        or inspect.isasyncgenfunction(function)
    ):
        raise TypeError("VERIFICATION_SCOPE_ENTRY")


def entry(function: Callable[_P, _R]) -> Callable[_P, _R]:
    """Join the caller's scope, or open one for this call's duration."""
    _plain(function)

    @functools.wraps(function)
    def call(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        if getattr(_local, "scope", None) is not None:
            return function(*args, **kwargs)
        try:
            _local.scope = {}
            return function(*args, **kwargs)
        finally:
            _local.scope = None

    return call


def boundary(function: Callable[_P, _R]) -> Callable[_P, _R]:
    """An owner's attempt boundary: a fresh scope; the caller's is restored."""
    _plain(function)

    @functools.wraps(function)
    def call(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        outer = getattr(_local, "scope", None)
        try:
            _local.scope = {}
            return function(*args, **kwargs)
        finally:
            _local.scope = outer

    return call


def once(check: Callable[..., object], *subjects: object) -> None:
    """Run the complete `check(*subjects)` unless these exact objects already
    passed it in the current scope; without a scope, open one for its duration."""
    passed = getattr(_local, "scope", None)
    if passed is None:
        try:
            _local.scope = {}
            check(*subjects)
        finally:
            _local.scope = None
        return
    key = (check, *map(id, subjects))
    if key not in passed:
        check(*subjects)
        passed[key] = subjects
