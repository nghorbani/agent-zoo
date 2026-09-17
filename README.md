# agent-zoo

Experiments with LLM agents built on the OpenAI Agents SDK. The one experiment in the zoo so far
finds a company's job listings in three steps, each a small async function in
`agent_zoo/get_job_listings/`:

1. `get_company_url.get_company_url(name, city, country)`: the company's website from a Serper
   web search (top hit).
2. `get_career_page.get_career_page(company_name, city, country, website=None)`: an agent with a
   Playwright browser (via the Playwright MCP server) browses candidate pages and returns the
   validated career page URL.
3. `get_job_listings.get_job_listings(career_page_url)`: an agent with the same browser reads the
   career page, follows the pagination and returns the job links plus pagination info as a
   `PageExtractionResult`.

## Install

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js (for `npx @playwright/mcp`,
which the agents start themselves), and API keys for [Serper](https://serper.dev/) and OpenAI.

```bash
uv sync              # runtime
uv sync --extra dev  # plus pytest and pytest-asyncio
```

Put the keys in a `.env` file at the repository root (it is read by `python-dotenv` and ignored by
git):

```
SERPER_API_KEY=...
OPENAI_API_KEY=...
```

## Run one crawler

Each module has a `demo()` that runs it on a sample company:

```bash
uv run python -m agent_zoo.get_job_listings.get_company_url     # website of "Cubert" in Ulm
uv run python -m agent_zoo.get_job_listings.get_career_page     # career page, needs the Playwright MCP server
uv run python -m agent_zoo.get_job_listings.get_job_listings    # job links on a career page, with pagination
```

Or from Python:

```python
import asyncio
from agent_zoo.get_job_listings.get_job_listings import get_job_listings

result = asyncio.run(get_job_listings("https://www.asys-group.com/de/karriere/jobboerse"))
for link in result.links:
    print(link.title, link.url)
```

## Tests

```bash
uv run pytest                                   # offline tests (data models)
AGENT_ZOO_RUN_NETWORK=1 uv run pytest -m network  # live runs against real websites; needs the keys and a browser
```

The network tests are marked `network` and skipped with an explicit reason unless
`AGENT_ZOO_RUN_NETWORK=1` is set.

## Licence

Apache-2.0, see [LICENSE](LICENSE).
