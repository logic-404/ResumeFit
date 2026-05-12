import pytest

from app.tools import registry


@pytest.mark.asyncio
async def test_entity_diff_clean():
    src = "I worked at CosX from 2026 on Python pipelines."
    out = "At CosX in 2026 I built Python pipelines."
    res = await registry.dispatch("entity_diff", {"source": src, "output": out})
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_entity_diff_flags_fabrication():
    src = "I worked at CosX from 2026 on Python pipelines."
    out = "At Google in 2024 I led teams in Rust."
    res = await registry.dispatch("entity_diff", {"source": src, "output": out})
    assert res["ok"] is False
    assert "Google" in res["fabricated_entities"]
    assert "2024" in res["fabricated_dates"]


@pytest.mark.asyncio
async def test_skill_taxonomy_alias_resolves():
    res = await registry.dispatch("skill_taxonomy_lookup", {"skill": "K8s"})
    assert res["ok"] and res["found"]
    assert res["canonical"] == "Kubernetes"


@pytest.mark.asyncio
async def test_skill_taxonomy_unknown():
    res = await registry.dispatch(
        "skill_taxonomy_lookup", {"skill": "ZZZ_not_real_skill"}
    )
    assert res["found"] is False


@pytest.mark.asyncio
async def test_fetch_jd_blocks_loopback():
    res = await registry.dispatch(
        "fetch_job_description", {"url": "http://localhost:8000/admin"}
    )
    assert res["ok"] is False


@pytest.mark.asyncio
async def test_fetch_jd_blocks_private_ip():
    res = await registry.dispatch(
        "fetch_job_description", {"url": "http://169.254.169.254/latest/meta-data/"}
    )
    assert res["ok"] is False


@pytest.mark.asyncio
async def test_fetch_jd_blocks_non_http_scheme():
    res = await registry.dispatch(
        "fetch_job_description", {"url": "file:///etc/passwd"}
    )
    assert res["ok"] is False


@pytest.mark.asyncio
async def test_web_search_disabled_by_default():
    res = await registry.dispatch("web_search", {"query": "atlassian"})
    assert res["ok"] is False


def test_registry_openai_specs():
    specs = registry.openai_specs(["entity_diff", "skill_taxonomy_lookup"])
    assert all(s["type"] == "function" for s in specs)
    assert {s["function"]["name"] for s in specs} == {
        "entity_diff",
        "skill_taxonomy_lookup",
    }
