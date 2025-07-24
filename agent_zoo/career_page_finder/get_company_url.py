
from pydantic import BaseModel
from loguru import logger
import dotenv
dotenv.load_dotenv(override=True)
class CompanyUrlResponse(BaseModel):
    company_name: str
    city: str
    country: str
    official_url: str
    confidence: float
    validation_notes: str
    

import os
import requests
from typing import List, Dict


def serper_search(query: str, num_results: int = 10) -> Dict:
    """
    Perform a search using the Serper API.

    Args:
        query (str): Search query.
        num_results (int): Maximum number of results to return.

    Returns:
        dict: Raw JSON response from Serper API.

    Raises:
        RuntimeError: If the request fails.
    """
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': os.getenv('SERPER_API_KEY'),
        'Content-Type': 'application/json'
    }
    payload = {"q": query, "num": num_results}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Serper API request failed: {e}")


def web_search(query: str,max_num_return: int = 5) -> List[str]:
    """
    Web search tool to return top related urls.

    Args:
        query (str): The search query.

    Returns:
        List[str]: A list of result URLs (may be empty).
    """
    
    try:
        results = serper_search(query)
    except RuntimeError as e:
        logger.error(f"Web search failed: {e}")
        return []

    organic_results = results.get("organic", [])
    if not isinstance(organic_results, list):
        return []

    urls = [item["link"] for item in organic_results if "link" in item]
    return urls[:max_num_return]


   
async def get_company_url(name: str, city: str, country: str) -> dict:
      query = f"company '{company_name}' in {city} {country} "
      results = web_search(query, 1)
      if not results:
         return None
      else:
         return results[0]
      
if __name__ == "__main__":
   demo()

  