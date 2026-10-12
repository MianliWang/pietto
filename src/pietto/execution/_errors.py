"""PIE-R codes and the errors of the public execution alpha.

Error text is built only from fixed vocabulary: the code, its category and
explanation, the private category word, the phase, the server's SQLSTATE and
the exception class name. No driver message, SQL, value or access field
enters it, and a public error is raised outside the handler of the private
exception it classifies, so neither ``__cause__`` nor ``__context__`` links one.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from pietto._project import project_execution as ex
from pietto._project.project_compiled_schema import CompiledError
from pietto._project.project_execution_source import SourceAdmissionError
from pietto._project.project_execution_template import BindingError
from pietto._project.project_guard_preparation import GuardPreparationError
from pietto._project.project_result_contract import ResultError
from pietto._project.project_scalar_meaning import ScalarMeaningError

if TYPE_CHECKING:
    from pietto.execution._handle import Outcome

__all__ = [
    "AttemptFailed",
    "CompileRejected",
    "ExecutionError",
    "Failure",
    "HandleMisuse",
    "RequestRejected",
]

# Every public code: (category, fixed explanation). docs/spec/diagnostics.md
# documents exactly these codes.
CODES = {
    "PIE-R1001": (
        "INPUT_MISSING",
        "a required argument is None; Pietto never substitutes a default for it",
    ),
    "PIE-R1002": (
        "INPUT_INVALID",
        "an input has the wrong type or an unsupported value",
    ),
    "PIE-R1003": (
        "ROUTE_REFUSED",
        "the route is not available in this alpha or does not fit the compiled query",
    ),
    "PIE-R1004": (
        "QUERY_NOT_EXECUTABLE",
        "the verified query cannot be prepared for execution",
    ),
    "PIE-R1005": (
        "CODE_IDENTITY",
        "the installed Pietto or ANTLR runtime code is not the code the query was"
        " compiled or accepted for, or its identity cannot be established",
    ),
    "PIE-R1006": (
        "VALUE_REFUSED",
        "the values do not fit the query's slots: their number differs, or a"
        " value's exact type or range is not its slot's",
    ),
    "PIE-R1007": (
        "BUNDLE_CONTENT",
        "the bundle bytes are not the bytes the expected pin names",
    ),
    "PIE-R1008": (
        "BUNDLE_NOT_ACCEPTED",
        "the bundle bytes are malformed, fail verification, or name a producer or"
        " compatibility other than the accepted ones",
    ),
    "PIE-R1999": (
        "REQUEST_UNCLASSIFIED",
        "the request was refused for a reason this alpha does not classify yet",
    ),
    "PIE-R2001": (
        "DEPENDENCY_MISSING",
        "a pinned dependency of the route is not installed;"
        " install the selected route's documented extra",
    ),
    "PIE-R2002": (
        "DRIVER_PROFILE",
        "the importable driver or PyArrow is not the route's pinned distribution,"
        " version and selected binary implementation, or is a copy from another"
        " location; or the driver or PyArrow cannot be loaded",
    ),
    "PIE-R2003": (
        "AMBIENT_ENVIRONMENT",
        "a refused route environment variable is set; unset it for this process",
    ),
    "PIE-R2004": (
        "CONNECTION_FAILED",
        "the selected route's connection, TLS profile or authentication failed;"
        " PostgreSQL requires TCP SCRAM-SHA-256, a password encrypted with"
        " password_encryption='scram-sha-256', and a first matching pg_hba.conf"
        " scram-sha-256 line; MySQL requires caching_sha2_password, TLS and a"
        " caller CA that verifies server identity",
    ),
    "PIE-R2005": (
        "TARGET_VERSION",
        "the server is not the selected route's pinned version (PostgreSQL 18.6"
        " or MySQL 8.4.12)",
    ),
    "PIE-R2006": (
        "SESSION_CONTEXT",
        "the session or its read-only transaction does not have the required settings",
    ),
    "PIE-R2007": (
        "SOURCE_QUALIFICATION",
        "a source relation does not qualify under the declared deployment premise",
    ),
    "PIE-R3001": ("DEADLINE", "the attempt reached its deadline (limits.seconds)"),
    "PIE-R3002": (
        "STATEMENT_TIMEOUT",
        "the server canceled a statement at the 10 second statement limit",
    ),
    "PIE-R3003": (
        "SERVER_ERROR",
        "the server or the open connection reported an error",
    ),
    "PIE-R3004": (
        "RESOURCE_LIMIT",
        "a row or byte limit would be exceeded; the whole batch was refused,"
        " not truncated",
    ),
    "PIE-R3005": (
        "RESULT_CHECK",
        "returned metadata or values do not match the result contract",
    ),
    "PIE-R3006": (
        "FINALIZATION",
        "the attempt could not commit or clean up at its end",
    ),
    "PIE-R3007": ("CONSUMER_ERROR", "the caller's code raised inside the with block"),
    "PIE-R3008": (
        "INTERRUPTED",
        "a BaseException that is not an Exception, such as KeyboardInterrupt,"
        " ended the attempt",
    ),
    "PIE-R3009": ("CANCELLED", "the caller cancelled the attempt before it completed"),
    "PIE-R3999": (
        "ATTEMPT_UNCLASSIFIED",
        "the attempt failed for a reason this alpha does not classify yet",
    ),
    "PIE-R4001": (
        "HANDLE_REUSED",
        "a result handle runs one attempt once; call execute() again for another",
    ),
    "PIE-R4002": ("BATCH_CLOSED", "the batch is closed"),
    "PIE-R4003": ("BATCH_TRANSFER", "the batch cannot be exported as requested"),
    "PIE-R4004": (
        "SCHEMA_EXPORT",
        "the result schema cannot be exported: PyArrow is missing, is not the"
        " pinned distribution or cannot be loaded, or the schema cannot be built;"
        " the attempt is unchanged",
    ),
    "PIE-R5001": ("CLEANUP_FAILED", "a cleanup step failed"),
    "PIE-R5002": (
        "DROPPED_UNCLOSED",
        "an open result handle was garbage-collected, or was still open at"
        " interpreter exit, without close(); use it as a context manager",
    ),
}

# Private owner refusals carry exactly one upper-case category word.
_OWNER_ERRORS = (
    ex.ExecutionError,
    BindingError,
    CompiledError,
    GuardPreparationError,
    ResultError,
    ScalarMeaningError,
    SourceAdmissionError,
    ValueError,
    TimeoutError,
)
# Refusals of the compiled query itself while an attempt is prepared.
_QUERY_ERRORS = (
    BindingError,
    CompiledError,
    GuardPreparationError,
    ResultError,
    ScalarMeaningError,
    SourceAdmissionError,
    ValueError,
)
_WORD = re.compile(r"[A-Z][A-Z0-9_]*(?::[0-9]+:[A-Za-z]+)?")
_SQLSTATE = re.compile(r"[0-9A-Z]{5}")

_REQUEST = {
    "POSTGRES_DEPLOYMENT_PREMISE_REQUIRED": "PIE-R1001",
    "MYSQL_DEPLOYMENT_PREMISE_REQUIRED": "PIE-R1001",
    "EXECUTION_REQUEST": "PIE-R1002",
    "EXECUTION_ARTIFACT": "PIE-R1002",
    "EXECUTION_ACCESS": "PIE-R1002",
    "EXECUTION_ACCESS_PROFILE": "PIE-R1002",
    "EXECUTION_LIMITS": "PIE-R1002",
    "EXECUTION_ISOLATION": "PIE-R1002",
    "POSTGRES_DEPLOYMENT_PREMISE_INVALID": "PIE-R1002",
    "POSTGRES_DEPLOYMENT_PREMISE_SCOPE": "PIE-R1002",
    "MYSQL_DEPLOYMENT_PREMISE_INVALID": "PIE-R1002",
    "MYSQL_DEPLOYMENT_PREMISE_SCOPE": "PIE-R1002",
    "EXECUTION_AMBIENT_CONNECTION_PROFILE": "PIE-R2003",
    "COMPILED_FRESH_PROFILE_REQUIRED": "PIE-R1003",
    "COMPILED_EXECUTION_ROUTE": "PIE-R1003",
    "EXECUTION_TARGET": "PIE-R1003",
    "UNFULFILLED_RUNTIME_OBLIGATION": "PIE-R1004",
    "EXECUTION_PRODUCER_NOT_DELIVERED": "PIE-R1004",
    "EXECUTION_REALIZATION_NOT_DELIVERED": "PIE-R1004",
    "COMPILED_COMPATIBILITY": "PIE-R1005",
    "COMPILED_CODE_ORIGIN": "PIE-R1005",
    "BINDING_SLOTS": "PIE-R1006",
}
# load_bundle's acceptance stage: the caller's records and the bundle bytes.
_BUNDLE = {
    "PUBLIC_BUNDLE_CODE_IDENTITY": "PIE-R1005",
    "COMPILED_CODE_ORIGIN": "PIE-R1005",
    "PUBLIC_BUNDLE_SIZE": "PIE-R1002",
    "COMPILED_CONTENT_PIN": "PIE-R1007",
    "PUBLIC_BUNDLE_UNSUPPORTED": "PIE-R1004",
}
_ATTEMPT = {
    "EXECUTION_DEPENDENCY_MISSING": "PIE-R2001",
    "ARROW_DEPENDENCY_MISSING": "PIE-R2001",
    "EXECUTION_DRIVER_VERSION": "PIE-R2002",
    "ARROW_DEPENDENCY_VERSION": "PIE-R2002",
    "POSTGRES_DRIVER_LIBRARY": "PIE-R2002",
    "EXECUTION_AMBIENT_CONNECTION_PROFILE": "PIE-R2003",
    "EXECUTION_TARGET_VERSION": "PIE-R2005",
    "EXECUTION_CONTEXT": "PIE-R2006",
    "EXECUTION_CONNECTION": "PIE-R2006",
    "POSTGRES_SOURCE_NATIVE_CONTEXT": "PIE-R2006",
    # The shared source qualification names an object outside the premise.
    "POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE": "PIE-R2007",
    "EXECUTION_DEADLINE": "PIE-R3001",
    "EXECUTION_RESOURCE_LIMIT": "PIE-R3004",
    "POSTGRES_SOURCE_RESOURCE_LIMIT": "PIE-R3004",
    "GUARD_RESOURCE_LIMIT": "PIE-R3004",
    "LIMIT": "PIE-R3004",
    "EXECUTION_FINALIZATION": "PIE-R3006",
}
_ATTEMPT_PREFIXES = (
    ("POSTGRES_TRANSACTION_", "PIE-R2006"),
    ("POSTGRES_SOURCE_", "PIE-R2007"),
)


@dataclass(frozen=True, slots=True)
class Failure:
    """One classified failure. ``code`` is the PIE-R code and ``category`` its
    name; code against these. ``detail`` is the private category word, which
    may change between alpha releases. ``phase`` names where it happened,
    ``sqlstate`` is the server's SQLSTATE and ``cause`` the exception class."""

    code: str
    category: str
    detail: str | None = None
    phase: str | None = None
    sqlstate: str | None = None
    cause: str | None = None

    def __str__(self) -> str:
        context = ", ".join(
            name + "=" + value
            for name, value in (
                ("detail", self.detail),
                ("phase", self.phase),
                ("sqlstate", self.sqlstate),
                ("cause", self.cause),
            )
            if value is not None
        )
        text = self.code + " " + self.category + ": " + CODES[self.code][1]
        return text + (" (" + context + ")" if context else "")


