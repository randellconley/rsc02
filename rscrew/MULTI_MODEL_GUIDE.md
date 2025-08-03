# RSCrew Multi-Model Management System

## Overview

RSCrew now supports **4 LLM providers** with intelligent load balancing, fallback logic, and centralized management:

- **Claude (Anthropic)** - Premium reasoning and strategic planning
- **OpenAI GPT-4** - General purpose and communication
- **Gemini (Google)** - Information processing and analysis  
- **DeepSeek** - Cost-effective coding and technical tasks

## Quick Start

### 1. Setup API Keys

Add your API keys to `.env` file:

```bash
# Required - Already configured
ANTHROPIC_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key

# Add these for full multi-model support
OPENAI_API_KEY=your_openai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
```

### 2. Check System Status

```bash
python model_manager_cli.py status
```

**Status Indicators:**
- 🔑 = API key found in environment
- ✅ = API is functional and responding
- ❌ = API key missing or API not responding
- ⏭️ = Skipped (no API key to test)

The status command automatically tests API connectivity for all providers.

### 3. View Available Providers

```bash
python model_manager_cli.py providers
```

## Model Management CLI

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Show current assignments and provider status | `python model_manager_cli.py status` |
| `providers` | List all available providers | `python model_manager_cli.py providers` |
| `agents` | List all available agents | `python model_manager_cli.py agents` |
| `assign` | Assign a model to an agent | `python model_manager_cli.py assign code_implementer deepseek --reasoning "Best for coding"` |
| `bulk` | Bulk assign using strategies | `python model_manager_cli.py bulk` |

### Assignment Examples

```bash
# Assign DeepSeek to code implementer (cost-effective coding)
python model_manager_cli.py assign code_implementer deepseek --reasoning "Cost-effective coding specialist"

# Assign OpenAI to technical writer (strong communication)
python model_manager_cli.py assign technical_writer openai --reasoning "Excellent documentation skills"

# Assign Claude to solution architect (premium reasoning)
python model_manager_cli.py assign solution_architect claude --reasoning "Complex architectural decisions"
```

## Current Agent Distribution

### Claude (Premium Reasoning) - 4 agents
- **project_orchestrator** - Strategic planning and coordination
- **solution_architect** - Complex architectural decisions
- **security_architecture_specialist** - Security analysis and design
- **plan_update_coordinator** - Plan synthesis and updates

### OpenAI (General Purpose) - 3 agents  
- **quality_assurance** - Testing strategy and validation
- **technical_writer** - Documentation and communication
- **frontend_architecture_specialist** - UI/UX and frontend patterns

### Gemini (Information Processing) - 3 agents
- **operator_intent_interpreter** - Request analysis and interpretation
- **research_analyst** - Information gathering and research
- **feature_analyst** - Feature analysis and requirements

### DeepSeek (Cost-Effective Technical) - 3 agents
- **code_implementer** - Code generation and implementation
- **database_architecture_specialist** - Database design and optimization
- **infrastructure_specialist** - DevOps and infrastructure automation

## Configuration Files

### Model Configuration (`src/rscrew/config/model_config.yaml`)

This file controls all model assignments and settings:

```yaml
# Global settings
global_settings:
  rate_limiting:
    enabled: true
    min_interval: 0.5
  fallback_enabled: true

# Provider definitions
providers:
  claude:
    model: "claude-3-5-sonnet-20241022"
    api_key_env: "ANTHROPIC_API_KEY"
    cost_tier: "premium"
  # ... other providers

# Agent assignments with fallback chain
agent_assignments:
  project_orchestrator:
    primary: "claude"      # First choice
    secondary: "openai"    # If primary fails
    tertiary: "gemini"     # If secondary fails  
    fallback: "deepseek"   # Last resort
    reasoning: "Strategic planning requires top-tier reasoning"
```

## Smart Routing Features

### 1. Priority-Based Fallback
Each agent has a priority chain: Primary → Secondary → Tertiary → Fallback

### 2. Rate Limiting
- 500ms intervals between API calls
- Prevents rate limit errors
- Configurable per environment

### 3. Cost Optimization
- Budget models for appropriate tasks
- Premium models for complex reasoning
- Automatic load balancing

### 4. Provider Health Monitoring
- Automatic fallback on API failures
- Real-time provider status checking
- Debug logging for troubleshooting

