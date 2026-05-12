from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.pipeline import ParsedJD


@pytest.fixture
def client():
    return TestClient(create_app())


def _parsed() -> ParsedJD:
    return ParsedJD(
        role="Staff Engineer",
        company="Aperture Labs",
        experience_level="senior",
        location="Remote",
    )


def test_jd_preview_happy_path(client):
    with (
        patch(
            "app.api.jd_preview.scrape_jd",
            new=AsyncMock(return_value="JD body text"),
        ),
        patch(
            "app.api.jd_preview.ParseJDSkill.run",
            new=AsyncMock(return_value=_parsed()),
        ),
    ):
        r = client.post(
            "/api/v1/jd/preview",
            json={"url": "https://boards.greenhouse.io/x/jobs/1"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["company"] == "Aperture Labs"
    assert body["role"] == "Staff Engineer"
    assert body["location"] == "Remote"
    assert body["jd_text"] == "JD body text"


def test_jd_preview_fetch_failed(client):
    with patch(
        "app.api.jd_preview.scrape_jd",
        new=AsyncMock(side_effect=ValueError("Domain not in allowlist: evil.com")),
    ):
        r = client.post(
            "/api/v1/jd/preview", json={"url": "https://evil.com/job"}
        )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "JD_FETCH_FAILED"


def test_jd_preview_too_large(client):
    huge = "word " * 50_000
    with patch(
        "app.api.jd_preview.scrape_jd", new=AsyncMock(return_value=huge)
    ):
        r = client.post(
            "/api/v1/jd/preview",
            json={"url": "https://boards.greenhouse.io/x/jobs/1"},
        )
    assert r.status_code == 413
    assert r.json()["detail"]["code"] == "JD_TOO_LARGE"


def test_jd_preview_parse_failed(client):
    with (
        patch(
            "app.api.jd_preview.scrape_jd", new=AsyncMock(return_value="JD text")
        ),
        patch(
            "app.api.jd_preview.ParseJDSkill.run",
            new=AsyncMock(side_effect=RuntimeError("LLM down")),
        ),
    ):
        r = client.post(
            "/api/v1/jd/preview",
            json={"url": "https://boards.greenhouse.io/x/jobs/1"},
        )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "JD_PARSE_FAILED"
