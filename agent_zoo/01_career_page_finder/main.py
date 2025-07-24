# given company name city and country, find the career page URL where the company posts job openings
# the url should be the one where all listings are there related to the company

# test case: "Cuber, Ulm, Germany: https://cubert-hyperspectral.com/de/karriere/"
# test case: "Asys, Dornstadt, Germany: https://www.asys-group.com/en/career/job-board"
# test case: "MPI for intelligent systems, Tuebingen, Germany: https://is.mpg.de/jobs"

# Use SerpAPI or Brave to find the career page
# Use Playwright to extract listings from the page (structure varies)
# Validate with a simple heuristic or LLM (e.g., presence of <a> tags with “Apply”, or job cards)


server_configs = {
    
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

    "memory":
    {
        "name": "Memory",
        "params":{ "command": "npx", "args":["-y", "mcp-memory-libsql"], "env":{"LIBSQL_URL":"file:./memory/ed.db"}},
        "client_session_timeout_seconds":30
    },
}