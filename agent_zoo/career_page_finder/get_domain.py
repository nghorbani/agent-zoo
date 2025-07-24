"""
Minimal agentic solution to find company URLs based on company name, city, and country.

Test cases:
- "Cubert, Ulm, Germany: https://cubert-hyperspectral.com/"
- "Asys, Dornstadt, Germany: https://www.asys-group.com/"
- "MPI for intelligent systems, Tuebingen, Germany: https://is.mpg.de/"
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import re

import openai
from playwright.async_api import async_playwright
import requests
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

@dataclass
class CompanyInfo:
    name: str
    city: str
    country: str
    
    def __str__(self) -> str:
        return f"{self.name}, {self.city}, {self.country}"

@dataclass
class CompanyResult:
    company_info: CompanyInfo
    url: Optional[str] = None
    confidence: float = 0.0
    method: str = "unknown"
    validated: bool = False
    error: Optional[str] = None

@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str

@dataclass
class ValidationResult:
    is_validated: bool
    confidence: float
    reasoning: str

class CompanyURLFinder:
    """Minimal agentic solution to find company URLs using validator agent."""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        
    async def find_company_url(self, company_info: CompanyInfo) -> CompanyResult:
        """Main method to find company URL using validator agent approach."""
        result = CompanyResult(company_info=company_info)
        
        try:
            # Step 1: Search for company using search tool
            logger.info(f"Searching for {company_info}")
            search_results = await self._search_web(company_info)
            
            if not search_results:
                result.error = "No search results found"
                logger.warning(f"No search results found for {company_info}")
                return result
            
            # Step 2: Validate only first 3 results and pick the first validated one
            max_results_to_validate = min(3, len(search_results))
            logger.info(f"Validating first {max_results_to_validate} search results")
            
            for i in range(max_results_to_validate):
                search_result = search_results[i]
                validation = await self._validate_with_agent(search_result, company_info)
                
                if validation.is_validated:
                    # Found first validated result, use it immediately
                    result.url = search_result.url
                    result.confidence = validation.confidence
                    result.method = "validator_agent"
                    result.validated = True
                    
                    logger.info(f"Selected first validated result: {result.url} (confidence: {result.confidence})")
                    break
                else:
                    logger.debug(f"Rejected result: {search_result.url} - {validation.reasoning}")
            else:
                # No validated results found in first 3
                result.error = "No result was approved by validator"
                logger.warning(f"No results were approved by validator in first {max_results_to_validate} results for {company_info}")
                
        except Exception as e:
            logger.error(f"Error finding URL for {company_info}: {str(e)}")
            result.error = str(e)
            
        return result
    
    async def _search_web(self, company_info: CompanyInfo) -> List[SearchResult]:
        """Search for company using web search tool."""
        try:
            # Construct search query as specified - try multiple query formats
            queries = [
                f'"{company_info.name}" {company_info.city} {company_info.country}',
                f'{company_info.name} {company_info.city} {company_info.country} website',
                f'{company_info.name} company {company_info.city} {company_info.country}'
            ]
            
            # Use Serper API as the search tool
            if not self.serper_api_key:
                logger.error("SERPER_API_KEY not found")
                return []
            
            search_results = []
            
            # Try different query formats until we get results
            for query in queries:
                logger.info(f"Search query: {query}")
                
                # Use Serper API (not SerpAPI)
                headers = {
                    'X-API-KEY': self.serper_api_key,
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'q': query,
                    'num': 10
                }
                
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json()
                    logger.debug(f"Search API response: {results}")
                    
                    if "organic" in results and results["organic"]:
                        for result in results["organic"]:
                            search_result = SearchResult(
                                url=result.get("link", ""),
                                title=result.get("title", ""),
                                snippet=result.get("snippet", "")
                            )
                            search_results.append(search_result)
                        
                        logger.info(f"Found {len(search_results)} search results with query: {query}")
                        break  # Stop trying other queries if we found results
                    else:
                        logger.debug(f"No results for query: {query}")
                else:
                    logger.error(f"Search API error: {response.status_code} - {response.text}")
            
            if not search_results:
                logger.warning("No search results found with any query format")
                
            return search_results
            
        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            return []
    
    async def _validate_with_agent(self, search_result: SearchResult, company_info: CompanyInfo) -> ValidationResult:
        """Validate search result using LLM validator agent."""
        try:
            prompt = f"""
            You are a validator agent that determines if a search result corresponds to the correct company.
            
            Company Information:
            - Name: {company_info.name}
            - City: {company_info.city}
            - Country: {company_info.country}
            
            Search Result:
            - URL: {search_result.url}
            - Title: {search_result.title}
            - Snippet: {search_result.snippet}
            
            Analyze if this search result is for the correct company. Consider:
            1. Does the URL domain match the company name?
            2. Does the title mention the company name?
            3. Does the snippet describe the right company in the right location?
            4. Is this likely the official company website?
            
            Respond with a JSON object containing:
            - "is_validated": boolean indicating if this is the correct company
            - "confidence": float between 0.0 and 1.0 indicating your confidence level
            - "reasoning": string explaining your decision
            
            Be strict in validation - only approve if you're confident this is the correct company.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"Validator response for {search_result.url}: {content}")
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()
                
                data = json.loads(content)
                
                return ValidationResult(
                    is_validated=data.get("is_validated", False),
                    confidence=data.get("confidence", 0.0),
                    reasoning=data.get("reasoning", "No reasoning provided")
                )
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse validator JSON response: {e}")
                return ValidationResult(
                    is_validated=False,
                    confidence=0.0,
                    reasoning="Failed to parse validator response"
                )
                
        except Exception as e:
            logger.error(f"Validation failed for {search_result.url}: {str(e)}")
            return ValidationResult(
                is_validated=False,
                confidence=0.0,
                reasoning=f"Validation error: {str(e)}"
            )

