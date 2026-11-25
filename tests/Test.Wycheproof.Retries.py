
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError, HTTPError

from test_wycheproof_vectors import _cached_requests_get_with_retries


def test_success_first_attempt():
    response = Mock()
    with patch("helpers.cached_requests_get", return_value=response) as download:
        assert _cached_requests_get_with_retries("https://example.com") is response
        download.assert_called_once()
        response.raise_for_status.assert_called_once()


def test_retry_then_success():
    response = Mock()
    with patch(
        "helpers.cached_requests_get",
        side_effect=[ConnectionError("Temporary connection reset"), response],
    ) as download, patch("time.sleep") as sleep:
        result = _cached_requests_get_with_retries("https://example.com")

    assert result is response
    assert download.call_count == 2
    sleep.assert_called_once_with(1.0)


def test_all_attempts_fail():
    with patch(
        "helpers.cached_requests_get",
        side_effect=ConnectionError("Network unavailable"),
    ) as download, patch("time.sleep") as sleep:
        with pytest.raises(pytest.skip.Exception):
            _cached_requests_get_with_retries("https://example.com")

    assert download.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1.0, 2.0]


def test_http_error():
    response = Mock()
    response.raise_for_status.side_effect = HTTPError("Server error")

    with patch(
        "helpers.cached_requests_get", return_value=response
    ) as download, patch("time.sleep"):
        with pytest.raises(pytest.skip.Exception):
            _cached_requests_get_with_retries("https://example.com")

    assert download.call_count == 3
