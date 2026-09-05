"""Unit tests for the scan rules and the streaming probes.

No database, no disk, no event loop — this is the practical argument for
pulling the logic out of the module that also owned the engine and the HTTP
layer. The probes are tested across deliberately awkward chunk boundaries,
because streaming is what makes the single-pass optimization possible and a
boundary bug there would be invisible in an end-to-end test.
"""

import random
import tracemalloc

import pytest

from src.domain.enums import ScanStatus
from src.services.scanning import (
    PdfPageProbe,
    TextProbe,
    describe,
    probes_for,
    scan,
)


def feed_in_chunks(probe, payload: bytes, size: int):
    for start in range(0, len(payload), size):
        probe.feed(payload[start : start + size])
    return probe.result()


class TestScanRules:
    def test_a_plain_file_is_clean(self):
        verdict = scan(original_name="notes.txt", size=10, mime_type="text/plain")

        assert verdict.status is ScanStatus.CLEAN
        assert verdict.details == "no threats found"
        assert verdict.requires_attention is False

    @pytest.mark.parametrize("extension", [".exe", ".bat", ".cmd", ".sh", ".js"])
    def test_suspicious_extensions(self, extension):
        verdict = scan(original_name=f"x{extension}", size=1, mime_type="text/plain")

        assert verdict.status is ScanStatus.SUSPICIOUS
        assert verdict.details == f"suspicious extension {extension}"

    def test_the_extension_check_is_case_insensitive(self):
        verdict = scan(original_name="PAYLOAD.EXE", size=1, mime_type="text/plain")

        assert verdict.requires_attention is True

    @pytest.mark.parametrize(
        ("size", "flagged"),
        [(10 * 1024 * 1024, False), (10 * 1024 * 1024 + 1, True)],
    )
    def test_the_size_boundary(self, size, flagged):
        verdict = scan(original_name="a.txt", size=size, mime_type="text/plain")

        assert verdict.requires_attention is flagged

    @pytest.mark.parametrize(
        ("mime_type", "flagged"),
        [
            ("application/pdf", False),
            ("application/octet-stream", False),
            ("text/plain", True),
        ],
    )
    def test_pdf_mime_agreement(self, mime_type, flagged):
        verdict = scan(original_name="r.pdf", size=1, mime_type=mime_type)

        assert verdict.requires_attention is flagged

    def test_reasons_are_joined_in_a_stable_order(self):
        verdict = scan(original_name="big.exe", size=10 * 1024 * 1024 + 1, mime_type="text/plain")

        assert verdict.details == "suspicious extension .exe, file is larger than 10 MB"


