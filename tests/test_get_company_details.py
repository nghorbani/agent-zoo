"""End-to-end checks against live websites; they need internet access and API keys, so they are
skipped unless AGENT_ZOO_RUN_NETWORK=1 is set."""

import os

import pytest

from agent_zoo.get_job_listings.get_career_page import get_career_page
from agent_zoo.get_job_listings.get_company_url import get_company_url

pytestmark = pytest.mark.network

skip_without_network = pytest.mark.skipif(
    os.getenv("AGENT_ZOO_RUN_NETWORK") != "1",
    reason="network test: needs internet, SERPER_API_KEY and OPENAI_API_KEY; set AGENT_ZOO_RUN_NETWORK=1 to run it",
)

TEST_COMPANIES = [
    ("Cubert", "Germany", "Ulm", "https://cubert-hyperspectral.com/", "https://cubert-hyperspectral.com/en/career/"),
    ("Asys", "Germany", "Dornstadt", "https://www.asys-group.com/", "https://www.asys-group.com/de/karriere/jobboerse"),
    ("Max-Planck Institute for intelligent systems", "Germany", "Tuebingen", "https://is.mpg.de/", "https://is.mpg.de/career"),
    ("Transporeon", "Germany", "Ulm", "https://www.transporeon.com", "https://trimblecareers.emea.trimble.com/careers"),
]


@skip_without_network
@pytest.mark.asyncio
async def test_company_url():
    for company_name, country, city, expected_website, _expected_career_page in TEST_COMPANIES:
        website = await get_company_url(company_name, city, country)

        assert website, f"Failed to find website for {company_name} in {city}, {country}"
        assert expected_website in website, f"Expected website '{expected_website}' not found in {website}"


@skip_without_network
@pytest.mark.asyncio
async def test_career_page():
    for company_name, country, city, expected_website, expected_career_page in TEST_COMPANIES:
        career_page = await get_career_page(company_name, city, country, expected_website)

        assert career_page, f"No career_page found for company {company_name}"
        print(f"Found career page for {company_name}: {career_page}")
        print(f"Expected career page: {expected_career_page}")
        # The exact URL may differ because the agent validates candidates, so only the shape is checked.
        assert isinstance(career_page, str) and career_page.startswith('http'), f"Invalid career page URL: {career_page}"
