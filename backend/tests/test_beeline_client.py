import logging

import httpx
import pytest

from conftest import event_records
from src.integrations.beeline import BeelineApiError, BeelineClient, BeelineSettings
from src.integrations.beeline.models import BeelineAuthConfig


def build_settings() -> BeelineSettings:
    return BeelineSettings(
        base_url="https://cloudpbx.beeline.ru/apis/portal",
        auth=BeelineAuthConfig(token="test-token"),
    )


@pytest.mark.asyncio
async def test_list_records_uses_auth_header_and_parses_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/apis/portal/records"
        assert request.headers["X-MPBX-API-AUTH-TOKEN"] == "test-token"
        assert request.url.params.get("limit") == "100"
        assert request.url.params.get("includeDeleted") == "false"
        return httpx.Response(
            200,
            json=[
                {
                    "recordId": "rec_1",
                    "extTrackingId": "track_1",
                    "userId": "user_1",
                    "phoneNumber": "+79991234567",
                    "durationSeconds": 42,
                }
            ],
        )

    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        records = await client.list_records(params={"limit": 100, "includeDeleted": False})
    finally:
        await client.close()

    assert len(records) == 1
    assert records[0].record_id == "rec_1"
    assert records[0].ext_tracking_id == "track_1"
    assert records[0].duration_seconds == 42


@pytest.mark.asyncio
async def test_list_records_keeps_routine_request_logs_out_of_info(caplog) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "recordId": "rec_1",
                    "extTrackingId": "track_1",
                    "userId": "user_1",
                    "durationSeconds": 42,
                }
            ],
        )

    caplog.set_level(logging.INFO)
    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        await client.list_records()
    finally:
        await client.close()

    assert not event_records(caplog, "beeline.request.start")
    assert not event_records(caplog, "beeline.request.success")


@pytest.mark.asyncio
async def test_list_records_parses_real_beeline_payload_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": "431708782",
                    "externalId": "53d41f43-2363-4940-b2ff-b84f6ada2467",
                    "phone": "9185197091",
                    "direction": "OUTBOUND",
                    "date": 1770879152935,
                    "duration": 25246,
                    "abonent": {
                        "userId": "9610387977@ufa.vo.ims.mnc099.mcc250.3gppnetwork.org",
                        "phone": "9610387977",
                    },
                }
            ],
        )

    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        records = await client.list_records()
    finally:
        await client.close()

    assert len(records) == 1
    assert records[0].record_id == "431708782"
    assert records[0].ext_tracking_id == "53d41f43-2363-4940-b2ff-b84f6ada2467"
    assert records[0].user_id == "9610387977@ufa.vo.ims.mnc099.mcc250.3gppnetwork.org"
    assert records[0].phone_number == "9185197091"
    assert records[0].external_number == "9610387977"
    assert records[0].started_at is not None
    assert records[0].started_at.year == 2026
    assert records[0].duration_seconds == 25


@pytest.mark.asyncio
async def test_get_record_reference_supports_plain_text_responses() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/apis/portal/records/rec_1/reference"
        return httpx.Response(200, text="https://cdn.example.test/recording.wav", headers={"content-type": "text/plain"})

    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        reference = await client.get_record_reference("rec_1")
    finally:
        await client.close()

    assert reference.url == "https://cdn.example.test/recording.wav"


@pytest.mark.asyncio
async def test_download_record_returns_bytes() -> None:
    payload = b"fake-audio"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/apis/portal/v2/records/rec_1/download"
        return httpx.Response(200, content=payload, headers={"content-type": "audio/mpeg"})

    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        result = await client.download_record("rec_1")
    finally:
        await client.close()

    assert result == payload


@pytest.mark.asyncio
async def test_delete_record_handles_no_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/apis/portal/v2/records/rec_1"
        return httpx.Response(204)

    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        result = await client.delete_record("rec_1")
    finally:
        await client.close()

    assert result.ok is True


@pytest.mark.asyncio
async def test_client_disables_environment_proxy_inference(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = BeelineClient(settings=build_settings())
    try:
        assert captured["trust_env"] is False
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_error_exposes_status_code_and_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    client = BeelineClient(settings=build_settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(BeelineApiError) as exc_info:
            await client.get_record("rec_1")
    finally:
        await client.close()

    assert exc_info.value.status_code == 401
    assert exc_info.value.details == {"message": "Unauthorized"}
