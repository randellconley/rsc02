# RSCrew Hybrid LLM Error Handling System

## 🎯 Overview

The RSCrew Hybrid LLM Error Handling System combines **Tenacity's robust retry logic** with **RSCrew's context-aware fallbacks** to prevent the common "Invalid response from LLM call - None or empty" errors that can occur due to:

- **API rate limiting**
- **Network connectivity issues** 
- **Temporary service outages**
- **Token limit exceeded**
- **Invalid API configurations**

## ✨ Hybrid Features

### 🔄 **Tenacity Retry Logic**
- ✅ **Battle-tested Reliability**: Production-grade retry mechanisms
- ✅ **Advanced Retry Strategies**: Exponential backoff with jitter
- ✅ **Sophisticated Error Classification**: Recoverable vs permanent errors
- ✅ **Async Support**: Built-in async/await compatibility
- ✅ **Retry Statistics**: Built-in metrics and callbacks

### 🎯 **RSCrew Context-Aware Fallbacks**
- ✅ **Intelligent Fallback Responses**: Context-aware responses when retries fail
- ✅ **Code-specific Fallbacks**: Helpful code templates for programming requests
- ✅ **Research Fallbacks**: Guidance for research and analysis requests
- ✅ **Zero Configuration**: Works out of the box with sensible defaults
- ✅ **Debug Logging**: Detailed logging for troubleshooting
- ✅ **Transparent Integration**: No changes needed to existing code

## 🚀 How It Works

### 1. Automatic Integration
The hybrid error handling is automatically applied to all agents when the crew is created:

```python
# In crew.py - happens automatically
robust_agents = apply_tenacity_error_handling_to_agents(self.agents)
```

### 2. Hybrid Retry Mechanism
When an LLM call fails:
1. **Tenacity Classification**: Determine if error is recoverable using Tenacity's logic
2. **Tenacity Retry**: Use exponential backoff with jitter (1s, 2s, 4s, etc.)
3. **Multiple Attempts**: Tenacity handles sophisticated retry strategies
4. **RSCrew Fallback**: If all retries fail, provide context-aware fallback response

### 3. Fallback Responses
Context-aware fallback responses based on the request type:

| Context Type | Fallback Response |
|--------------|-------------------|
| **Code/Programming** | `# Unable to generate code due to technical issues...` |
| **Research/Analysis** | `I'm currently unable to perform research...` |
| **General Tasks** | `I apologize, but I'm experiencing technical difficulties...` |

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Maximum retry attempts (default: 3)
RSCREW_LLM_MAX_RETRIES=3

# Enable fallback responses (default: true)
RSCREW_LLM_FALLBACK=true

# Base delay for exponential backoff in seconds (default: 1.0)
RSCREW_LLM_BASE_DELAY=1.0

# Maximum delay cap in seconds (default: 60.0)
RSCREW_LLM_MAX_DELAY=60.0

# Enable debug logging (default: true)
RSCREW_DEBUG=true
```

### Configuration Examples

**Conservative (Fewer retries, faster failure)**:
```bash
RSCREW_LLM_MAX_RETRIES=2
RSCREW_LLM_BASE_DELAY=0.5
RSCREW_LLM_MAX_DELAY=30.0
```

**Aggressive (More retries, longer waits)**:
```bash
RSCREW_LLM_MAX_RETRIES=5
RSCREW_LLM_BASE_DELAY=2.0
RSCREW_LLM_MAX_DELAY=120.0
```

**Production (Balanced)**:
```bash
RSCREW_LLM_MAX_RETRIES=3
RSCREW_LLM_FALLBACK=true
RSCREW_LLM_BASE_DELAY=1.0
RSCREW_LLM_MAX_DELAY=60.0
RSCREW_DEBUG=false
```

## 🔧 Advanced Usage

### Manual LLM Wrapping
If you need to wrap LLM instances manually:

```python
from rscrew.llm_error_handler import create_robust_llm

# Wrap any LLM instance
robust_llm = create_robust_llm(
    your_llm_instance,
    max_retries=5,
    fallback_enabled=True
)
```

### Decorator Usage
Apply error handling to individual functions:

```python
from rscrew.llm_error_handler import with_llm_error_handling

