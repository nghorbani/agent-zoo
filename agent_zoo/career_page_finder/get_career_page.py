
"""
I am trying to implement an agentic soluton that given company name, country and city, finds the url pof the company and returns it. 
This module is designed to be used in a career page finder context, where it can be integrated
with other components to provide a comprehensive solution for job seekers looking for company career pages.
it will use openai agentic sdk for oimplemnting the agentic soluton
it will use serper and playwright for finding the urls of the companies
it will use requests for making http requests to the company urls

there is a single company_url_agent with serper tool and play write, 
first it will get some suggestions then using playwrite it will look for the suggested pages and validate them one by one.
it is assumed that company home page will be the top most one.

"""

import os
import requests
from typing import List, Dict

from pydantic import BaseModel
from loguru import logger
import dotenv
from agent_zoo.career_page_finder.get_company_url import web_search, get_company_url


dotenv.load_dotenv(override=True)

class CompanyUrlResponse(BaseModel):
    company_name: str
    city: str
    country: str
    official_url: str
    confidence: float
    validation_notes: str
    


def get_career_page(company_name: str, city: str, country: str, website:Optional[str]=None) -> CompanyUrlResponse:
    """
    Get the career page URL for a company based on its name, city, and country.

    Args:
        company_name (str): Name of the company.
        city (str): City where the company is located.
        country (str): Country where the company is located.

    Returns:
        CompanyUrlResponse: Response containing the career page URL and other details.
    """
    if not website:
        # If no website is provided, use the get_company_url function to find it
        website = get_company_url(company_name, city, country)
        if not website:
            raise ValueError(f"Could not find website for {company_name} in {city}, {country}")
        
    company_website_query = f"career page for company '{company_name}' in {city} {country} under {url}"
    possible_career_pages = web_search(company_website_query, max_num_return=10)
    
    mcp_servers = {
        "playwright": {
            'name': 'Playwright Browser',
            'params': {
                "command": "npx", 
                "args": ["@playwright/mcp@latest"],
                "env": {
                    "headless": "true",  # Essential for WSL
                    "DISPLAY": ":0"      # Optional display setting
                }
            },
            'client_session_timeout_seconds': 60
        },
        
        }
    
    agent_prompt = """
        You are a web validator agent. Your task is to find the official career or job listings page of a company from an ordered list of candidate URLs.

        Instructions:
        1. Use the Playwright browser tool to visit the first URL in the list.
        2. Determine if it is a valid career page by checking for the following:
        - It displays actual job listings (not just HR information).
        - Jobs are listed directly.
        3. If the first URL is valid, return it immediately. Do not check further URLs.
        4. If it is not valid, proceed to the next one and repeat.
        5. Stop at the first valid match.

        Output your result as:
        {
        "valid_url": "<confirmed_career_page_url>",
        "reason": "<short justification why this page was accepted>"
        }

        Only return one result. Do not check all URLs if a valid one is found early.
        """
        
    




if __name__ == "__main__":
    TEST_COMPANIES = [
    ("Cubert", "Germany", "Ulm", "https://cubert-hyperspectral.com/", "https://cubert-hyperspectral.com/en/career/"),
    ("Asys", "Germany", "Dornstadt", "https://www.asys-group.com/", "https://www.asys-group.com/de/karriere/jobboerse"),
    ("Max-Planck Institute for intelligent systems", "Germany", "Tuebingen", "https://is.mpg.de/", "https://is.mpg.de/career"),
    ("Transporeon", "Germany", "Ulm", "https://www.transporeon.com", "https://trimblecareers.emea.trimble.com/careers"),
    ]
    cmpany_id = -2
    company_name, country, city, expected_website, expected_career_page = TEST_COMPANIES[cmpany_id]
    get_career_page(company_name, city, country, expected_website)


