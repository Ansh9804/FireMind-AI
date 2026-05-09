import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()
SERP_API_KEY = os.getenv("SERP_API_KEY")

def search_web(query):
    if not SERP_API_KEY:
        return "Web search skipped: API key not configured."
        
    try:
        params = {
            "q": query,
            "api_key": SERP_API_KEY,
            "num": 3
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        organic = results.get("organic_results", [])
        snippets = []
        for r in organic:
            if r.get("snippet"):
                snippets.append(f"Source ({r.get('link')}): {r.get('snippet')}")
        return "\n\n".join(snippets)

    except Exception as e:
        print(f"SerpAPI Error: {e}")
        return "Web search failed."