@with_llm_error_handling(max_retries=3, fallback_enabled=True)
def my_llm_function(prompt):
    return llm.call(prompt)
```

### Custom Error Handling
Create custom error handlers:

```python
from rscrew.llm_error_handler import LLMErrorHandler

handler = LLMErrorHandler(
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0
)

# Check if error is recoverable
if handler.is_recoverable_error(exception):
    # Implement custom retry logic
    pass
```

## 📊 Error Types

### Recoverable Errors (Will Retry)
- Rate limit exceeded
- Network timeouts
- Connection errors
- Service unavailable (5xx errors)
- Empty/None LLM responses
- Temporary API issues

### Non-Recoverable Errors (Immediate Failure)
- Invalid API keys
- Authentication failures
- Malformed requests
- Quota exceeded (permanent)
- Model not found

## 🐛 Debugging

### Enable Debug Logging
```bash
export RSCREW_DEBUG=true
```

### Debug Output Example
```
[LLM_ERROR_HANDLER] LLM call attempt 1/4
[LLM_ERROR_HANDLER] LLM call failed on attempt 1: Rate limit exceeded
[LLM_ERROR_HANDLER] Waiting 1.00s before retry...
[LLM_ERROR_HANDLER] LLM call attempt 2/4
[LLM_ERROR_HANDLER] LLM call succeeded on attempt 2
```

### Common Issues & Solutions

**Issue**: Still getting LLM errors despite error handling
**Solution**: Check if `RSCREW_LLM_FALLBACK=true` and increase `RSCREW_LLM_MAX_RETRIES`

**Issue**: Too many retry attempts slowing down execution
**Solution**: Reduce `RSCREW_LLM_MAX_RETRIES` or decrease `RSCREW_LLM_BASE_DELAY`

**Issue**: Fallback responses not helpful
**Solution**: The system provides context-aware fallbacks, but you can disable with `RSCREW_LLM_FALLBACK=false`

## 📈 Performance Impact

### Retry Timing
With default settings (3 retries, 1s base delay):
- **Success on 1st attempt**: No delay
- **Success on 2nd attempt**: ~1s delay
- **Success on 3rd attempt**: ~3s delay  
- **Fallback response**: ~7s total delay

### Memory Usage
- **Minimal overhead**: ~1KB per wrapped LLM instance
- **No persistent storage**: All state is ephemeral

## 🔄 Integration Status

The LLM error handling is automatically integrated into:

- ✅ **All RSCrew Agents**: Project Orchestrator, Technical Lead, etc.
- ✅ **RC Command**: Automatic error handling for all RC executions
- ✅ **Interactive Dialogue**: Error handling during Q&A sessions
- ✅ **Task Execution**: Robust task completion with fallbacks

## 📝 Implementation Details

### Files Added
- `src/rscrew/tenacity_llm_handler.py`: Hybrid Tenacity + RSCrew error handling system
- `src/rscrew/llm_error_handler.py`: Original custom error handling (fallback)
- `llm_config.env`: Configuration template
- `LLM_ERROR_HANDLING.md`: This documentation
- `TENACITY_COMPARISON.md`: Comparison between approaches

### Files Modified
- `src/rscrew/crew.py`: Integrated hybrid error handling into crew creation

### Dependencies
- **Tenacity**: Advanced retry library (already installed in RSCrew)
- **Standard Python libraries**: `time`, `logging`, `functools`
- **Fallback**: Custom error handler if Tenacity unavailable

## 🎯 Hybrid Benefits

1. **Best-in-Class Reliability**: Tenacity's battle-tested retry logic + RSCrew's intelligent fallbacks
2. **Superior User Experience**: Meaningful responses instead of crashes or generic errors
3. **Production-Ready**: Tenacity's robustness with RSCrew's domain-specific intelligence
4. **Advanced Debugging**: Tenacity's detailed retry logs + RSCrew's context-aware logging
5. **Future-Proof**: Tenacity's active development + RSCrew's specialized LLM handling
6. **Zero Configuration**: Works out of the box with intelligent defaults
7. **Graceful Degradation**: Always provides useful responses, even during outages

---

*This LLM error handling system was implemented to address the "Invalid response from LLM call - None or empty" errors identified in the RSCrew system, providing robust error recovery and improved reliability.*