#!/usr/bin/env python3
"""
SerpAPI integration for lead enrichment
Gathers hiring signals, tech stack info, and company news
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from serpapi import GoogleSearch

# Load environment variables
load_dotenv()

class LeadEnricher:
    """Enriches company leads with web research via SerpAPI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SerpAPI key not found. Please set SERPAPI_KEY in .env file")
    
    def enrich_company(self, company: str) -> Dict:
        """Enrich a single company with hiring, tech stack, and news data
        
        Args:
            company: Company name to research
            
        Returns:
            Dict containing enriched company data
        """
        enrichment = {
            "company": company,
            "hiring_signals": self._search_hiring_signals(company),
            "tech_stack": self._search_tech_stack(company),
            "news_mentions": self._search_news_mentions(company)
        }
        return enrichment
    
    def _search_hiring_signals(self, company: str) -> List[str]:
        """Search for hiring/job posting signals"""
        query = f'"{company}" hiring project manager OR "software engineer" OR "product manager"'
        return self._get_search_snippets(query, num_results=3)
    
    def _search_tech_stack(self, company: str) -> List[str]:
        """Search for technology stack and infrastructure info"""
        query = f'"{company}" tech stack OR infrastructure OR "uses AWS" OR "uses React"'
        return self._get_search_snippets(query, num_results=3)
    
    def _search_news_mentions(self, company: str) -> List[str]:
        """Search for recent news and press mentions"""
        query = f'"{company}" news OR press release OR funding OR acquisition'
        return self._get_search_snippets(query, num_results=3)
    
    def _get_search_snippets(self, query: str, num_results: int = 5) -> List[str]:
        """Perform search and extract relevant snippets"""
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": num_results
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            snippets = []
            for result in results.get('organic_results', []):
                if 'snippet' in result:
                    snippets.append(result['snippet'])
            
            return snippets
            
        except Exception as e:
            print(f"Search error for '{query}': {e}")
            return []

# Test function
def test_enrichment():
    """Test the enrichment functionality"""
    try:
        enricher = LeadEnricher()
        result = enricher.enrich_company("Shopify")
        print("✅ SerpAPI enrichment working!")
        print(f"Found {len(result['hiring_signals'])} hiring signals")
        print(f"Found {len(result['tech_stack'])} tech mentions")
        print(f"Found {len(result['news_mentions'])} news items")
        return True
    except Exception as e:
        print(f"❌ Enrichment Error: {e}")
        return False

if __name__ == "__main__":
    test_enrichment()
