from typing import List, Optional
import hashlib
from pydantic import BaseModel, Field
from loguru import logger
import dotenv
from agents import Agent, Runner, trace, function_tool
from agents.mcp import MCPServerStdio

dotenv.load_dotenv(override=True)

class Job(BaseModel):
    """
    Represents a job listing with relevant details.
    """
    title: str = Field(description="The title of the job position")
    location: str = Field(description="The location of the job")
    url: str = Field(description="The URL to the job listing")
    description: str = Field(description="A brief description of the job responsibilities and requirements")
    date_posted: str = Field(description="The date when the job was posted")
    skills_required: List[str] = Field(description="A list of skills required for the job")
    employment_type: str = Field(description="Type of employment (e.g., full-time, part-time, contract)")
    
    
class JobListings(BaseModel):
    """
    Represents a collection of job listings.
    """
    jobs: List[Job] = Field(description="A list of job listings")
    
class Link(BaseModel):
    """
    Represents a link to a job listing.
    """
    title: str = Field(description="The title of the job listing")
    url: str = Field(description="The URL to the job listing")
    
class PageExtractionResult(BaseModel):
    """
    Represents a list of links to job listings.
    """
    links: List[Link] = Field(description="A list of job listing links")
    next_page_url: Optional[str] = Field(default=None, description="URL of the next page of job listings, if available")


@function_tool
def hash_job_link(title: str, url: str) -> str:
    """
    Normalizes the title, combines it with the URL, and returns a SHA-256 hash.
    
    Args:
        title (str): The job title.
        url (str): The URL to the job listing.
        
    Returns:
        str: A hexadecimal SHA-256 hash representing the normalized title + URL.
    """
    normalized_title = " ".join(title.strip().lower().split())
    combined = f"{normalized_title}|{url.strip()}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


async def get_job_listings(career_page_url: str) -> PageExtractionResult:
    """
    Extract job listing links from a company's career page.
    
    Args:
        career_page_url (str): The URL of the company's career page
        
    Returns:
        LinkList: A list of job listing links found on the career page
    """

    
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
        "memory": {
            "name": "Memory",
            "params": {"command": "npx", "args": ["-y", "mcp-memory-libsql"], "env": {"LIBSQL_URL": "file:.job_listings.db"}},
            "client_session_timeout_seconds": 30
        },
    }
    
    # Create agent prompt with the list of URLs
    
    agent_prompt = """
You are an intelligent browser automation agent tasked with extracting job listings from a company's career page using the web_browser tool.

## INPUT
You are given a `career_page_url`.

## GOAL
Your goal is to return a structured LinkList object that contains all job listing links (`title`, `url`) found on the **current** page of the given career page. 
Additionally, return the `next_page_url` if there is a link to the next page of job listings.

## INSTRUCTIONS

1. Visit the provided `career_page_url` using the `web_browser` tool.
2. Extract all anchor links (`<a>`) on the current page. For each link:
   - Retain the link only if it appears to be a real job posting.
     - Job links often contain job titles like "Software Engineer", "Data Scientist", "Sales Manager", etc.
     - Avoid links such as "Contact", "About us", "Imprint", "Privacy Policy", or navigation elements.
     - Avoid links that point to the same page or unrelated external sites.
   - Use heuristics (e.g., presence of job-related words in the anchor text or URL).
   - Do NOT visit the job listing URL itself — just collect the URL and the anchor text as the title.
3. Look for a pagination element on the page (e.g., links labeled "Next", "Weiter", ">>", forward arrow or numbered pages).
   - If a "next page" exists, extract its full URL and return it as `next_page_url`.
   - Use the `web_browser` tool to confirm that the next page URL is valid and leads to a new page of job listings.
   - If the next page URL is relative, convert it to an absolute URL based on the `career_page_url`.
   - Exhaustively check for pagination links, including those that might be hidden or dynamically loaded.
   - If no such link exists, return `next_page_url` as null.

## OUTPUT
Return your final answer as a structured `LinkList` object with the following format:

```json
{
  "links": [
    {"title": "Job Title 1", "url": "https://example.com/job1"},
    {"title": "Job Title 2", "url": "https://example.com/job2"}
  ],
  "next_page_url": "https://example.com/careers?page=2"
}
```


If no next page is found, return next_page_url as null.

Return only the job links found on the current page.

Do not include any links that are already stored in memory (check hash of title+url).

Only use the web_browser tool to navigate and extract content.
"""

    max_pages = 5  # Limit the number of pages to visit to avoid infinite loops or excessive resource usage
    try:
        # Use MCP server with the correct pattern
        async with MCPServerStdio(**server_configs["playwright"]) as mcp_server_playwright:
            current_url = career_page_url
            pages_visited = 0
            # Create the agent with the MCP server
            agent = Agent(
                name="single_page_extractor",
                model="gpt-4.1-mini",
                instructions=agent_prompt,
                mcp_servers=[mcp_server_playwright],
                # tools=[hash_job_link],
                output_type=PageExtractionResult, 
                
            )
            
            all_links = []
            
            # Use trace and await Runner.run as specified
            with trace("extract job listings"):
                while current_url and pages_visited < max_pages:
                    result = await Runner.run(agent, f"Extract job links from {current_url}", max_turns=30)
                    if not isinstance(result.final_output, PageExtractionResult):
                        logger.warning("Invalid output from agent, breaking extraction.")
                        return PageExtractionResult(links=[])
                    logger.info(f"Extracted {len(result.final_output.links)} links from {current_url}")
                    logger.info(f"Next page URL: {result.final_output.next_page_url}")
                    all_links.extend(result.final_output.links)
                    current_url = result.final_output.next_page_url
                    pages_visited += 1
            
            # Return the collected links
            return PageExtractionResult(links=all_links)

    except Exception as e:
        logger.error(f"Error extracting job listings from {career_page_url}: {e}")
        return PageExtractionResult(links=[])

def demo():
    import asyncio
    TEST_COMPANIES = [
    ("Cubert", "Germany", "Ulm", "https://cubert-hyperspectral.com/", "https://cubert-hyperspectral.com/en/career/"),
    ("Asys", "Germany", "Dornstadt", "https://www.asys-group.com/", "https://www.asys-group.com/de/karriere/jobboerse"),
    ("Max-Planck Institute for intelligent systems", "Germany", "Tuebingen", "https://is.mpg.de/", "https://is.mpg.de/career"),
    ("Transporeon", "Germany", "Ulm", "https://www.transporeon.com", "https://trimblecareers.emea.trimble.com/careers"),
    ]
    cmpany_id = 1
    company_name, country, city, expected_website, expected_career_page = TEST_COMPANIES[cmpany_id]
    async def main():
        result = await get_job_listings(expected_career_page)
        if len(result.links) == 0:
            print("No job listings found.")
        else:
            print(f"Found {len(result.links)} job listings:")
            # for link in result.links:
            #     print(f"Job Title: {link.title}, URL: {link.url}")

    asyncio.run(main())


if __name__ == "__main__":
    demo()
