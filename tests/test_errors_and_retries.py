import anthropic
import httpx
import pytest

from evidence_agent.exceptions import ConfigurationError, ModelError, TransientError
from evidence_agent.graph import NETWORK_RETRY
from evidence_agent.llm import model_errors


def _status_error(cls, status_code: int):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code, request=request)
    return cls("boom", response=response, body=None)


def test_missing_credential_typeerror_becomes_configuration_error():
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        with model_errors():
            raise TypeError("Could not resolve authentication method. Expected one of api_key")


def test_unrelated_typeerror_is_not_swallowed():
    # A genuine bug in our own code must not be relabelled as a config problem.
    with pytest.raises(TypeError, match="unexpected keyword"):
        with model_errors():
            raise TypeError("got an unexpected keyword argument 'mdoel'")


def test_rate_limit_becomes_transient():
    with pytest.raises(TransientError):
        with model_errors():
            raise _status_error(anthropic.RateLimitError, 429)


def test_server_error_becomes_transient():
    with pytest.raises(TransientError):
        with model_errors():
            raise _status_error(anthropic.InternalServerError, 503)


def test_client_error_becomes_model_error_not_transient():
    with pytest.raises(ModelError):
        with model_errors():
            raise _status_error(anthropic.BadRequestError, 400)


def test_retry_policy_retries_transient_only():
    retry_on = NETWORK_RETRY.retry_on
    assert retry_on is TransientError

    # A missing key would fail identically on every attempt, so it must not retry.
    assert not issubclass(ConfigurationError, TransientError)
    assert not issubclass(ModelError, TransientError)
