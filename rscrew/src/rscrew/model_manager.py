"""
Centralized Model Management System for RSCrew
Handles multi-provider LLM creation, fallback logic, and load balancing
"""

import os
import time
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from crewai import LLM

# Global rate limiting variables
_last_call_time = 0
_min_call_interval = 0.5

def debug_print(message: str) -> None:
    """Print debug messages if debug mode is enabled"""
    if os.getenv('RSCREW_DEBUG', 'false').lower() == 'true':
        print(f"[DEBUG] {message}")

def apply_rate_limiting() -> None:
    """Apply rate limiting between LLM calls"""
    global _last_call_time, _min_call_interval
    
    current_time = time.time()
    time_since_last_call = current_time - _last_call_time
    
    if time_since_last_call < _min_call_interval:
        sleep_time = _min_call_interval - time_since_last_call
        debug_print(f"Rate limiting: sleeping for {sleep_time:.3f}s")
        time.sleep(sleep_time)
    
    _last_call_time = time.time()

class ModelManager:
    """Centralized model management system"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv('RSCREW_MODEL_CONFIG_PATH', 'src/rscrew/config/model_config.yaml')
        self.config = self._load_config()
        self._validate_config()
        self._setup_rate_limiting()
        
        debug_print("=== Model Manager Initialized ===")
        debug_print(f"Config loaded from: {self.config_path}")
        debug_print(f"Available providers: {list(self.config['providers'].keys())}")
        debug_print(f"Rate limiting: {self.config['global_settings']['rate_limiting']['enabled']}")
        debug_print("=================================")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                debug_print(f"Config file not found: {self.config_path}, using defaults")
                return self._get_default_config()
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            debug_print(f"Model config loaded successfully from {self.config_path}")
            return config
            
        except Exception as e:
            debug_print(f"Error loading config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if config file is not available"""
        return {
            'global_settings': {
                'rate_limiting': {'enabled': True, 'min_interval': 0.5},
                'fallback_enabled': True,
                'debug_mode': True
            },
            'providers': {
                'claude': {'model': 'claude-3-5-sonnet-20241022', 'api_key_env': 'ANTHROPIC_API_KEY'},
                'gemini': {'model': 'gemini-1.5-pro', 'api_key_env': 'GEMINI_API_KEY'},
                'openai': {'model': 'gpt-4o', 'api_key_env': 'OPENAI_API_KEY'},
                'deepseek': {'model': 'deepseek-chat', 'api_key_env': 'DEEPSEEK_API_KEY'}
            },
            'agent_assignments': {}
        }
    
    def _validate_config(self) -> None:
        """Validate configuration and check API keys"""
        required_sections = ['global_settings', 'providers', 'agent_assignments']
        for section in required_sections:
            if section not in self.config:
                debug_print(f"Warning: Missing config section: {section}")
        
        # Check API keys
        for provider, config in self.config['providers'].items():
            api_key_env = config.get('api_key_env')
            if api_key_env and os.getenv(api_key_env):
                debug_print(f"✅ {provider.upper()} API key found")
            else:
                debug_print(f"⚠️ {provider.upper()} API key not found in environment")
    
    def _setup_rate_limiting(self) -> None:
        """Setup global rate limiting settings"""
        global _min_call_interval
        
        rate_config = self.config.get('global_settings', {}).get('rate_limiting', {})
        if rate_config.get('enabled', True):
            _min_call_interval = rate_config.get('min_interval', 0.5)
            debug_print(f"Rate limiting enabled: {_min_call_interval}s interval")
    
    def _create_llm_for_provider(self, provider: str, agent_name: str) -> Optional[LLM]:
        """Create LLM instance for specific provider"""
        if provider not in self.config['providers']:
            debug_print(f"❌ Unknown provider: {provider}")
            return None
        
        provider_config = self.config['providers'][provider]
        api_key_env = provider_config.get('api_key_env')
        model = provider_config.get('model')
        
        # Check if API key is available
        if not os.getenv(api_key_env):
            debug_print(f"❌ {provider.upper()} API key not found for {agent_name}")
            return None
        
        try:
            # Apply rate limiting
            if self.config.get('global_settings', {}).get('rate_limiting', {}).get('enabled', True):
                apply_rate_limiting()
            
            # Create LLM instance
            llm = LLM(model=model)
            debug_print(f"✅ {provider.upper()} LLM created for {agent_name}: {model}")
            return llm
            
        except Exception as e:
            debug_print(f"❌ Failed to create {provider.upper()} LLM for {agent_name}: {e}")
            return None
    
    def get_llm_for_agent(self, agent_name: str) -> LLM:
        """Get LLM instance for agent with fallback logic"""
        debug_print(f"=== Creating LLM for {agent_name} ===")
        
        # Get agent assignment or use default
        assignment = self.config.get('agent_assignments', {}).get(agent_name, {})
        if not assignment:
            debug_print(f"No specific assignment for {agent_name}, using Claude as default")
            assignment = {'primary': 'claude', 'secondary': 'openai', 'tertiary': 'gemini', 'fallback': 'deepseek'}
        
        # Try providers in priority order
        providers_to_try = [
            assignment.get('primary'),
            assignment.get('secondary'),
            assignment.get('tertiary'),
            assignment.get('fallback')
        ]
        
        # Filter out None values and duplicates
        providers_to_try = list(dict.fromkeys([p for p in providers_to_try if p]))
        
        debug_print(f"Provider priority for {agent_name}: {' -> '.join(providers_to_try)}")
        
        for provider in providers_to_try:
            llm = self._create_llm_for_provider(provider, agent_name)
            if llm:
                reasoning = assignment.get('reasoning', 'No specific reasoning provided')
                debug_print(f"✅ Using {provider.upper()} for {agent_name}")
                debug_print(f"Reasoning: {reasoning}")
                debug_print("=" * 50)
                return llm
        
        # If all providers fail, create a basic Claude LLM as last resort
        debug_print(f"⚠️ All providers failed for {agent_name}, using basic Claude fallback")
        try:
            fallback_llm = LLM(model="claude-3-5-sonnet-20241022")
            debug_print("✅ Fallback Claude LLM created")
            debug_print("=" * 50)
            return fallback_llm
        except Exception as e:
            debug_print(f"❌ Even fallback failed: {e}")
            raise Exception(f"Unable to create LLM for {agent_name}: all providers failed")
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics about provider usage and availability"""
        stats = {
            'available_providers': [],
            'unavailable_providers': [],
            'total_agents': len(self.config.get('agent_assignments', {})),
            'provider_distribution': {}
        }
        
        # Check provider availability
        for provider, config in self.config['providers'].items():
            api_key_env = config.get('api_key_env')
            if os.getenv(api_key_env):
                stats['available_providers'].append(provider)
            else:
                stats['unavailable_providers'].append(provider)
        
        # Count primary assignments
        for agent, assignment in self.config.get('agent_assignments', {}).items():
            primary = assignment.get('primary')
            if primary:
                stats['provider_distribution'][primary] = stats['provider_distribution'].get(primary, 0) + 1
        
        return stats
    
    def update_agent_assignment(self, agent_name: str, primary: str, secondary: str = None, 
                              tertiary: str = None, fallback: str = None, reasoning: str = None) -> bool:
        """Update agent model assignment"""
        try:
            if 'agent_assignments' not in self.config:
                self.config['agent_assignments'] = {}
            
            assignment = {
                'primary': primary,
                'secondary': secondary or 'claude',
                'tertiary': tertiary or 'openai', 
                'fallback': fallback or 'gemini'
            }
            
            if reasoning:
                assignment['reasoning'] = reasoning
            
            self.config['agent_assignments'][agent_name] = assignment
            debug_print(f"Updated assignment for {agent_name}: {primary} -> {secondary} -> {tertiary} -> {fallback}")
            return True
            
        except Exception as e:
            debug_print(f"Failed to update assignment for {agent_name}: {e}")
            return False

# Global model manager instance
_model_manager = None

def get_model_manager() -> ModelManager:
    """Get or create global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