def failure(
    code: str,
    detail: str | None = None,
    *,
    phase: str | None = None,
    sqlstate: str | None = None,
    cause: str | None = None,
) -> Failure:
    return Failure(code, CODES[code][0], detail, phase, sqlstate, cause)


class ExecutionError(Exception):
    """Base of the PIE-R errors: ``failure`` classifies it, ``attempt`` and
    ``outcome`` describe the attempt it ended, if there was one."""

    def __init__(
        self,
        failure: Failure,
        *,
        attempt: str | None = None,
        outcome: Outcome | None = None,
    ):
        super().__init__(str(failure))
        self.failure = failure
        self.attempt = attempt
        self.outcome = outcome

    @property
    def code(self) -> str:
        return self.failure.code

    @property
    def category(self) -> str:
        return self.failure.category

    @property
    def detail(self) -> str | None:
        return self.failure.detail


class RequestRejected(ExecutionError):
    """PIE-R1xxx: refused before any connection; there is no attempt."""


class AttemptFailed(ExecutionError):
    """PIE-R2xxx and PIE-R3xxx: the attempt failed and is closed; ``outcome``
    is its final state."""


class HandleMisuse(ExecutionError):
    """PIE-R4xxx: a handle or batch was used against its lifecycle; the
    attempt's state is unchanged."""


