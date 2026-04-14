from openai import AsyncOpenAI, DefaultAsyncHttpxClient

from config import OPENAI_HTTP_PROXY


def build_openai_async_client(
    api_key: str | None,
    *,
    proxy_url: str | None = OPENAI_HTTP_PROXY,
) -> AsyncOpenAI | None:
    if not api_key:
        return None

    if proxy_url:
        return AsyncOpenAI(
            api_key=api_key,
            http_client=DefaultAsyncHttpxClient(proxy=proxy_url),
        )

    return AsyncOpenAI(api_key=api_key)
