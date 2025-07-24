from pydantic import BaseModel, Field

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
class LinkList(BaseModel):
    """
    Represents a list of links to job listings.
    """
    links: List[Link] = Field(description="A list of job listing links")


async def get_job_listings(career_page_url:str) -> JobListings:
    """
    
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
            "params": {"command": "npx", "args": ["-y", "mcp-memory-libsql"], "env": {"LIBSQL_URL": "file:./memory/ed.db"}},
            "client_session_timeout_seconds": 30
        },
    }
    
    # Create agent prompt with the list of URLs
    
    agent_prompt = f"""
You are an intelligent browser automation agent tasked with extracting job listings from a company's career page using the web_browser tool.

career_page_url is {career_page_url}

## GOAL
Your goal is to return a structured LinkList object that contains all job listing links (`title`, `url`) found on the given career page. The job titles must represent actual job advertisements, not generic navigation or informational links.

## INSTRUCTIONS

1. Visit the provided `career_page_url` using the `web_browser` tool.
2. Extract all anchor links on the page. For each link:
   - Retain the link only if it looks like a real job posting.
     - Job links often contain job titles like "Software Engineer", "Data Scientist", "Sales Manager", etc.
     - Avoid links like "Contact", "About us", "Imprint", or "Privacy Policy".
     - Avoid links that loop back to the same page or external sites unrelated to job posts.
   - Use heuristics (e.g., presence of job-related words in the anchor text or URL).
3. Detect and follow pagination (e.g., "Next", "Weiter", or page numbers):
   - Navigate to all subsequent pages.
   - Apply the same filtering logic on each page.
   - Accumulate links across all pages.
4. For each job posting link:
   - Normalize the title by stripping whitespace and collapsing internal spaces.
   - Combine the title and URL and hash them.
   - Check against memory if the hash exists. If so, skip it.
   - If not in memory:
     - Add the job link to the LinkList.
     - Save the hash along with url and title to memory to prevent future duplicates.

## OUTPUT
Return a single `LinkList` object containing unique job posting links.

## MEMORY USAGE
Use memory to persist visited job links across runs. Store the following fields:
- `title`
- `url`
- `hash(title + url)`

Only use the `web_browser` tool to navigate and extract information.
Return your final answer as a `LinkList` object.
"""


    # Use MCP server with the correct pattern
    async with MCPServerStdio(**server_configs["playwright"]) as mcp_server_playwright:
        async with MCPServerStdio(**server_configs["memory"]) as mcp_server_memory:
            # Create the agent with the MCP server
            agent = Agent(
                name="job_listing_extractor",
                instructions=agent_prompt,
                model="gpt-4.1-mini",
                mcp_servers=[mcp_server_playwright, mcp_server_memory],
                output_type=LinkList
            )
            
            # Use trace and await Runner.run as specified
            with trace("extract job listings"):
                result = await Runner.run(agent, f"Please extract job listings from {career_page_url}.")
                
                # The result should already be structured due to output_type=LinkList
                if hasattr(result, 'final_output') and isinstance(result.final_output, LinkList):
                    structured = result.final_output
                    logger.info(f"Extracted {len(structured.links)} job links from {career_page_url}")
                    return structured
                elif isinstance(result, LinkList):
                    logger.info(f"Extracted {len(result.links)} job links from {career_page_url}")
                    return result
                else:
                    # Fallback if structured response parsing failed
                    logger.warning(f"Failed to get structured response for {career_page_url}. Returning empty LinkList.")
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
        result = await get_job_listings(expected_career_page)
        if result is None:
            print("No job listings found.")
        else:
            print(f"Found {len(result.links)} job listings:")
            for link in result.links:
                print(f"Job Title: {link.title}, URL: {link.url}")

    asyncio.run(main())


if __name__ == "__main__":
    demo()