class CompileRejected(Exception):
    """compile_query refused the project input. ``status`` is INPUT_REJECTED
    or BLOCKED and ``emission`` is the ``pietto.sql-emission.v1`` failure
    document, byte for byte what ``pietto emit-sql --project ... --format json``
    prints for the same input; str() is that command's ``--format text`` report.
    """

    def __init__(self, status: str, emission: bytes, text: str):
        super().__init__(text)
        self.status = status
        self.emission = emission


def category_word(error):
    """The category word of a private owner's refusal, or None for a driver or
    Arrow exception, whose message is never read."""
    args = getattr(error, "args", None)
    if (
        type(error) in _OWNER_ERRORS
        and type(args) is tuple
        and len(args) == 1
        and type(args[0]) is str
        and _WORD.fullmatch(args[0])
    ):
        return args[0]
    return None


def sqlstate(error):
    state = getattr(error, "sqlstate", None)
    return state if type(state) is str and _SQLSTATE.fullmatch(state) else None


def request_failure(error):
    """Classify a refusal raised while a request is prepared (no I/O)."""
    word = category_word(error)
    if word in _REQUEST:
        code = _REQUEST[word]
    elif word is not None and word.startswith("BINDING_VALUE:"):
        code = "PIE-R1006"
    elif word is not None and type(error) in _QUERY_ERRORS:
        code = "PIE-R1004"
    else:
        code = "PIE-R1999"
    return failure(code, word, cause=type(error).__name__)


