#!/usr/bin/env python3
"""
Lead scoring module using OpenAI and prompt templates with robust API handling
"""

import os
import json
import sys
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import modules
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from prompts.renderer import PromptRenderer
from utils.api_client import RobustOpenAIClient, APIUsageTracker

# Load environment variables
load_dotenv()

class LeadScorer:
    """Scores leads using OpenAI and structured prompt templates with robust API handling and A/B testing"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo", models: Optional[List[str]] = None, ab_test_id: Optional[str] = None):
        # Use robust client with fallback models
        fallback_models = models or [model, "gpt-4o-mini", "gpt-3.5-turbo"]
        self.client = RobustOpenAIClient(api_key=api_key, models=fallback_models)
        self.renderer = PromptRenderer()
        self.usage_tracker = APIUsageTracker()
        
        # A/B testing support
        self.ab_test_id = ab_test_id
        self.prompt_manager = None
        if ab_test_id:
            from prompts.prompt_manager import PromptVersionManager
            self.prompt_manager = PromptVersionManager()
    
    def score_company(self, company: str, enriched_data: Dict) -> Dict[str, Any]:
        """Score a single company using the Recurly template with robust API handling and A/B testing
        
        Args:
            company: Company name
            enriched_data: Dict containing enrichment data from SerpAPI
            
        Returns:
            Dict containing the scoring results
        """
        # Format enriched data for the prompt
        formatted_data = self._format_enriched_data(enriched_data)
        
        # Determine which prompt version to use
        prompt_version_id = None
        if self.ab_test_id and self.prompt_manager:
            prompt_version_id = self.prompt_manager.get_prompt_for_ab_test(self.ab_test_id)
        
        # Render the prompt template
        if prompt_version_id:
            # Use A/B test version
            variables = {'company': company, 'enriched_data': formatted_data}
            prompt = self.renderer.render_with_version_manager(prompt_version_id, variables)
        else:
            # Use default template
            prompt = self.renderer.render_recurly_template(company, formatted_data)
        
        # Call OpenAI API with fallback and retry logic
        messages = [{"role": "user", "content": prompt}]
        api_result = self.client.chat_completion_with_fallback(
            messages=messages,
            temperature=0.1,  # Low temperature for consistent scoring
            max_tokens=1000
        )
        
        # Track usage
        self.usage_tracker.track_openai_usage(api_result.get('usage'), api_result['success'])
        
        if api_result['success']:
            # Parse the JSON response
            content = api_result['content'].strip()
            result = self._parse_scoring_response(content)
            
            # Add metadata about which model and prompt version was used
            result['model_used'] = api_result['model_used']
            if prompt_version_id:
                result['prompt_version_id'] = prompt_version_id
                result['ab_test_id'] = self.ab_test_id
                
                # Record A/B test result
                if self.prompt_manager:
                    self.prompt_manager.record_test_result(
                        self.ab_test_id, prompt_version_id, company, result
                    )
            
            return result
        else:
            print(f"Error scoring {company}: {api_result['error']}")
            error_response = self._create_error_response(company, api_result['error'])
            error_response['api_error_details'] = api_result
            if prompt_version_id:
                error_response['prompt_version_id'] = prompt_version_id
                error_response['ab_test_id'] = self.ab_test_id
            return error_response
    
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
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get API usage summary"""
        return self.usage_tracker.get_usage_summary()
    
    def print_usage_summary(self):
        """Print API usage summary"""
        self.usage_tracker.print_usage_summary()

# Backward compatibility function
def score_companies(enriched_list, model='gpt-3.5-turbo'):
    """Legacy function for backward compatibility"""
    scorer = LeadScorer(model=model)
    return scorer.score_companies(enriched_list)
