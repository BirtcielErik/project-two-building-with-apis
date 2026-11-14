"""Pytest fixtures shared by every test in the project.

Fixtures marked ``autouse=True`` run automatically for every test, so no test
has to ask for them.
"""

import socket
from collections.abc import Iterator
from typing import NoReturn

import pytest
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.test import Client

NETWORK_BLOCKED_MESSAGE = (
    "Network access is blocked during tests. Mock the Open Library service "
    "(with `responses` or `monkeypatch`) instead of calling the real internet."
)


class NetworkBlockedError(RuntimeError):
    """Raised when a test tries to open a real network connection."""


def _refuse_network(*args: object, **kwargs: object) -> NoReturn:
    """Stand-in for socket functions: always fail with a clear message."""
    raise NetworkBlockedError(NETWORK_BLOCKED_MESSAGE)


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every real network connection fail during tests.

    Looking up a host name (DNS) and connecting a socket are the two steps any
    HTTP request must take, so replacing both catches every outbound call.
    ``monkeypatch`` puts the real functions back after each test.
    """
    monkeypatch.setattr(socket, "getaddrinfo", _refuse_network)
    monkeypatch.setattr(socket.socket, "connect", _refuse_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse_network)


@pytest.fixture
def logged_in_client(client: Client, django_user_model: type[AbstractUser]) -> Client:
    """A test client logged in as a fresh user named "reader"."""
    user = django_user_model.objects.create_user(username="reader", password="pw-12345-long")
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    """Empty Django's cache before and after each test.

    The in-memory cache holds Open Library search results and API throttle
    counters, so clearing it keeps one test from affecting another.
    """
    cache.clear()
    yield
    cache.clear()
