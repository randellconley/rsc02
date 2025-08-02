# Debug Configuration

## Debug Toggle

The project includes comprehensive debug logging that can be toggled on/off using the `RSCREW_DEBUG` environment variable.

### Enable Debug Mode (default)
```bash
export RSCREW_DEBUG=true
# or
RSCREW_DEBUG=true rc "your command"
```

### Disable Debug Mode
```bash
export RSCREW_DEBUG=false
# or
RSCREW_DEBUG=false rc "your command"
```

## Debug Output Includes

1. **Environment Check**: API key availability and length
2. **Agent Creation**: LLM configuration, provider, class type
3. **LLM Testing**: Direct LLM call test during agent creation
4. **Task Creation**: Agent assignment verification
5. **Crew Creation**: Agent and task counts, LLM assignments
6. **CrewAI Internal Logging**: Full debug logging from CrewAI framework

## Troubleshooting the "None or empty response" Error

The debug output will help identify:
- Whether Claude LLM is properly configured
- If API key is available during execution
- What model/provider is actually being used
- If LLM calls work in isolation
- Where in the execution chain the failure occurs

## Example Debug Output

```
[DEBUG] Debug mode enabled
[DEBUG] === Environment Check ===
[DEBUG] ANTHROPIC_API_KEY exists: True
[DEBUG] ANTHROPIC_API_KEY length: 108
[DEBUG] ==========================
[DEBUG] === Creating Researcher Agent ===
[DEBUG] API Key available: True
[DEBUG] API Key length: 108
[DEBUG] LLM created successfully: claude-3-5-sonnet-20241022
[DEBUG] LLM provider: anthropic
[DEBUG] LLM class: LLM
[DEBUG] Testing LLM with simple call...
[DEBUG] LLM test response: test successful
[DEBUG] Researcher LLM: claude-3-5-sonnet-20241022
[DEBUG] ===================================
[DEBUG] Agent created with LLM: <crewai.llm.LLM object>
```