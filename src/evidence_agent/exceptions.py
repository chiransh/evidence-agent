"""Typed errors for the pipeline.

The distinction that matters here is retryable vs not. A rate limit or a 5xx
is worth another attempt; a missing API key or a malformed model response is
not, and retrying it just turns a clear failure into a slow one. Nodes raise
these instead of letting provider-specific exceptions escape, so callers and
the graph's retry policy can tell the two apart without importing the
provider SDK or string-matching error text.
"""


class EvidenceAgentError(Exception):
    """Base for every error this package raises on purpose."""


class ConfigurationError(EvidenceAgentError):
    """Something the operator has to fix: missing credentials, bad settings.

    Never retryable.
    """


class TransientError(EvidenceAgentError):
    """A failure that may well succeed on another attempt: rate limits,
    upstream 5xx, connection resets."""


class SearchError(EvidenceAgentError):
    """The search backend failed in a way that isn't obviously transient."""


class ModelError(EvidenceAgentError):
    """The model call failed, or returned something the pipeline can't use."""
