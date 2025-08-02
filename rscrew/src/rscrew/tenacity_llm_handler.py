"""
Tenacity-based LLM Error Handler for RSCrew

Combines Tenacity's robust retry mechanisms with RSCrew-specific
LLM error handling and context-aware fallbacks.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union
from functools import wraps

try:
    from tenacity import (
        retry, stop_after_attempt, wait_exponential, 
        retry_if_exception_type, before_sleep_log,
        RetryError, Retrying
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    print("⚠️  Tenacity not installed. Install with: pip install tenacity")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TenacityLLMHandler:
    """Enhanced LLM error handler using Tenacity for robust retries"""
    
    def __init__(self):
        self.debug_mode = os.getenv('RSCREW_DEBUG', 'true').lower() == 'true'
        self.max_retries = int(os.getenv('RSCREW_LLM_MAX_RETRIES', '3'))
        self.base_delay = float(os.getenv('RSCREW_LLM_BASE_DELAY', '1.0'))
        self.max_delay = float(os.getenv('RSCREW_LLM_MAX_DELAY', '60.0'))
        self.fallback_enabled = os.getenv('RSCREW_LLM_FALLBACK', 'true').lower() == 'true'
    
    def debug_print(self, message: str):
        """Print debug message if debug mode is enabled"""
        if self.debug_mode:
            logger.info(f"[TENACITY_LLM_HANDLER] {message}")
    
    def is_llm_error(self, exception: Exception) -> bool:
        """Check if exception is an LLM-related error worth retrying"""
        error_str = str(exception).lower()
        
        # LLM-specific error patterns
        llm_error_patterns = [
            'invalid response from llm call',
            'none or empty',
            'rate limit',
            'timeout',
            'connection',
            'network',
            'service unavailable',
            'internal server error',
            'bad gateway',
            'gateway timeout',
            'too many requests',
            'openai',
            'anthropic',
            'api error'
        ]
        
        return any(pattern in error_str for pattern in llm_error_patterns)
    
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

def create_tenacity_llm_retry():
    """Create a Tenacity retry decorator configured for LLM calls"""
    if not TENACITY_AVAILABLE:
        raise ImportError("Tenacity is required. Install with: pip install tenacity")
    
    handler = TenacityLLMHandler()
    
    return retry(
        # Stop after max attempts
        stop=stop_after_attempt(handler.max_retries),
        
        # Exponential backoff with jitter
        wait=wait_exponential(
            multiplier=handler.base_delay,
            min=handler.base_delay,
            max=handler.max_delay
        ),
        
        # Only retry on LLM-related errors
        retry=retry_if_exception_type((
            ValueError,  # "Invalid response from LLM call"
            ConnectionError,
            TimeoutError,
            Exception  # Catch-all for API errors
        )),
        
        # Log before each retry
        before_sleep=before_sleep_log(logger, logging.INFO),
        
        # Re-raise the last exception if all retries fail
        reraise=True
    )

def with_tenacity_llm_error_handling(fallback_enabled: bool = True):
    """Decorator that combines Tenacity retries with RSCrew fallback responses"""
    
    def decorator(func):
        if not TENACITY_AVAILABLE:
            # Fallback to basic error handling if Tenacity not available
            return func
        
        handler = TenacityLLMHandler()
        tenacity_retry = create_tenacity_llm_retry()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Apply Tenacity retry logic
                @tenacity_retry
                def _retry_func():
                    result = func(*args, **kwargs)
                    
                    # Validate the response
                    if not handler.validate_llm_response(result):
                        raise ValueError("Invalid response from LLM call - None or empty.")
                    
                    return result
                
                return _retry_func()
                
            except RetryError as e:
                # All retries failed
                handler.debug_print(f"All retries failed: {e}")
                
                if fallback_enabled and handler.fallback_enabled:
                    # Provide fallback response
                    context = str(kwargs.get('messages', '')) if 'messages' in kwargs else str(args)
                    fallback = handler.get_fallback_response(context)
                    handler.debug_print("Using fallback response due to persistent LLM errors")
                    return fallback
                else:
                    # Re-raise the original error
                    raise e.last_attempt.exception()
            
            except Exception as e:
                # Non-retry error, handle directly
                if fallback_enabled and handler.fallback_enabled and handler.is_llm_error(e):
                    context = str(kwargs.get('messages', '')) if 'messages' in kwargs else str(args)
                    return handler.get_fallback_response(context)
                else:
                    raise e
        
        return wrapper
    return decorator

class TenacityLLMWrapper:
    """Wrapper class for LLM instances using Tenacity for retries"""
    
    def __init__(self, llm_instance, fallback_enabled: bool = True):
        self.llm = llm_instance
        self.fallback_enabled = fallback_enabled
        self.handler = TenacityLLMHandler()
    
    def __getattr__(self, name):
        """Delegate attribute access to the wrapped LLM instance"""
        attr = getattr(self.llm, name)
        
        # If it's a callable method that might make LLM calls, wrap it
        if callable(attr) and name in ['call', 'invoke', 'generate', 'predict', 'run']:
            return with_tenacity_llm_error_handling(
                fallback_enabled=self.fallback_enabled
            )(attr)
        
        return attr
    
    def call(self, *args, **kwargs):
        """Wrapped call method with Tenacity error handling"""
        return with_tenacity_llm_error_handling(
            fallback_enabled=self.fallback_enabled
        )(self.llm.call)(*args, **kwargs)

def create_tenacity_robust_llm(llm_instance, fallback_enabled: bool = True):
    """Factory function to create a Tenacity-based robust LLM wrapper"""
    if not TENACITY_AVAILABLE:
        logger.warning("Tenacity not available, falling back to basic error handling")
        # Could fallback to the original implementation here
        from rscrew.llm_error_handler import create_robust_llm
        return create_robust_llm(llm_instance, fallback_enabled=fallback_enabled)
    
    return TenacityLLMWrapper(llm_instance, fallback_enabled)

def apply_tenacity_error_handling_to_agents(agents: List[Any]) -> List[Any]:
    """Apply Tenacity-based error handling to all agents in a list"""
    for agent in agents:
        if hasattr(agent, 'llm') and agent.llm is not None:
            logger.info(f"Applying Tenacity LLM error handling to agent: {getattr(agent, 'role', 'unknown')}")
            agent.llm = create_tenacity_robust_llm(agent.llm, fallback_enabled=True)
    
    return agents

# Installation check and recommendation
def check_tenacity_installation():
    """Check if Tenacity is installed and provide installation instructions"""
    if TENACITY_AVAILABLE:
        logger.info("✅ Tenacity is available - using advanced retry mechanisms")
        return True
    else:
        logger.warning("""
⚠️  Tenacity not installed. For better LLM error handling, install with:

    pip install tenacity

Benefits of Tenacity:
- More robust retry strategies
- Better async support  
- Advanced stop conditions
- Retry statistics and callbacks
- Battle-tested reliability

Falling back to basic error handling for now.
        """)
        return False

# Environment variable documentation
"""
Environment Variables for Tenacity LLM Error Handling:

RSCREW_LLM_MAX_RETRIES: Maximum number of retry attempts (default: 3)
RSCREW_LLM_FALLBACK: Enable fallback responses (default: true)  
RSCREW_LLM_BASE_DELAY: Base delay for exponential backoff in seconds (default: 1.0)
RSCREW_LLM_MAX_DELAY: Maximum delay for exponential backoff in seconds (default: 60.0)
RSCREW_DEBUG: Enable debug logging (default: true)

Installation:
pip install tenacity

Example usage:
@with_tenacity_llm_error_handling(fallback_enabled=True)
def my_llm_call(messages):
    return llm.call(messages)
"""