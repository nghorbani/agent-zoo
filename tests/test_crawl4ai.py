"""Smoke test for crawl4ai against a live career page; needs internet access and a Playwright browser,
so it is skipped unless AGENT_ZOO_RUN_NETWORK=1 is set."""

import os

import pytest

pytestmark = pytest.mark.network


@pytest.mark.skipif(
    os.getenv("AGENT_ZOO_RUN_NETWORK") != "1",
    reason="network test: needs internet and a Playwright browser (playwright install); set AGENT_ZOO_RUN_NETWORK=1 to run it",
)
@pytest.mark.asyncio
async def test_crawl_career_page():
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://www.asys-group.com/en/career/job-board")

    assert result.markdown
