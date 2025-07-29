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

class PaginationInfo(BaseModel):
    """
    Represents pagination information from a page.
    """
    current_page: int = Field(description="Current page number")
    total_pages: int = Field(description="Total number of pages")
    next_page_url: Optional[str] = Field(default=None, description="URL of the next page, if available")
    has_next_page: bool = Field(description="Whether there is a next page available")
    
class PageExtractionResult(BaseModel):
    """
    Represents a list of links to job listings.
    """
    links: List[Link] = Field(description="A list of job listing links")
    pagination_info: PaginationInfo = Field(description="Pagination information for the current page")


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


def create_pagination_agent(mcp_server_playwright) -> Agent:
    """
    Create a pagination detection agent that can be used as a tool.
    
    Args:
        mcp_server_playwright: The Playwright MCP server instance
        
    Returns:
        Agent: Pagination detection agent
    """
    
    pagination_prompt = """
You are a pagination detection specialist. Your sole task is to analyze the current web page for pagination information.

## GOAL
Extract pagination information from the currently loaded page and return it as a structured PaginationInfo object.

## CONTEXT
You may receive context about previous pagination information to help with analysis:
- Previous total pages discovered
- Expected current page number
- Expected next page number

Use this context to validate and improve your analysis, but always prioritize what you observe on the current page.

## INSTRUCTIONS

1. Analyze the current page for pagination indicators:
   - Page numbers (1, 2, 3, 4, etc.)
   - Page indicators like "1 / 4", "Page 1 of 4", "1-10 of 40", etc.
   - Navigation arrows (left/right arrows, previous/next buttons)
   - Text like "Next", "Previous", "Weiter", "Zurück", ">", ">>", etc.

2. Determine:
   - Current page number (usually highlighted or indicated)
   - Total number of pages (from indicators or by counting page numbers)
   - Whether there is a next page available
   - The URL of the next page (if available)

3. Look for common pagination patterns:
   - Images with src containing "arrow", "next", "prev", "right", "left"
   - Clickable elements (`<a>`, `<button>`, `<div>`) around pagination areas
   - Elements with classes like "pagination", "nav", "next", "prev", "arrow"
   - JavaScript-based pagination with onclick handlers or data attributes

4. **CRITICAL**: If you find pagination indicators showing multiple pages (e.g., "1 / 4"):
   - The current page should match the first number
   - The total pages should match the second number
   - If current page < total pages, there MUST be a next page
   - Look for the specific next page number (current + 1) in clickable elements
   - If you can't find a direct link, construct the URL using the pattern from the current URL

5. URL Construction:
   - If current URL has no page parameter and this is page 1, next page is usually "?page=2"
   - If current URL has "?page=N", next page is "?page=N+1"
   - Always return the full absolute URL
   - **CRITICAL**: If you detect pagination (e.g., "1 / 4") but cannot find a clickable next page element, you MUST construct the next page URL:
     - For page 1 with no page parameter: add "?page=2" to the current URL
     - For page N: replace or add "?page=N+1"
     - This is mandatory when has_next_page is true

## OUTPUT
Return a PaginationInfo object with:
- current_page: The current page number (default to 1 if unclear)
- total_pages: Total number of pages (default to 1 if unclear)
- next_page_url: Full URL to the next page (null if no next page)
- has_next_page: Boolean indicating if there's a next page

**IMPORTANT**: If you see indicators like "1 / 4" or "2 / 4", you MUST extract both numbers correctly and ensure has_next_page is true when current_page < total_pages.

Note: The page is already loaded by the main agent, so you can directly analyze the current page content.
"""

    return Agent(
        name="pagination_detector",
        model="gpt-4.1-mini",
        instructions=pagination_prompt,
        mcp_servers=[mcp_server_playwright],
        output_type=PaginationInfo,
    )


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
    
    # Simplified job extraction prompt
    job_extraction_prompt = """
You are a job listing extraction specialist. Your task is to extract job listings from a career page and use the pagination detection tool to find pagination information.

## GOAL
Extract all job listing links from the current page and use the pagination_detector tool to get complete pagination information.

## INSTRUCTIONS

1. Visit the provided `career_page_url` using the web_browser tool.
2. Extract all anchor links (`<a>`) on the current page. For each link:
   - Retain the link only if it appears to be a real job posting.
   - Job links often contain job titles like "Software Engineer", "Data Scientist", "Sales Manager", etc.
   - Avoid links such as "Contact", "About us", "Imprint", "Privacy Policy", or navigation elements.
   - Avoid links that point to the same page or unrelated external sites.
   - Use heuristics (e.g., presence of job-related words in the anchor text or URL).
   - Do NOT visit the job listing URL itself — just collect the URL and the anchor text as the title.

3. After extracting job links, use the pagination_detector tool to analyze the current page for pagination information.
   - The tool will return complete pagination details including current page, total pages, and next page URL.

## OUTPUT
Return a PageExtractionResult object with:
- links: Array of job listing links found on the current page
- pagination_info: The complete PaginationInfo object from the pagination_detector tool

Focus on extracting job links and let the pagination tool handle pagination detection.
"""

    max_pages = 5  # Limit the number of pages to visit to avoid infinite loops or excessive resource usage
    try:
        # Use MCP server with the correct pattern
        async with MCPServerStdio(**server_configs["playwright"]) as mcp_server_playwright:
            current_url = career_page_url
            pages_visited = 0
            
            # Create pagination agent and convert to tool
            pagination_agent = create_pagination_agent(mcp_server_playwright)
            pagination_tool = pagination_agent.as_tool(
                tool_name="pagination_detector",
                tool_description="Analyze the current page for pagination information and return details about current page, total pages, and next page URL"
            )
            
            # Create the main job extraction agent with pagination tool
            agent = Agent(
                name="job_extractor",
                model="gpt-4.1-mini",
                instructions=job_extraction_prompt,
                mcp_servers=[mcp_server_playwright],
                tools=[pagination_tool],
                output_type=PageExtractionResult, 
            )
            
            all_links = []
            last_pagination_info = None
            
            # Use trace and await Runner.run as specified
            with trace("extract job listings"):
                while current_url and pages_visited < max_pages:
                    result = await Runner.run(agent, f"Extract job links from {current_url}", max_turns=30)
                    if not isinstance(result.final_output, PageExtractionResult):
                        logger.warning("Invalid output from agent, breaking extraction.")
                        break
                    
                    pagination_info = result.final_output.pagination_info
                    logger.info(f"Page {pagination_info.current_page}/{pagination_info.total_pages}: Extracted {len(result.final_output.links)} links from {current_url}")
                    logger.info(f"Has next page: {pagination_info.has_next_page}, Next page URL: {pagination_info.next_page_url}")
                    
                    all_links.extend(result.final_output.links)
                    last_pagination_info = pagination_info
                    
                    # Continue to next page if available
                    if pagination_info.has_next_page and pagination_info.next_page_url:
                        current_url = pagination_info.next_page_url
                        pages_visited += 1
                    else:
                        logger.info("No more pages available, stopping extraction.")
                        break
            
            # Return the collected links with final pagination info
            final_pagination_info = last_pagination_info or PaginationInfo(
                current_page=1, total_pages=1, next_page_url=None, has_next_page=False
            )
            return PageExtractionResult(links=all_links, pagination_info=final_pagination_info)

    except Exception as e:
        logger.error(f"Error extracting job listings from {career_page_url}: {e}")
        return PageExtractionResult(
            links=[], 
            pagination_info=PaginationInfo(current_page=1, total_pages=1, next_page_url=None, has_next_page=False)
        )

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