class TestTextProbe:
    @pytest.mark.parametrize("chunk_size", [1, 3, 7, 1024])
    def test_counts_survive_any_chunking(self, chunk_size):
        payload = b"first\nsecond\nthird\n"

        assert feed_in_chunks(TextProbe(), payload, chunk_size) == {
            "line_count": 3,
            "char_count": 19,
        }

    @pytest.mark.parametrize("chunk_size", [1, 2, 5])
    def test_a_final_line_without_a_newline_still_counts(self, chunk_size):
        assert feed_in_chunks(TextProbe(), b"a\nb", chunk_size)["line_count"] == 2

    @pytest.mark.parametrize("chunk_size", [1, 2, 3, 8])
    def test_crlf_split_across_a_boundary_is_one_line_break(self, chunk_size):
        """The riskiest case: "\\r" ending a chunk and "\\n" opening the next."""
        assert feed_in_chunks(TextProbe(), b"a\r\nb\r\nc", chunk_size)["line_count"] == 3

    @pytest.mark.parametrize("chunk_size", [1, 2, 3])
    def test_multibyte_characters_split_across_a_boundary(self, chunk_size):
        payload = "привет\n".encode()

        assert feed_in_chunks(TextProbe(), payload, chunk_size) == {
            "line_count": 1,
            "char_count": 7,
        }

    def test_a_stream_without_line_breaks_is_not_retained(self):
        """The probe must hold a bounded amount of state, not the document.

        Text with no line terminator anywhere — minified JSON, a single-line
        CSV, a mislabelled binary — is the case where a naive carry-over buffer
        silently accumulates the whole stream and reintroduces exactly the
        memory profile the streaming rewrite exists to remove.
        """
        probe = TextProbe()
        chunk = b"x" * (256 * 1024)

        tracemalloc.start()
        try:
            baseline = tracemalloc.get_traced_memory()[0]
            for _ in range(32):  # 8 MiB
                probe.feed(chunk)
            retained = tracemalloc.get_traced_memory()[0] - baseline
        finally:
            tracemalloc.stop()

        assert probe.result() == {"line_count": 1, "char_count": 8 * 1024 * 1024}
        assert retained < 1024 * 1024, f"probe retained {retained / 1024 / 1024:.1f} MiB"

    @pytest.mark.parametrize("seed", range(25))
    def test_the_count_always_matches_str_splitlines(self, seed):
        """Randomised cross-check against the behaviour being reimplemented.

        The probe counts boundaries incrementally rather than calling
        splitlines() on the whole document, so the two have to be shown to
        agree — including on the separators nobody thinks about and on chunk
        sizes that cut every one of them in half.
        """
        rng = random.Random(seed)
        alphabet = "ab\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 200)))
        payload = text.encode()
        chunk_size = rng.randint(1, 8)

        probe = TextProbe()
        for start in range(0, len(payload), chunk_size):
            probe.feed(payload[start : start + chunk_size])

        assert probe.result() == {
            "line_count": len(text.splitlines()),
            "char_count": len(text),
        }, f"disagreed on {text!r} at chunk size {chunk_size}"

    def test_an_empty_stream(self):
        assert TextProbe().result() == {"line_count": 0, "char_count": 0}

    def test_undecodable_bytes_are_ignored_not_fatal(self):
        probe = TextProbe()
        probe.feed(b"ok\n\xff\xfe\n")

        assert probe.result()["line_count"] == 2


class TestPdfPageProbe:
    PDF = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R>>endobj\n"
        b"4 0 obj<</Type /Page/Parent 2 0 R>>endobj\n"
        b"5 0 obj<</Type/Page/Parent 2 0 R>>endobj\n"
        b"%%EOF\n"
    )

    @pytest.mark.parametrize("chunk_size", [1, 5, 17, 64, 4096])
    def test_pages_are_counted_across_any_chunking(self, chunk_size):
        """Three pages, one of them written with the space the old code wanted."""
        assert feed_in_chunks(PdfPageProbe(), self.PDF, chunk_size) == {"approx_page_count": 3}

    def test_the_page_tree_is_not_a_page(self):
        probe = PdfPageProbe()
        probe.feed(b"<</Type/Pages/Kids[]>>")

        assert probe.result()["approx_page_count"] == 1

    def test_a_document_with_no_marker_reports_one(self):
        probe = PdfPageProbe()
        probe.feed(b"%PDF-1.4 nothing here")

        assert probe.result()["approx_page_count"] == 1


class TestProbeSelection:
    @pytest.mark.parametrize(
        ("mime_type", "expected"),
        [
            ("text/plain", [TextProbe]),
            ("text/csv", [TextProbe]),
            ("application/pdf", [PdfPageProbe]),
            ("image/png", []),
        ],
    )
    def test_probes_match_the_content_type(self, mime_type, expected):
        assert [type(probe) for probe in probes_for(mime_type)] == expected


def test_describe_merges_row_fields_with_measured_metrics():
    assert describe(
        original_name="Report.TXT",
        size=19,
        mime_type="text/plain",
        metrics={"line_count": 3, "char_count": 19},
    ) == {
        "extension": ".txt",
        "size_bytes": 19,
        "mime_type": "text/plain",
        "line_count": 3,
        "char_count": 19,
    }
