# Implementation Plan for Career Page Finder Agent
Perfect! Updated plan with agentic validation and proper tooling:

## Updated Step-by-Step Implementation Plan

### Step 1: Update Dependencies (UV)
**Command: `uv add <packages>`**
- `uv add google-search-results` (SerpAPI)
- `uv add beautifulsoup4` (HTML parsing)
- Note: Fire already in dependencies, OpenAI Agent SDK already available

### Step 2: Create Data Models
**File: `agent_zoo/01_career_page_finder/models.py`**
- Create `CareerPageResult` class with fields:
  - `url: str`
  - `confidence_score: float`
  - `company_name: str`
  - `validation_reasoning: str`
  - `found_indicators: List[str]`

### Step 3: Implement SerpAPI Search Tool
**File: `agent_zoo/01_career_page_finder/tools/serp_search.py`**
- Create `SerpSearchTool` class
- Implement search query construction: `"{company} {city} {country} careers jobs"`
- Parse SerpAPI response to extract candidate URLs
- Filter results to prioritize company domain matches
- Return top 5-10 candidate URLs

### Step 4: Create Agentic Career Page Validator
**File: `agent_zoo/01_career_page_finder/agents/validator_agent.py`**
- Create `CareerPageValidatorAgent` using OpenAI Agent SDK
- Give it tools to:
  - Analyze HTML content structure
  - Identify job-related elements
  - Reason about page purpose
- Implement `validate_career_page(url, html_content, company_name)` method
- Return structured validation with:
  - Confidence score (0.0 to 1.0)
  - Reasoning explanation
  - Specific indicators found

### Step 5: Create Main Orchestrator Agent
**File: `agent_zoo/01_career_page_finder/agents/career_finder_agent.py`**
- Create `CareerPageFinderAgent` class using OpenAI Agent SDK
- Implement main workflow method `find_career_page(company, city, country)`:
  1. Use SerpSearchTool to find candidate URLs
  2. For each candidate URL:
     - Use MCP Playwright to navigate and extract content
     - Use CareerPageValidatorAgent to validate and score the page
  3. Return the highest-scoring result as `CareerPageResult`

### Step 6: Update Main Entry Point with Fire CLI
**File: `agent_zoo/01_career_page_finder/main.py`**
- Import `CareerPageFinderAgent`
- Create Fire CLI class:
```python
class CareerPageFinderCLI:
    def find(self, company: str, city: str, country: str):
        """Find career page for company"""
        agent = CareerPageFinderAgent()
        result = agent.find_career_page(company, city, country)
        return result

if __name__ == "__main__":
    fire.Fire(CareerPageFinderCLI)
```
- Add MCP server configuration for Playwright
- Include example usage documentation

### Step 7: Create Test File
**File: `agent_zoo/01_career_page_finder/tests/test_agent.py`**
- Create `TestCareerPageFinder` class
- Implement 3 test methods for the required test cases:
  - `test_cuber_ulm_germany()`
  - `test_asys_dornstadt_germany()`
  - `test_mpi_tuebingen_germany()`
- Each test validates URL and confidence score > 0.7

### Step 8: Create Test Configuration
**File: `agent_zoo/01_career_page_finder/tests/conftest.py`**
- Set up pytest configuration
- Configure environment variables for testing
- Set up MCP server configuration for tests

### Step 9: Create Package Structure
**Files to create/update:**
- `agent_zoo/01_career_page_finder/tools/__init__.py`
- `agent_zoo/01_career_page_finder/agents/__init__.py`
- `agent_zoo/01_career_page_finder/tests/__init__.py`

### Step 10: Test and Validate
- Run tests: `uv run pytest agent_zoo/01_career_page_finder/tests/`
- Test CLI: `uv run python agent_zoo/01_career_page_finder/main.py find "Cuber" "Ulm" "Germany"`
- Debug and refine agentic validation based on results

## Updated Implementation Order:
1. **Dependencies** (Step 1) - `uv add` commands
2. **Models** (Step 2) - Foundation data structures
3. **SerpAPI Tool** (Step 3) - Core search functionality  
4. **Agentic Validator** (Step 4) - LLM-powered validation agent
5. **Main Agent** (Step 5) - Orchestration logic
6. **Fire CLI** (Step 6) - Command-line interface
7. **Tests** (Steps 7-8) - Validation
8. **Package Structure** (Step 9) - Clean imports
9. **Final Testing** (Step 10) - End-to-end validation

## Key Updates:
- ✅ **Agentic Validation**: CareerPageValidatorAgent uses LLM reasoning
- ✅ **UV Environment**: All dependency management via `uv add`
- ✅ **Fire CLI**: Clean command-line interface with Fire
- ✅ **Two-Agent Architecture**: Finder + Validator agents working together

The validator agent will now use LLM reasoning to analyze pages and provide detailed explanations for its confidence scores, making the solution truly agentic throughout.

