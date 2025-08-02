"""
LLM Error Handler for RSCrew

Provides robust error handling and retry mechanisms for LLM calls to prevent
"Invalid response from LLM call - None or empty" errors.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMErrorHandler:
    """Handles LLM errors with retry logic and fallback strategies"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.debug_mode = os.getenv('RSCREW_DEBUG', 'true').lower() == 'true'
    
    def debug_print(self, message: str):
        """Print debug message if debug mode is enabled"""
        if self.debug_mode:
            logger.info(f"[LLM_ERROR_HANDLER] {message}")
    
    def exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay
    
    def is_recoverable_error(self, error: Exception) -> bool:
        """Determine if an error is recoverable and worth retrying"""
        error_str = str(error).lower()
        
        # Recoverable errors (network, rate limiting, temporary issues)
        recoverable_patterns = [
            'rate limit',
            'timeout',
            'connection',
            'network',
            'temporary',
            'service unavailable',
            'internal server error',
            'bad gateway',
            'gateway timeout',
            'too many requests',
            'invalid response from llm call - none or empty'
        ]
        
        return any(pattern in error_str for pattern in recoverable_patterns)
    
    def validate_llm_response(self, response: Any) -> bool:
        """Validate that LLM response is not None or empty"""
        if response is None:
            return False
        
        if isinstance(response, str) and response.strip() == "":
            return False
        
        if hasattr(response, 'content') and (response.content is None or response.content.strip() == ""):
            return False
        
        return True
    
    def get_fallback_response(self, context: str = "") -> str:
        """Generate a fallback response when LLM fails"""
        fallback_responses = {
            "analysis": "I apologize, but I'm experiencing technical difficulties with the AI analysis. Please try again in a moment, or provide more specific details about what you need help with.",
            "code": "# Unable to generate code due to technical issues\n# Please try again or provide more specific requirements",
            "research": "I'm currently unable to perform the research due to technical difficulties. Please try again shortly or break down your request into smaller parts.",
            "default": "I apologize, but I'm experiencing technical difficulties and cannot provide a complete response right now. Please try again in a moment."
        }
        
        # Try to determine context type
        context_lower = context.lower()
        if any(word in context_lower for word in ['code', 'script', 'function', 'class']):
            return fallback_responses["code"]
        elif any(word in context_lower for word in ['research', 'find', 'search', 'investigate']):
            return fallback_responses["research"]
        elif any(word in context_lower for word in ['analyze', 'analysis', 'examine']):
            return fallback_responses["analysis"]
        else:
            return fallback_responses["default"]

def with_llm_error_handling(max_retries: int = 3, fallback_enabled: bool = True):
    """Decorator to add error handling and retry logic to LLM calls"""
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = LLMErrorHandler(max_retries=max_retries)
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    handler.debug_print(f"LLM call attempt {attempt + 1}/{max_retries + 1}")
                    
                    # Call the original function
                    result = func(*args, **kwargs)
                    
                    # Validate the response
                    if handler.validate_llm_response(result):
                        if attempt > 0:
                            handler.debug_print(f"LLM call succeeded on attempt {attempt + 1}")
                        return result
                    else:
                        raise ValueError("Invalid response from LLM call - None or empty.")
                
                except Exception as e:
                    last_error = e
                    handler.debug_print(f"LLM call failed on attempt {attempt + 1}: {str(e)}")
                    
                    # If this is the last attempt, handle the error
                    if attempt == max_retries:
                        if fallback_enabled and handler.is_recoverable_error(e):
                            handler.debug_print("Using fallback response due to persistent LLM errors")
                            context = str(kwargs.get('messages', '')) if 'messages' in kwargs else str(args)
                            return handler.get_fallback_response(context)
                        else:
                            # Re-raise the original error
                            raise e
                    
                    # If the error is recoverable, wait and retry
                    if handler.is_recoverable_error(e):
                        delay = handler.exponential_backoff(attempt)
                        handler.debug_print(f"Waiting {delay:.2f}s before retry...")
                        time.sleep(delay)
                    else:
                        # Non-recoverable error, don't retry
                        raise e
            
            # This should never be reached, but just in case
            if last_error:
                raise last_error
            
        return wrapper
    return decorator

class RobustLLMWrapper:
    """Wrapper class for LLM instances with built-in error handling"""
    
    def __init__(self, llm_instance, max_retries: int = 3, fallback_enabled: bool = True):
        self.llm = llm_instance
        self.handler = LLMErrorHandler(max_retries=max_retries)
        self.fallback_enabled = fallback_enabled
        self.max_retries = max_retries
    
    def __getattr__(self, name):
        """Delegate attribute access to the wrapped LLM instance"""
        attr = getattr(self.llm, name)
        
        # If it's a callable method that might make LLM calls, wrap it
        if callable(attr) and name in ['call', 'invoke', 'generate', 'predict', 'run']:
            return with_llm_error_handling(
                max_retries=self.max_retries,
                fallback_enabled=self.fallback_enabled
            )(attr)
        
        return attr
    
    def call(self, *args, **kwargs):
        """Wrapped call method with error handling"""
        return with_llm_error_handling(
            max_retries=self.max_retries,
            fallback_enabled=self.fallback_enabled
        )(self.llm.call)(*args, **kwargs)

def create_robust_llm(llm_instance, max_retries: int = 3, fallback_enabled: bool = True):
    """Factory function to create a robust LLM wrapper"""
    return RobustLLMWrapper(llm_instance, max_retries, fallback_enabled)

# Configuration helpers
def get_llm_config():
    """Get LLM configuration from environment variables"""
    config = {
        'max_retries': int(os.getenv('RSCREW_LLM_MAX_RETRIES', '3')),
        'fallback_enabled': os.getenv('RSCREW_LLM_FALLBACK', 'true').lower() == 'true',
        'base_delay': float(os.getenv('RSCREW_LLM_BASE_DELAY', '1.0')),
        'max_delay': float(os.getenv('RSCREW_LLM_MAX_DELAY', '60.0')),
    }
    return config

def apply_error_handling_to_agents(agents: List[Any]) -> List[Any]:
    """Apply error handling to all agents in a list"""
    config = get_llm_config()
    
    for agent in agents:
        if hasattr(agent, 'llm') and agent.llm is not None:
            logger.info(f"Applying LLM error handling to agent: {getattr(agent, 'role', 'unknown')}")
            agent.llm = create_robust_llm(
                agent.llm,
                max_retries=config['max_retries'],
                fallback_enabled=config['fallback_enabled']
            )
    
    return agents

# Environment variable documentation
"""
Environment Variables for LLM Error Handling:

RSCREW_LLM_MAX_RETRIES: Maximum number of retry attempts (default: 3)
RSCREW_LLM_FALLBACK: Enable fallback responses (default: true)
RSCREW_LLM_BASE_DELAY: Base delay for exponential backoff in seconds (default: 1.0)
RSCREW_LLM_MAX_DELAY: Maximum delay for exponential backoff in seconds (default: 60.0)
RSCREW_DEBUG: Enable debug logging (default: true)

Example:
export RSCREW_LLM_MAX_RETRIES=5
export RSCREW_LLM_FALLBACK=true
export RSCREW_LLM_BASE_DELAY=2.0
export RSCREW_LLM_MAX_DELAY=120.0
"""