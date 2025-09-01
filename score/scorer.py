#!/usr/bin/env python3
"""
Lead scoring module using OpenAI and prompt templates
"""

import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path to import prompt renderer
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.renderer import PromptRenderer

# Load environment variables
load_dotenv()

class LeadScorer:
    """Scores leads using OpenAI and structured prompt templates"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.model = model
        self.renderer = PromptRenderer()
    
    def score_company(self, company: str, enriched_data: Dict) -> Dict[str, Any]:
        """Score a single company using the Recurly template
        
        Args:
            company: Company name
            enriched_data: Dict containing enrichment data from SerpAPI
            
        Returns:
            Dict containing the scoring results
        """
        # Format enriched data for the prompt
        formatted_data = self._format_enriched_data(enriched_data)
        
        # Render the prompt template
        prompt = self.renderer.render_recurly_template(company, formatted_data)
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=1000
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            result = self._parse_scoring_response(content)
            return result
            
        except Exception as e:
            print(f"Error scoring {company}: {e}")
            return self._create_error_response(company, str(e))
    
    def score_companies(self, enriched_list: List[Dict]) -> List[Dict[str, Any]]:
        """Score multiple companies (backward compatibility)
        
        Args:
            enriched_list: List of enriched company data
            
        Returns:
            List of scoring results
        """
        results = []
        for item in enriched_list:
            company = item.get('company', 'Unknown')
            result = self.score_company(company, item)
            results.append(result)
        return results
    
    def _format_enriched_data(self, enriched_data: Dict) -> str:
        """Format enriched data into a readable string for the prompt"""
        formatted = []
        
        if 'hiring_signals' in enriched_data and enriched_data['hiring_signals']:
            formatted.append("HIRING SIGNALS:")
            for signal in enriched_data['hiring_signals']:
                formatted.append(f"- {signal}")
            formatted.append("")
        
        if 'tech_stack' in enriched_data and enriched_data['tech_stack']:
            formatted.append("TECH STACK:")
            for tech in enriched_data['tech_stack']:
                formatted.append(f"- {tech}")
            formatted.append("")
        
        if 'news_mentions' in enriched_data and enriched_data['news_mentions']:
            formatted.append("NEWS MENTIONS:")
            for news in enriched_data['news_mentions']:
                formatted.append(f"- {news}")
            formatted.append("")
        
        return "\n".join(formatted) if formatted else "No enriched data available"
    
    def _parse_scoring_response(self, content: str) -> Dict[str, Any]:
        """Parse the OpenAI response and extract JSON"""
        try:
            # Try to find JSON in the response
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw content: {content}")
            # Return a fallback response
            return {
                "company": "Unknown",
                "score": 0,
                "error": "Failed to parse scoring response",
                "raw_response": content
            }
    
    def _create_error_response(self, company: str, error: str) -> Dict[str, Any]:
        """Create a standard error response"""
        return {
            "company": company,
            "score": 0,
            "error": error,
            "breakdown": {},
            "summary": [],
            "justification": f"Error occurred during scoring: {error}",
            "priority": "Low",
            "next_steps": "Review error and retry"
        }

# Backward compatibility function
def score_companies(enriched_list, model='gpt-3.5-turbo'):
    """Legacy function for backward compatibility"""
    scorer = LeadScorer(model=model)
    return scorer.score_companies(enriched_list)
