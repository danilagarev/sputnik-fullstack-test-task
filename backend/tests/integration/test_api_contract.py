"""Externally observable behaviour of the HTTP API.

The wire format — status codes, field names, ordering — is what the frontend
and any other client depend on, so that is what these assert on, never the
internal structure behind it.
"""


async def test_upload_returns_the_created_file(client, storage_dir):
    response = await client.post(
        "/files",
        data={"title": "Квартальный отчёт"},
        files={"file": ("report.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Квартальный отчёт"
    assert body["original_name"] == "report.txt"
    assert body["mime_type"] == "text/plain"
    assert body["size"] == 5
    assert body["processing_status"] == "uploaded"
    assert body["scan_status"] is None
    assert body["scan_details"] is None
    assert body["metadata_json"] is None
    assert body["requires_attention"] is False
    assert body["id"]
    assert body["created_at"] and body["updated_at"]


async def test_upload_never_exposes_the_storage_name(uploaded):
    """The name on disk is an implementation detail and must not leak."""
    assert "stored_name" not in uploaded


async def test_upload_writes_the_payload_to_storage(client, storage_dir):
    await client.post(
        "/files",
        data={"title": "Отчёт"},
        files={"file": ("report.txt", b"payload bytes", "text/plain")},
    )

    stored = list(storage_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].read_bytes() == b"payload bytes"
    assert stored[0].suffix == ".txt"


async def test_upload_schedules_processing(uploaded, enqueued):
    """Exactly one unit of background work, for this file."""
    assert len(enqueued) == 1
    _, arguments = enqueued[0]
    assert arguments[0] == uploaded["id"]


async def test_upload_rejects_an_empty_file(client):
    response = await client.post(
        "/files",
        data={"title": "Пустой"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File is empty"


async def test_upload_falls_back_to_octet_stream_for_unknown_types(client):
    response = await client.post(
        "/files",
        data={"title": "Без типа"},
        files={"file": ("payload.unknownext", b"data", None)},
    )

    assert response.status_code == 201
    assert response.json()["mime_type"] == "application/octet-stream"


async def test_list_files_is_newest_first(client):
    for title in ("первый", "второй", "третий"):
        await client.post(
            "/files",
            data={"title": title},
            files={"file": (f"{title}.txt", b"x", "text/plain")},
        )

    response = await client.get("/files")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["третий", "второй", "первый"]


async def test_list_files_is_empty_by_default(client):
    response = await client.get("/files")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_file_returns_the_same_representation(client, uploaded):
    response = await client.get(f"/files/{uploaded['id']}")

    assert response.status_code == 200
    assert response.json() == uploaded


async def test_get_file_404_for_unknown_id(client):
    response = await client.get("/files/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


async def test_patch_updates_only_the_title(client, uploaded):
    response = await client.patch(f"/files/{uploaded['id']}", json={"title": "Новое название"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Новое название"
    assert body["original_name"] == uploaded["original_name"]
    assert body["size"] == uploaded["size"]


async def test_patch_404_for_unknown_id(client):
    response = await client.patch(
        "/files/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )

    assert response.status_code == 404


async def test_patch_requires_a_title(client, uploaded):
    response = await client.patch(f"/files/{uploaded['id']}", json={})

    assert response.status_code == 422


async def test_download_returns_the_original_bytes(client, uploaded):
    response = await client.get(f"/files/{uploaded['id']}/download")

    assert response.status_code == 200
    assert response.content == b"line one\nline two\n"
    assert response.headers["content-type"].startswith("text/plain")
    assert "contract.txt" in response.headers["content-disposition"]


async def test_download_404_for_unknown_id(client):
    response = await client.get("/files/00000000-0000-0000-0000-000000000000/download")

    assert response.status_code == 404


async def test_download_404_when_the_payload_is_gone(client, uploaded, storage_dir):
    for path in storage_dir.iterdir():
        path.unlink()

    response = await client.get(f"/files/{uploaded['id']}/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Stored file not found"


async def test_delete_removes_the_row_and_the_payload(client, uploaded, storage_dir):
    response = await client.delete(f"/files/{uploaded['id']}")

    assert response.status_code == 204
    assert list(storage_dir.iterdir()) == []
    assert (await client.get(f"/files/{uploaded['id']}")).status_code == 404
    assert (await client.get("/files")).json() == []


async def test_delete_404_for_unknown_id(client):
    response = await client.delete("/files/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


async def test_list_alerts_is_empty_by_default(client):
    response = await client.get("/alerts")

    assert response.status_code == 200
    assert response.json() == []


async def test_a_page_is_bounded(client):
    """A list never returns the whole table, however much of it there is."""
    for index in range(4):
        await client.post(
            "/files",
            data={"title": f"файл {index}"},
            files={"file": (f"{index}.txt", b"x", "text/plain")},
        )

    response = await client.get("/files", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_an_oversized_limit_is_capped(client):
    response = await client.get("/files", params={"limit": 10_000})

    assert response.status_code == 200


async def test_a_whitespace_title_is_refused(client):
    """The browser trimmed its input; another client need not."""
    response = await client.post(
        "/files",
        data={"title": "   "},
        files={"file": ("report.txt", b"data", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Value must not be empty"


async def test_a_missing_title_is_refused_by_validation(client):
    response = await client.post(
        "/files",
        files={"file": ("report.txt", b"data", "text/plain")},
    )

    assert response.status_code == 422


async def test_a_blank_title_is_refused_on_rename(client, uploaded):
    response = await client.patch(f"/files/{uploaded['id']}", json={"title": "  "})

    assert response.status_code == 400


async def test_a_title_is_stored_trimmed(client):
    response = await client.post(
        "/files",
        data={"title": "  Договор  "},
        files={"file": ("report.txt", b"data", "text/plain")},
    )

    assert response.json()["title"] == "Договор"


async def test_an_overlong_name_is_a_client_error_not_a_crash(client):
    """Both columns are String(255); the database used to answer with a 500."""
    response = await client.post(
        "/files",
        data={"title": "x" * 300},
        files={"file": ("report.txt", b"data", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Value is too long"


async def test_a_dot_in_the_middle_of_a_name_is_not_an_extension(client, storage_dir):
    """A name is not a path: only a plausible suffix reaches the filesystem."""
    await client.post(
        "/files",
        data={"title": "Отчёт"},
        files={"file": ("Отчёт за 2026.09 итог", b"data", "text/plain")},
    )

    stored = list(storage_dir.iterdir())
    assert stored[0].suffix == ""


async def test_an_upload_survives_an_unavailable_broker(client, monkeypatch):
    """The bytes are stored and the row committed, so the upload succeeded."""
    from src.workers.queue import CeleryProcessingQueue

    def explode(*_args, **_kwargs):
        raise ConnectionError("broker is down")

    monkeypatch.setattr(CeleryProcessingQueue, "publish", explode)

    response = await client.post(
        "/files",
        data={"title": "Отчёт"},
        files={"file": ("report.txt", b"data", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["processing_status"] == "uploaded"


async def test_an_oversized_upload_is_refused_and_leaves_nothing_behind(
    client, storage_dir, monkeypatch
):
    """Nothing survives a refusal: no row, no bytes, no partial file."""
    from src.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 8)

    response = await client.post(
        "/files",
        data={"title": "Слишком большой"},
        files={"file": ("big.bin", b"x" * 64, "application/octet-stream")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File is too large"
    assert list(storage_dir.iterdir()) == []
    assert (await client.get("/files")).json() == []


async def test_an_oversized_upload_never_reaches_the_endpoint(client, monkeypatch):
    """The declared length is checked before the body is read.

    Without that check the multipart parser spools the whole payload to a
    temporary file before the handler runs, so the storage layer's own counter
    can only refuse it once the bytes are already on disk. Overriding the
    service with something that refuses to run is how "before" is asserted:
    the endpoint's dependencies are never resolved.
    """
    from src.api.deps import get_file_service
    from src.app import app
    from src.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 8)

    def unreachable() -> None:
        raise AssertionError("the endpoint must not run for an oversized body")

    app.dependency_overrides[get_file_service] = unreachable
    try:
        response = await client.post(
            "/files",
            data={"title": "Слишком большой"},
            files={"file": ("big.bin", b"x" * 64, "application/octet-stream")},
        )
    finally:
        app.dependency_overrides.pop(get_file_service, None)

    assert response.status_code == 413
    assert response.json()["detail"] == "File is too large"


async def test_a_request_within_the_limit_is_untouched(client, monkeypatch):
    """The guard reads the declared length and nothing else."""
    from src.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 1024)

    response = await client.post(
        "/files",
        data={"title": "Обычный"},
        files={"file": ("notes.txt", b"data", "text/plain")},
    )

    assert response.status_code == 201