def bundle_failure(error):
    """Classify a refusal of the caller's records or the bundle bytes (no I/O)."""
    word = category_word(error)
    if word in _BUNDLE:
        code = _BUNDLE[word]
    elif word is not None and type(error) is CompiledError:
        code = "PIE-R1008"
    else:
        code = "PIE-R1999"
    return failure(code, word, cause=type(error).__name__)


def attempt_failure(error, *, phase, deadline, connected, driver=False):
    """Classify an exception that ended an attempt. A deadline wins over the
    exception it caused; before the session exists, an exception of the
    route's driver (`driver`) is a connection failure and any other one is
    unclassified."""
    word = category_word(error)
    state = sqlstate(error)
    if word == "EXECUTION_REUSE":
        code = "PIE-R4001"
    elif deadline:
        code = "PIE-R3001"
    elif word is not None:
        code = _ATTEMPT.get(word) or next(
            (c for prefix, c in _ATTEMPT_PREFIXES if word.startswith(prefix)), None
        )
        if code is None:
            code = {ResultError: "PIE-R3005", SourceAdmissionError: "PIE-R2007"}.get(
                type(error), "PIE-R3999"
            )
    elif isinstance(error, ImportError):
        code = "PIE-R2002"
    elif not connected:
        code = "PIE-R2004" if driver else "PIE-R3999"
    elif state == "57014":
        code = "PIE-R3002"
    else:
        code = "PIE-R3003"
    return failure(code, word, phase=phase, sqlstate=state, cause=type(error).__name__)


def record_failure(record, code):
    """A failure the owner recorded without raising it through the public layer."""
    return failure(
        code, phase=record.phase, sqlstate=sqlstate(record), cause=record.kind
    )


def batch_failure(error):
    word = category_word(error)
    code = "PIE-R4002" if word == "INTEROP_CLOSED" else "PIE-R4003"
    return failure(code, word, cause=type(error).__name__)


def schema_failure(error):
    """Classify a schema-export refusal without exposing private messages."""
    return failure("PIE-R4004", category_word(error), cause=type(error).__name__)
