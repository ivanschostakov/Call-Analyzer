from openai import DefaultAsyncHttpxClient

from src.app.openai_client import build_openai_async_client


def test_build_openai_async_client_uses_proxy_when_configured() -> None:
    client = build_openai_async_client("test-key", proxy_url="http://127.0.0.1:3128")

    assert client is not None
    assert isinstance(client._client, DefaultAsyncHttpxClient)
    assert getattr(client._client, "_mounts", {})


def test_build_openai_async_client_without_proxy_uses_default_client() -> None:
    client = build_openai_async_client("test-key", proxy_url=None)

    assert client is not None
    assert not getattr(client._client, "_mounts", {})
