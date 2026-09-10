"""Provider-agnostic web search used to ground self-care advice.

Mirrors llm_client.py. PROVIDER comes from HEALTHDECK_SEARCH_PROVIDER.

- "tavily": queries the Tavily REST API, restricted to a fixed allowlist of
  trusted medical domains. Needs TAVILY_API_KEY. If that key is not set the
  call is treated as "mock" so nothing crashes.
- "mock": returns whatever set_mock_results queued, or an empty list.

search(query) returns a list of {"title", "url", "content"} dicts. An empty
list is the signal for the graph to keep the model-only self-care advice.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.environ.get("HEALTHDECK_SEARCH_PROVIDER", "tavily")

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

TRUSTED_MEDICAL_DOMAINS = [
    "mayoclinic.org",
    "nhs.uk",
    "medlineplus.gov",
    "cdc.gov",
    "who.int",
    "clevelandclinic.org",
]

_mock_results = []


def set_mock_results(results):
    global _mock_results
    _mock_results = list(results)


def _tavily_search(query):
    api_key = os.environ.get("TAVILY_API_KEY")
    response = requests.post(
        TAVILY_SEARCH_URL,
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
            "include_domains": TRUSTED_MEDICAL_DOMAINS,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    for item in payload.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
        )
    return results


def search(query):
    provider = PROVIDER
    if provider == "tavily" and not os.environ.get("TAVILY_API_KEY"):
        provider = "mock"

    if provider == "mock":
        return list(_mock_results)

    if provider == "tavily":
        try:
            return _tavily_search(query)
        except requests.RequestException:
            return []

    return []