## Load Balancing Strategies

### Current Strategy: Task-Optimized
- **Claude**: Complex reasoning, strategic planning, security
- **OpenAI**: Communication, testing, frontend design
- **Gemini**: Information processing, analysis, research
- **DeepSeek**: Code generation, database design, infrastructure

### Alternative Strategies

#### Cost-Optimized
```bash
python model_manager_cli.py bulk
# Choose option 1: Cost-optimized
```

#### Performance-Optimized  
```bash
python model_manager_cli.py bulk
# Choose option 2: Performance-optimized
```

## Monitoring and Debugging

### Enable Debug Mode
```bash
export RSCREW_DEBUG=true
```

### Debug Output Example
```
[DEBUG] === Creating LLM for code_implementer ===
[DEBUG] Provider priority: deepseek -> claude -> openai -> gemini
[DEBUG] ✅ DEEPSEEK LLM created: deepseek-chat
[DEBUG] Reasoning: DeepSeek excels at code generation
```

### Check Provider Stats
```python
from src.rscrew.model_manager import get_model_manager

manager = get_model_manager()
stats = manager.get_provider_stats()
print(f"Available: {stats['available_providers']}")
print(f"Distribution: {stats['provider_distribution']}")
```

## Cost Management

### Cost Tiers
- **Premium**: Claude, OpenAI GPT-4 (high cost, best quality)
- **Standard**: Gemini (moderate cost, good quality)
- **Budget**: DeepSeek (low cost, specialized for coding)

### Cost Optimization Tips
1. Use DeepSeek for coding tasks
2. Use Gemini for information processing
3. Reserve Claude/OpenAI for complex reasoning
4. Monitor usage with `python model_manager_cli.py status`

## Troubleshooting

### Common Issues

#### API Key Not Found
```bash
# Check environment variables
python model_manager_cli.py providers
# Look for ❌ next to provider names
```

#### Model Assignment Not Working
```bash
# Verify configuration
python model_manager_cli.py status

# Check specific agent
python model_manager_cli.py assign agent_name provider_name
```

#### Rate Limiting Issues
```bash
# Increase interval in config
# Edit src/rscrew/config/model_config.yaml
global_settings:
  rate_limiting:
    min_interval: 1.0  # Increase from 0.5
```

## Advanced Usage

### Custom Provider Configuration

Edit `src/rscrew/config/model_config.yaml` to add new providers or modify existing ones:

```yaml
providers:
  custom_provider:
    model: "custom-model-name"
    api_key_env: "CUSTOM_API_KEY"
    description: "Custom provider description"
    cost_tier: "custom"
```

### Programmatic Management

```python
from src.rscrew.model_manager import get_model_manager

manager = get_model_manager()

# Update agent assignment
manager.update_agent_assignment(
    agent_name="custom_agent",
    primary="claude",
    secondary="openai",
    reasoning="Custom reasoning"
)

# Get LLM for agent
llm = manager.get_llm_for_agent("project_orchestrator")
```

## Migration from Previous System

The new system is **backward compatible**. Old LLM creation functions still work but now route through the centralized system:

```python
# Old way (still works)
llm = create_claude_llm_with_monitoring("agent_name")

# New way (recommended)
llm = create_llm_with_smart_routing("agent_name")
```

## Performance Benefits

### Before (2 providers)
- Claude: 5 agents (38%)
- Gemini: 8 agents (62%)
- Limited fallback options
- Manual load balancing

### After (4 providers)
- Claude: 4 agents (31%)
- OpenAI: 3 agents (23%)
- Gemini: 3 agents (23%)
- DeepSeek: 3 agents (23%)
- Intelligent fallback chains
- Automatic load balancing
- Cost optimization
- Easy management

## Next Steps

1. **Add your OpenAI and DeepSeek API keys** to `.env`
2. **Test the system**: `python model_manager_cli.py status`
3. **Customize assignments** based on your preferences
4. **Monitor performance** and adjust as needed
5. **Use bulk assignment** for quick strategy changes

## Support

For issues or questions:
1. Check debug logs: `export RSCREW_DEBUG=true`
2. Verify API keys: `python model_manager_cli.py providers`
3. Check configuration: `python model_manager_cli.py status`
4. Review this guide for troubleshooting tips