def create_llm_with_smart_routing(agent_name: str) -> LLM:
    """Create LLM with smart routing based on centralized configuration"""
    manager = get_model_manager()
    return manager.get_llm_for_agent(agent_name)

# Legacy compatibility functions
def create_claude_llm_with_monitoring(agent_name: str) -> LLM:
    """Legacy function - now routes through centralized system"""
    debug_print(f"Legacy Claude call for {agent_name} - routing through model manager")
    return create_llm_with_smart_routing(agent_name)

def create_gemini_llm_with_monitoring(agent_name: str) -> LLM:
    """Legacy function - now routes through centralized system"""
    debug_print(f"Legacy Gemini call for {agent_name} - routing through model manager")
    return create_llm_with_smart_routing(agent_name)

def create_openai_llm_with_monitoring(agent_name: str) -> LLM:
    """Create OpenAI LLM with monitoring"""
    debug_print(f"OpenAI LLM call for {agent_name} - routing through model manager")
    return create_llm_with_smart_routing(agent_name)

def create_deepseek_llm_with_monitoring(agent_name: str) -> LLM:
    """Create DeepSeek LLM with monitoring"""
    debug_print(f"DeepSeek LLM call for {agent_name} - routing through model manager")
    return create_llm_with_smart_routing(agent_name)