"""Tests that the test suite can never reach the real internet."""

import pytest
import requests


def test_real_http_call_fails_loudly():
    # ".invalid" is a reserved domain that never exists, so even if blocking
    # were broken this test would not reach a real website.
    with pytest.raises(Exception) as excinfo:
        requests.get("https://openlibrary.invalid/search.json?q=dune", timeout=5)

    assert "Network access is blocked during tests" in str(excinfo.value)
