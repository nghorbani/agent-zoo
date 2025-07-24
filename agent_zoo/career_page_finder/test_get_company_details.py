import pytest

from agent_zoo.career_page_finder.get_company_url import get_company_url
from agent_zoo.career_page_finder.get_career_page import get_career_page

TEST_COMPANIES = [
("Cubert", "Germany", "Ulm", "https://cubert-hyperspectral.com/", "https://cubert-hyperspectral.com/en/career/"),
("Asys", "Germany", "Dornstadt", "https://www.asys-group.com/", "https://www.asys-group.com/de/karriere/jobboerse"),
("Max-Planck Institute for intelligent systems", "Germany", "Tuebingen", "https://is.mpg.de/", "https://is.mpg.de/career"),
("Transporeon", "Germany", "Ulm", "https://www.transporeon.com", "https://trimblecareers.emea.trimble.com/careers"),
]



def test_company_url():
    for company in TEST_COMPANIES:
        company_name, country, city, expected_website, expected_career_page = company
        website = get_company_url(company_name, city, country)

        assert website, f"Failed to find website for {company_name} in {city}, {country}"
        assert expected_website in website, f"Expected website '{expected_website}' not found

def test_career_page():
    for company in TEST_COMPANIES:
        company_name, country, city, website, career_page = company
        results = get_career_page(company_name, city, country, website)
        
        assert results, f"No results found for career page of {company_name}"
        assert career_page in results[0], f"Expected career page '{career_page}' not found in result '{results[0]}' for {company_name}"