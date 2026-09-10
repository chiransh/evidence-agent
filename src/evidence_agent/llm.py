"""One place where provider errors become this package's typed errors.

Every node that calls the model goes through `model_errors()`, so the
retry policy in evidence_agent.graph can decide what to retry without any
node importing provider-specific exception classes.
"""

from contextlib import contextmanager

import anthropic

from evidence_agent.exceptions import ConfigurationError, ModelError, TransientError

MODEL = "claude-opus-5"

# The SDK raises a bare TypeError, not an auth error, when no credential
# resolves at request-build time. Match on its text so a genuine TypeError
# from our own code isn't swallowed and relabelled as a config problem.
_NO_CREDENTIAL = "Could not resolve authentication method"

_NO_CREDENTIAL_HELP = (
    "no Anthropic credentials found (set ANTHROPIC_API_KEY or run `ant auth login`)"
)


@contextmanager
def model_errors():
    try:
        yield
    except TypeError as exc:
        if _NO_CREDENTIAL in str(exc):
            raise ConfigurationError(_NO_CREDENTIAL_HELP) from exc
        raise
    except anthropic.AuthenticationError as exc:
        raise ConfigurationError("Anthropic rejected the configured credentials") from exc
    except anthropic.PermissionDeniedError as exc:
        raise ConfigurationError("Anthropic credentials lack the required permissions") from exc
    except (
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
        anthropic.InternalServerError,
    ) as exc:
        raise TransientError(str(exc)) from exc
    except anthropic.APIStatusError as exc:
        if exc.status_code >= 500:
            raise TransientError(str(exc)) from exc
        raise ModelError(str(exc)) from exc
    except anthropic.APIError as exc:
        raise ModelError(str(exc)) from exc


def client() -> anthropic.Anthropic:
    # The SDK retries connection errors and 429/5xx itself; the graph's retry
    # policy sits above that for anything it gives up on.
    return anthropic.Anthropic(max_retries=2)
