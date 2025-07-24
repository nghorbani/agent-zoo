
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
from typing import List, Dict, Optional
import json

from pydantic import BaseModel, Field
from loguru import logger
import dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio
from agent_zoo.career_page_finder.get_company_url import web_search, get_company_url


dotenv.load_dotenv(override=True)

class CompanyUrlResponse(BaseModel):
    company_name: str = Field(description="Name of the company")
    city: str = Field(description="City where the company is located")
    country: str = Field(description="Country where the company is located")
    official_url: str = Field(description="The validated career page URL for the company")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0 for the validation")
    validation_notes: str = Field(description="Notes explaining why this URL was selected as the career page")
    


async def get_career_page(company_name: str, city: str, country: str, website:Optional[str]=None) -> Optional[str]:
    """
    Get the career page URL for a company based on its name, city, and country.

    Args:
        company_name (str): Name of the company.
        city (str): City where the company is located.
        country (str): Country where the company is located.
        website (Optional[str]): The company website URL. If not provided, will be searched for.

    Returns:
        Optional[str]: The validated career page URL, or None if no valid career page is found.
    """
    if not website:
        # If no website is provided, use the get_company_url function to find it
        website = get_company_url(company_name, city, country)
        if not website:
            raise ValueError(f"Could not find website for {company_name} in {city}, {country}")
        
    company_website_query = f"career page for company '{company_name}' in {city} {country} under {website}"
    possible_career_pages = web_search(company_website_query, max_num_return=10)
    
    
    if not possible_career_pages:
        logger.warning(f"No career page candidates found for {company_name}")
        return None
    
    logger.info(f"Found {len(possible_career_pages)} candidate career pages for {company_name}: {possible_career_pages}")
    
    # Create MCP server configuration for Playwright
    server_configs = {
        "playwright": {
            'name': 'Playwright Browser',
            'params': {
                "command": "npx", 
                "args": ["@playwright/mcp@latest"],
                "env": {
                    "headless": "true",  # Essential for WSL
                    # "DISPLAY": ":0"      # Optional display setting
                }
            },
            'client_session_timeout_seconds': 60
        },
    }
    
    # Create agent prompt with the list of URLs
    urls_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(possible_career_pages)])
    
    agent_prompt = f"""
You are a web validator agent. Your task is to find the official career or job listings page of a company from an ordered list of candidate URLs.

Company: {company_name}
Location: {city}, {country}

Candidate URLs to check:
{urls_list}

Instructions:
1. Use the Playwright browser tool to visit the first URL in the list.
2. Determine if it is a valid career page by checking for the following:
   - It displays actual job listings (not just HR information or general career info)
   - Jobs are listed directly on the page or easily accessible
   - The page is specifically for careers/jobs at this company
3. If the first URL is valid, return it immediately. Do not check further URLs.
4. If it is not valid, proceed to the next one and repeat.
5. Stop at the first valid match.

Return the validated career page information with confidence and reasoning.
"""

    # Use MCP server with the correct pattern
    async with MCPServerStdio(
        **server_configs["playwright"],
    ) as mcp_server_playwright:
        # Create the agent with the MCP server
        agent = Agent(
            name="career_page_validator",
            instructions=agent_prompt,
            model="gpt-4.1-mini",
            mcp_servers=[mcp_server_playwright],
            output_type=CompanyUrlResponse
        )
        
        # Use trace and await Runner.run as specified
        with trace("find career page"):
            result = await Runner.run(agent, f"Please validate the career pages for {company_name} from the provided list and return the best career page URL with validation details.")
            
            # The result should already be structured due to output_type=CompanyUrlResponse
            if hasattr(result, 'final_output') and isinstance(result.final_output, CompanyUrlResponse):
                structured = result.final_output
                logger.info(f"Validated career page for {company_name}: {structured.official_url}")
                return structured.official_url
            elif isinstance(result, CompanyUrlResponse):
                logger.info(f"Validated career page for {company_name}: {result.official_url}")
                return result.official_url
            else:
                # Fallback if structured response parsing failed
                logger.warning(f"Failed to get structured response for {company_name}. Returning None.")
    return None



def demo():
    import asyncio
    TEST_COMPANIES = [
    ("Cubert", "Germany", "Ulm", "https://cubert-hyperspectral.com/", "https://cubert-hyperspectral.com/en/career/"),
    ("Asys", "Germany", "Dornstadt", "https://www.asys-group.com/", "https://www.asys-group.com/de/karriere/jobboerse"),
    ("Max-Planck Institute for intelligent systems", "Germany", "Tuebingen", "https://is.mpg.de/", "https://is.mpg.de/career"),
    ("Transporeon", "Germany", "Ulm", "https://www.transporeon.com", "https://trimblecareers.emea.trimble.com/careers"),
    ]
    cmpany_id = -1
    company_name, country, city, expected_website, expected_career_page = TEST_COMPANIES[cmpany_id]
    async def main():
        result = await get_career_page(company_name, city, country, expected_website)
        print("Career page URL:", result)

    asyncio.run(main())


if __name__ == "__main__":
    demo()