# Convenience functions for easy usage
async def find_company_url(company_name: str, city: str, country: str) -> CompanyResult:
    """Find company URL given name, city, and country."""
    finder = CompanyURLFinder()
    company_info = CompanyInfo(name=company_name, city=city, country=country)
    return await finder.find_company_url(company_info)

def find_company_url_sync(company_name: str, city: str, country: str) -> CompanyResult:
    """Synchronous wrapper for find_company_url."""
    return asyncio.run(find_company_url(company_name, city, country))

# CLI functions
def find_url(company_name: str, city: str, country: str) -> None:
    """Find company URL given name, city, and country.
    
    Args:
        company_name: Name of the company
        city: City where the company is located
        country: Country where the company is located
    """
    result = find_company_url_sync(company_name, city, country)
    
    logger.info(f"Company: {result.company_info}")
    logger.info(f"URL: {result.url}")
    logger.info(f"Confidence: {result.confidence}")
    logger.info(f"Method: {result.method}")
    logger.info(f"Validated: {result.validated}")
    if result.error:
        logger.error(f"Error: {result.error}")

def test_cases() -> None:
    """Run the provided test cases."""
    test_cases = [
        ("Cubert", "Ulm", "Germany"),
        ("Asys", "Dornstadt", "Germany"),
        ("MPI for intelligent systems", "Tuebingen", "Germany"),
    ]
    
    for company_name, city, country in test_cases:
        logger.info(f"Testing: {company_name}, {city}, {country}")
        logger.info("=" * 60)
        
        result = find_company_url_sync(company_name, city, country)
        
        logger.info(f"Result URL: {result.url}")
        logger.info(f"Confidence: {result.confidence}")
        logger.info(f"Method: {result.method}")
        logger.info(f"Validated: {result.validated}")
        if result.error:
            logger.error(f"Error: {result.error}")
        logger.info("")

if __name__ == "__main__":
    import fire
    fire.Fire({
        'find': find_url,
        'test': test_cases,
    })
