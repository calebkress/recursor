#!/usr/bin/env python3
"""
Robust API client with retry logic and model fallback
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv
from openai import OpenAI
from serpapi import GoogleSearch
import openai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom exception for API errors"""
    pass

class QuotaExceededError(APIError):
    """Exception for quota/billing errors"""
    pass

class RateLimitError(APIError):
    """Exception for rate limiting errors"""
    pass

class RobustOpenAIClient:
    """OpenAI client with retry logic and model fallback"""
    
    DEFAULT_MODELS = [
        "gpt-3.5-turbo",
        "gpt-4o-mini", 
        "gpt-4o"
    ]
    
    def __init__(self, api_key: Optional[str] = None, models: Optional[List[str]] = None):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.models = models or self.DEFAULT_MODELS
        self.current_model_index = 0
        
    def get_current_model(self) -> str:
        """Get the current model to use"""
        return self.models[self.current_model_index]
    
    def fallback_to_next_model(self) -> bool:
        """Fallback to next model in the list. Returns True if fallback available."""
        if self.current_model_index < len(self.models) - 1:
            self.current_model_index += 1
            logger.warning(f"Falling back to model: {self.get_current_model()}")
            return True
        return False
    
    def reset_model_selection(self):
        """Reset to the first model in the list"""
        self.current_model_index = 0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError))
    )
    def _make_chat_request(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Make a chat completion request with retry logic"""
        try:
            response = self.client.chat.completions.create(
                model=self.get_current_model(),
                messages=messages,
                **kwargs
            )
            return {
                'success': True,
                'content': response.choices[0].message.content,
                'model_used': self.get_current_model(),
                'usage': response.usage.model_dump() if response.usage else None
            }
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit hit for {self.get_current_model()}: {e}")
            raise RateLimitError(f"Rate limit: {e}")
            
        except openai.APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise APIError(f"Connection error: {e}")
            
        except openai.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise APIError(f"Authentication error: {e}")
            
        except Exception as e:
            # Check if it's a quota error
            if "quota" in str(e).lower() or "billing" in str(e).lower():
                logger.error(f"Quota exceeded for {self.get_current_model()}: {e}")
                raise QuotaExceededError(f"Quota exceeded: {e}")
            else:
                logger.error(f"Unexpected error: {e}")
                raise APIError(f"Unexpected error: {e}")
    
    def chat_completion_with_fallback(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        Make chat completion request with model fallback
        
        Returns:
            Dict with success, content, model_used, usage, and any error info
        """
        self.reset_model_selection()
        
        for attempt in range(len(self.models)):
            try:
                result = self._make_chat_request(messages, **kwargs)
                return result
                
            except QuotaExceededError as e:
                logger.warning(f"Quota exceeded for {self.get_current_model()}: {e}")
                if not self.fallback_to_next_model():
                    return {
                        'success': False,
                        'error': f"Quota exceeded for all models: {e}",
                        'model_used': None,
                        'fallback_exhausted': True
                    }
                continue
                
            except (RateLimitError, APIError) as e:
                logger.warning(f"API error for {self.get_current_model()}: {e}")
                if not self.fallback_to_next_model():
                    return {
                        'success': False,
                        'error': f"All models failed: {e}",
                        'model_used': None,
                        'fallback_exhausted': True
                    }
                continue
        
        # This shouldn't be reached, but just in case
        return {
            'success': False,
            'error': "All fallback attempts exhausted",
            'model_used': None,
            'fallback_exhausted': True
        }

class RobustSerpAPIClient:
    """SerpAPI client with retry logic"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SerpAPI key not found")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((APIError, RateLimitError))
    )
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform search with retry logic
        
        Returns:
            Dict with success status and results or error info
        """
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                **kwargs
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for API errors in response
            if 'error' in results:
                error_msg = results['error']
                if 'rate limit' in error_msg.lower():
                    raise RateLimitError(f"SerpAPI rate limit: {error_msg}")
                else:
                    raise APIError(f"SerpAPI error: {error_msg}")
            
            return {
                'success': True,
                'results': results,
                'query': query
            }
            
        except Exception as e:
            if 'rate limit' in str(e).lower():
                logger.warning(f"SerpAPI rate limit hit: {e}")
                raise RateLimitError(f"Rate limit: {e}")
            else:
                logger.error(f"SerpAPI error: {e}")
                raise APIError(f"SerpAPI error: {e}")
    
    def get_organic_results(self, query: str, num_results: int = 10) -> List[Dict]:
        """Get organic search results with error handling"""
        try:
            result = self.search(query, num=num_results)
            if result['success']:
                return result['results'].get('organic_results', [])
            else:
                logger.error(f"Failed to get results for query: {query}")
                return []
        except Exception as e:
            logger.error(f"Error getting organic results: {e}")
            return []

class APIUsageTracker:
    """Track API usage and costs"""
    
    def __init__(self):
        self.openai_usage = {
            'total_tokens': 0,
            'prompt_tokens': 0, 
            'completion_tokens': 0,
            'requests': 0,
            'errors': 0
        }
        self.serpapi_usage = {
            'requests': 0,
            'errors': 0
        }
    
    def track_openai_usage(self, usage: Optional[Dict], success: bool):
        """Track OpenAI API usage"""
        self.openai_usage['requests'] += 1
        if not success:
            self.openai_usage['errors'] += 1
        
        if usage:
            self.openai_usage['total_tokens'] += usage.get('total_tokens', 0)
            self.openai_usage['prompt_tokens'] += usage.get('prompt_tokens', 0)
            self.openai_usage['completion_tokens'] += usage.get('completion_tokens', 0)
    
    def track_serpapi_usage(self, success: bool):
        """Track SerpAPI usage"""
        self.serpapi_usage['requests'] += 1
        if not success:
            self.serpapi_usage['errors'] += 1
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary"""
        return {
            'openai': self.openai_usage,
            'serpapi': self.serpapi_usage,
            'total_requests': self.openai_usage['requests'] + self.serpapi_usage['requests'],
            'total_errors': self.openai_usage['errors'] + self.serpapi_usage['errors']
        }
    
    def print_usage_summary(self):
        """Print usage summary to console"""
        summary = self.get_usage_summary()
        
        print("\n📊 API Usage Summary:")
        print("-" * 40)
        print(f"OpenAI Requests: {summary['openai']['requests']} (Errors: {summary['openai']['errors']})")
        print(f"OpenAI Tokens: {summary['openai']['total_tokens']} total")
        print(f"SerpAPI Requests: {summary['serpapi']['requests']} (Errors: {summary['serpapi']['errors']})")
        print(f"Total Requests: {summary['total_requests']} (Errors: {summary['total_errors']})")
        
        if summary['total_errors'] > 0:
            error_rate = (summary['total_errors'] / summary['total_requests']) * 100
            print(f"Error Rate: {error_rate:.1f}%")

# Example usage and testing
def test_robust_clients():
    """Test the robust API clients"""
    print("Testing Robust API Clients...")
    
    # Test OpenAI client
    openai_client = RobustOpenAIClient()
    tracker = APIUsageTracker()
    
    print("\n1. Testing OpenAI with fallback...")
    messages = [{"role": "user", "content": "Say hello in exactly 3 words."}]
    
    result = openai_client.chat_completion_with_fallback(messages, max_tokens=10)
    tracker.track_openai_usage(result.get('usage'), result['success'])
    
    if result['success']:
        print(f"✅ Success with {result['model_used']}: {result['content']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test SerpAPI client
    print("\n2. Testing SerpAPI with retry...")
    serpapi_client = RobustSerpAPIClient()
    
    search_result = serpapi_client.search("test query", num=1)
    tracker.track_serpapi_usage(search_result['success'])
    
    if search_result['success']:
        print(f"✅ SerpAPI working: Found {len(search_result['results'].get('organic_results', []))} results")
    else:
        print("❌ SerpAPI failed")
    
    # Print usage summary
    tracker.print_usage_summary()

if __name__ == "__main__":
    test_robust_clients()
