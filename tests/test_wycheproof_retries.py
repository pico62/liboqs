
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


def test_mlkem_processes_downloaded_data():
    import json
    from test_wycheproof_vectors import fetch_wycheproof_kem_test_cases

    test_data = {
        "testGroups": [{
            "parameterSet": "ML-KEM-512",
            "type": "MlKemTest",
            "tests": [{"tcId": 1}, {"tcId": 2}]
        }]
    }

    response = Mock()
    response.content = json.dumps(test_data).encode("utf-8")

    with patch(
        "test_wycheproof_vectors._cached_requests_get_with_retries",
        return_value=response
    ) as download:
        result = fetch_wycheproof_kem_test_cases(
            "ML-KEM-512", "test", ["MlKemTest"]
        )

    assert len(result) == 2
    assert result[0]["tcId"] == 1
    assert result[1]["tcId"] == 2
    download.assert_called_once()


def test_mldsa_processes_downloaded_data():
    import json
    from test_wycheproof_vectors import fetch_wycheproof_sig_test_cases

    test_data = {
        "testGroups": [{
            "type": "MlDsaTest",
            "tests": [{"tcId": 1}, {"tcId": 2}]
        }]
    }

    response = Mock()
    response.content = json.dumps(test_data).encode("utf-8")

    with patch(
        "test_wycheproof_vectors._cached_requests_get_with_retries",
        return_value=response
    ) as download:
        result = fetch_wycheproof_sig_test_cases(
            "ML-DSA-44", "test", ["MlDsaTest"]
        )

    assert len(result) == 2
    assert result[0][1]["tcId"] == 1
    assert result[1][1]["tcId"] == 2
    download.assert_called_once()


def test_invalid_json_raises_error():
    import json
    from test_wycheproof_vectors import fetch_wycheproof_kem_test_cases

    response = Mock()
    response.content = b"invalid json"

    with patch(
        "test_wycheproof_vectors._cached_requests_get_with_retries",
        return_value=response
    ):
        with pytest.raises(json.JSONDecodeError):
            fetch_wycheproof_kem_test_cases(
                "ML-KEM-512", "test", ["MlKemTest"]
            )


