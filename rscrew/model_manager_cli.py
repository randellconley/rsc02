#!/usr/bin/env python3
"""
Model Manager CLI - Easy management of LLM assignments for RSCrew agents
Usage: python model_manager_cli.py [command] [options]
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rscrew.model_manager import get_model_manager

def load_config(config_path: str = "src/rscrew/config/model_config.yaml") -> Dict[str, Any]:
    """Load model configuration"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return {}
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return {}

def save_config(config: Dict[str, Any], config_path: str = "src/rscrew/config/model_config.yaml") -> bool:
    """Save model configuration"""
    try:
        # Ensure directory exists
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Configuration saved to {config_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def test_provider_connectivity(provider: str, config: Dict[str, Any]) -> tuple[bool, str]:
    """Test if a provider is actually reachable and functional"""
    try:
        provider_config = config.get('providers', {}).get(provider, {})
        api_key_env = provider_config.get('api_key_env', '')
        api_key = os.getenv(api_key_env)
        
        if not api_key:
            return False, "API key not found"
        
        # Import here to avoid circular imports
        from crewai import LLM
        
        # Create a minimal LLM instance to test connectivity
        model = provider_config.get('model', '')
        llm = LLM(model=model, api_key=api_key)
        
        # Try a minimal call to test connectivity
        # This is a very short prompt to minimize cost
        test_result = llm.call("Hi")
        
        if test_result and len(str(test_result).strip()) > 0:
            return True, "Operational"
        else:
            return False, "No response"
            
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "authentication" in error_msg:
            return False, "Invalid API key"
        elif "rate limit" in error_msg:
            return False, "Rate limited"
        elif "network" in error_msg or "connection" in error_msg:
            return False, "Network error"
        else:
            return False, f"Error: {str(e)[:50]}..."

def show_status():
    """Show current model assignments and provider status with connectivity testing"""
    print("🚀 RSCrew Multi-Model Status")
    print("=" * 50)
    
    try:
        manager = get_model_manager()
        stats = manager.get_provider_stats()
        
        print(f"\n📊 Provider Status:")
        print("🧪 Testing API connectivity...")
        config = load_config()
        
        for provider in ['claude', 'gemini', 'openai', 'deepseek']:
            api_key_env = config.get('providers', {}).get(provider, {}).get('api_key_env', '')
            has_key = "🔑" if os.getenv(api_key_env) else "❌"
            
            if os.getenv(api_key_env):
                is_functional, status_msg = test_provider_connectivity(provider, config)
                status_icon = "✅" if is_functional else "❌"
                print(f"  {provider.upper()}: {has_key} {status_icon} {status_msg}")
            else:
                print(f"  {provider.upper()}: {has_key} ⏭️  Skipped (no API key)")
        
        print(f"\n📈 Load Distribution:")
        for provider, count in stats['provider_distribution'].items():
            percentage = (count / stats['total_agents'] * 100) if stats['total_agents'] > 0 else 0
            print(f"  {provider.upper()}: {count} agents ({percentage:.1f}%)")
        
        print(f"\n🤖 Agent Assignments:")
        config = load_config()
        assignments = config.get('agent_assignments', {})
        
        for agent, assignment in assignments.items():
            primary = assignment.get('primary', 'unknown')
            secondary = assignment.get('secondary', 'unknown')
            reasoning = assignment.get('reasoning', 'No reasoning provided')
            print(f"  {agent}: {primary.upper()} → {secondary.upper()}")
            print(f"    Reasoning: {reasoning}")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")

def list_agents():
    """List all available agents"""
    print("🤖 Available Agents")
    print("=" * 30)
    
    config = load_config()
    assignments = config.get('agent_assignments', {})
    
    for i, agent in enumerate(assignments.keys(), 1):
        assignment = assignments[agent]
        primary = assignment.get('primary', 'unknown')
        print(f"{i:2d}. {agent} (Primary: {primary.upper()})")

def list_providers():
    """List all available providers"""
    print("🔧 Available Providers")
    print("=" * 30)
    
    config = load_config()
    providers = config.get('providers', {})
    
    for provider, details in providers.items():
        model = details.get('model', 'unknown')
        description = details.get('description', 'No description')
        cost_tier = details.get('cost_tier', 'unknown')
        api_key_env = details.get('api_key_env', '')
        
        # Check if API key is available
        key_status = "✅" if os.getenv(api_key_env) else "❌"
        
        print(f"\n{provider.upper()} {key_status}")
        print(f"  Model: {model}")
        print(f"  Cost Tier: {cost_tier}")
        print(f"  Description: {description}")

def assign_model(agent_name: str, primary: str, secondary: str = None, reasoning: str = None):
    """Assign a model to an agent"""
    config = load_config()
    
    if 'agent_assignments' not in config:
        config['agent_assignments'] = {}
    
    # Validate provider exists
    providers = config.get('providers', {})
    if primary not in providers:
        print(f"❌ Unknown provider: {primary}")
        print(f"Available providers: {', '.join(providers.keys())}")
        return False
    
    # Create assignment
    assignment = {
        'primary': primary,
        'secondary': secondary or 'claude',
        'tertiary': 'openai',
        'fallback': 'gemini'
    }
    
    if reasoning:
        assignment['reasoning'] = reasoning
    
    config['agent_assignments'][agent_name] = assignment
    
    if save_config(config):
        print(f"✅ Assigned {primary.upper()} to {agent_name}")
        if reasoning:
            print(f"   Reasoning: {reasoning}")
        return True
    
    return False

def bulk_assign():
    """Interactive bulk assignment of models"""
    print("🔄 Bulk Model Assignment")
    print("=" * 30)
    
    config = load_config()
    providers = list(config.get('providers', {}).keys())
    agents = list(config.get('agent_assignments', {}).keys())
    
    print(f"Available providers: {', '.join(providers)}")
    print(f"Available agents: {len(agents)}")
    
    strategy = input("\nChoose strategy:\n1. Cost-optimized (prefer budget models)\n2. Performance-optimized (prefer premium models)\n3. Balanced\n4. Custom\nChoice (1-4): ")
    
    if strategy == "1":  # Cost-optimized
        assignments = {
            'primary_coding': 'deepseek',
            'primary_reasoning': 'claude', 
            'primary_analysis': 'gemini',
            'primary_communication': 'openai'
        }
    elif strategy == "2":  # Performance-optimized
        assignments = {
            'primary_coding': 'claude',
            'primary_reasoning': 'claude',
            'primary_analysis': 'openai', 
            'primary_communication': 'openai'
        }
    elif strategy == "3":  # Balanced
        assignments = {
            'primary_coding': 'deepseek',
            'primary_reasoning': 'claude',
            'primary_analysis': 'gemini',
            'primary_communication': 'openai'
        }
    else:  # Custom
        print("Custom assignment not implemented yet. Use individual assign commands.")
        return
    
    # Apply assignments based on agent type
    coding_agents = ['code_implementer', 'database_architecture_specialist', 'infrastructure_specialist']
    reasoning_agents = ['project_orchestrator', 'solution_architect', 'security_architecture_specialist']
    analysis_agents = ['research_analyst', 'feature_analyst', 'operator_intent_interpreter']
    communication_agents = ['technical_writer', 'quality_assurance', 'frontend_architecture_specialist', 'plan_update_coordinator']
    
    updates = 0
    for agent in agents:
        if agent in coding_agents:
            primary = assignments['primary_coding']
        elif agent in reasoning_agents:
            primary = assignments['primary_reasoning']
        elif agent in analysis_agents:
            primary = assignments['primary_analysis']
        elif agent in communication_agents:
            primary = assignments['primary_communication']
        else:
            primary = 'claude'  # Default
        
        if assign_model(agent, primary, reasoning=f"Bulk assignment - {strategy} strategy"):
            updates += 1
    
    print(f"\n✅ Updated {updates} agent assignments")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="RSCrew Model Manager CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show current model assignments and provider status with connectivity testing')
    
    # List commands
    subparsers.add_parser('agents', help='List all available agents')
    subparsers.add_parser('providers', help='List all available providers')
    
    # Assign command
    assign_parser = subparsers.add_parser('assign', help='Assign a model to an agent')
    assign_parser.add_argument('agent', help='Agent name')
    assign_parser.add_argument('primary', help='Primary provider')
    assign_parser.add_argument('--secondary', help='Secondary provider')
    assign_parser.add_argument('--reasoning', help='Reasoning for assignment')
    
    # Bulk assign command
    subparsers.add_parser('bulk', help='Bulk assign models using predefined strategies')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'status':
        show_status()
    elif args.command == 'agents':
        list_agents()
    elif args.command == 'providers':
        list_providers()
    elif args.command == 'assign':
        assign_model(args.agent, args.primary, args.secondary, args.reasoning)
    elif args.command == 'bulk':
        bulk_assign()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()