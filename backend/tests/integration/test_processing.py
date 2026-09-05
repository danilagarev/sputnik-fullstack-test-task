"""Business rules of scanning, metadata extraction and alerting.

Pinned through the public API rather than through the task functions, so the
assertions survive a change to the shape of the pipeline: work is published by
uploading a file and then draining the queue.
"""

import pytest

SUSPICIOUS_EXTENSIONS = [".exe", ".bat", ".cmd", ".sh", ".js"]


async def upload(client, filename, content=b"data", content_type="text/plain"):
    response = await client.post(
        "/files",
        data={"title": filename},
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize("extension", SUSPICIOUS_EXTENSIONS)
async def test_suspicious_extensions_are_flagged(client, run_pipeline, extension):
    file_id = await upload(client, f"payload{extension}")
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["scan_status"] == "suspicious"
    assert body["scan_details"] == f"suspicious extension {extension}"
    assert body["requires_attention"] is True


async def test_a_plain_file_is_clean(client, run_pipeline):
    file_id = await upload(client, "notes.txt")
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["scan_status"] == "clean"
    assert body["scan_details"] == "no threats found"
    assert body["requires_attention"] is False


async def test_files_over_ten_megabytes_are_flagged(client, run_pipeline):
    file_id = await upload(client, "big.txt", content=b"x" * (10 * 1024 * 1024 + 1))
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["scan_status"] == "suspicious"
    assert body["scan_details"] == "file is larger than 10 MB"


async def test_ten_megabytes_exactly_is_not_flagged(client, run_pipeline):
    file_id = await upload(client, "exact.txt", content=b"x" * (10 * 1024 * 1024))
    await run_pipeline()

    assert (await client.get(f"/files/{file_id}")).json()["scan_status"] == "clean"


async def test_pdf_extension_with_a_foreign_mime_type_is_flagged(client, run_pipeline):
    file_id = await upload(client, "report.pdf", content=b"%PDF-1.4", content_type="text/plain")
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["scan_status"] == "suspicious"
    assert body["scan_details"] == "pdf extension does not match mime type"


async def test_pdf_with_an_octet_stream_mime_type_is_accepted(client, run_pipeline):
    file_id = await upload(
        client, "report.pdf", content=b"%PDF-1.4", content_type="application/octet-stream"
    )
    await run_pipeline()

    assert (await client.get(f"/files/{file_id}")).json()["scan_status"] == "clean"


async def test_several_reasons_are_joined(client, run_pipeline):
    file_id = await upload(client, "big.exe", content=b"x" * (10 * 1024 * 1024 + 1))
    await run_pipeline()

    details = (await client.get(f"/files/{file_id}")).json()["scan_details"]
    assert details == "suspicious extension .exe, file is larger than 10 MB"


async def test_text_metadata_counts_lines_and_characters(client, run_pipeline):
    file_id = await upload(client, "notes.txt", content=b"first\nsecond\nthird\n")
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["processing_status"] == "processed"
    assert body["metadata_json"] == {
        "extension": ".txt",
        "size_bytes": 19,
        "mime_type": "text/plain",
        "line_count": 3,
        "char_count": 19,
    }


async def test_metadata_for_other_types_has_no_counters(client, run_pipeline):
    file_id = await upload(client, "image.png", content=b"\x89PNG\r\n", content_type="image/png")
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["metadata_json"] == {
        "extension": ".png",
        "size_bytes": 6,
        "mime_type": "image/png",
    }


async def test_a_clean_file_produces_an_info_alert(client, run_pipeline):
    file_id = await upload(client, "notes.txt")
    await run_pipeline()

    alerts = (await client.get("/alerts")).json()
    assert len(alerts) == 1
    assert alerts[0]["file_id"] == file_id
    assert alerts[0]["level"] == "info"
    assert alerts[0]["message"] == "File processed successfully"


async def test_a_suspicious_file_produces_a_warning_alert(client, run_pipeline):
    await upload(client, "payload.exe")
    await run_pipeline()

    alerts = (await client.get("/alerts")).json()
    assert len(alerts) == 1
    assert alerts[0]["level"] == "warning"
    assert alerts[0]["message"] == "File requires attention: suspicious extension .exe"


async def test_a_missing_payload_fails_processing_and_alerts(client, run_pipeline, storage_dir):
    file_id = await upload(client, "notes.txt")
    for path in storage_dir.iterdir():
        path.unlink()

    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["processing_status"] == "failed"
    assert body["scan_details"] == "stored file not found during metadata extraction"

    alerts = (await client.get("/alerts")).json()
    assert len(alerts) == 1
    assert alerts[0]["level"] == "critical"
    assert alerts[0]["message"] == "File processing failed"


async def test_processing_a_deleted_file_is_a_no_op(client, run_pipeline):
    file_id = await upload(client, "notes.txt")
    await client.delete(f"/files/{file_id}")

    await run_pipeline()

    assert (await client.get("/alerts")).json() == []


async def test_alerts_are_newest_first(client, run_pipeline):
    await upload(client, "one.txt")
    await run_pipeline()
    await upload(client, "two.exe")
    await run_pipeline()

    alerts = (await client.get("/alerts")).json()
    assert [alert["level"] for alert in alerts] == ["warning", "info"]


async def test_pdf_pages_are_counted(client, run_pipeline):
    """The old pattern searched for "/Type /Page" with a space, which no
    producer emits, so every document was reported as a single page."""
    document = b"%PDF-1.4\n" + b"/Type /Pages\n" + b"/Type/Page\n" * 3
    file_id = await upload(client, "doc.pdf", document, "application/pdf")
    await run_pipeline()

    body = (await client.get(f"/files/{file_id}")).json()
    assert body["metadata_json"]["approx_page_count"] == 3


async def test_a_processed_file_can_be_deleted(client, run_pipeline, storage_dir):
    """Every processed file owns an alert, and the key used to have no cascade."""
    file_id = await upload(client, "notes.txt")
    await run_pipeline()

    response = await client.delete(f"/files/{file_id}")

    assert response.status_code == 204
    assert (await client.get("/alerts")).json() == []
    assert list(storage_dir.iterdir()) == []


async def test_a_redelivered_task_does_not_duplicate_the_alert(client, run_pipeline, enqueued):
    """`task_acks_late` may deliver a completed task again."""
    file_id = await upload(client, "notes.txt")
    await run_pipeline()

    from src.workers import tasks as tasks_module

    await tasks_module._process_file(file_id)

    alerts = (await client.get("/alerts")).json()
    assert len(alerts) == 1


async def test_no_file_is_left_in_a_non_terminal_state(client, run_pipeline, storage_dir):
    """Whatever happens, processing ends in `processed` or `failed`."""
    good = await upload(client, "notes.txt")
    broken = await upload(client, "gone.txt")
    for path in storage_dir.iterdir():
        if path.stem == broken:
            path.unlink()

    await run_pipeline()

    listing = (await client.get("/files")).json()
    statuses = {item["id"]: item["processing_status"] for item in listing}
    assert statuses[good] == "processed"
    assert statuses[broken] == "failed"
