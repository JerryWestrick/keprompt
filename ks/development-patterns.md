# KePrompt Development Patterns

## Integration Patterns

### Subprocess Integration (Recommended)
```python
import subprocess
import json

def call_keprompt(prompt_name, **params):
    cmd = ['keprompt', '-e', prompt_name]
    for key, value in params.items():
        cmd.extend(['--param', key, str(value)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"KePrompt error: {result.stderr}")
    return result.stdout.strip()

# Usage
response = call_keprompt('customer_support', 
                        message="I need help", 
                        user_id="123")
```

### Error Handling Pattern
```python
def safe_keprompt_call(prompt_name, **params):
    try:
        return call_keprompt(prompt_name, **params)
    except subprocess.TimeoutExpired:
        # Handle timeout (long-running AI calls)
        return "Request timed out, please try again"
    except Exception as e:
        # Log error and return fallback
        logger.error(f"KePrompt failed: {e}")
        return "Service temporarily unavailable"
```

### Async Integration Pattern
```python
import asyncio

async def async_keprompt_call(prompt_name, **params):
    cmd = ['keprompt', '-e', prompt_name]
    for key, value in params.items():
        cmd.extend(['--param', key, str(value)])
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"KePrompt error: {stderr.decode()}")
    return stdout.decode().strip()
```

## Prompt Development Patterns

### Basic Prompt Structure
```
.# Prompt description and purpose
.llm {"model": "gpt-4o-mini", "temperature": 0.3}
.system You are a helpful assistant specialized in [domain].

Context: <<context>>
User request: <<user_input>>

.user <<user_input>>
.exec
```

### Multi-Step Prompt Pattern
```
.# Complex analysis with multiple steps
.llm {"model": "gpt-4o"}
.system You are an expert analyst.

.user Analyze this data: <<data>>
.exec

.user Based on your analysis, provide 3 specific recommendations.
.exec

.print Final recommendations: <<last_response>>
```

### Function Integration Pattern
```
.# Prompt that uses external data
.llm {"model": "gpt-4o-mini"}
.system You are a data analyst.
.user Analyze this data and provide insights:

.include <<data_file>>

.exec
```
REPLACE

### Conversation Continuation Pattern
```bash
# Start conversation
keprompt -e initial_prompt --conversation session_123 --param topic "AI"

# Continue conversation
keprompt --conversation session_123 --answer "Tell me more about the second point"

# Continue with new context
keprompt --conversation session_123 --answer "How does this apply to healthcare?"
```

## Testing Patterns

### Basic Prompt Testing
```python
def test_customer_support_prompt():
    result = call_keprompt('customer_support',
                          message="I can't log in",
                          user_tier="premium")
    
    assert "password reset" in result.lower()
    assert len(result) > 50  # Ensure substantial response
    # Cost assertion could be added here
```

### Model Comparison Testing
```python
def test_prompt_across_models():
    models = ["gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash"]
    results = {}
    
    for model in models:
        # Temporarily modify prompt to use different model
        result = call_keprompt('test_prompt', model=model, input="test")
        results[model] = result
    
    # Compare results for consistency
    assert all(len(r) > 20 for r in results.values())
```

### Cost Control Testing
```python
def test_prompt_cost_limits():
    # Use debug mode to capture cost information
    result = subprocess.run([
        'keprompt', '-e', 'expensive_prompt', '--debug'
    ], capture_output=True, text=True)
    
    # Parse debug output for cost information
    assert "Total cost:" in result.stderr
    # Add assertions for cost thresholds
```

## Production Patterns

### Monitoring Integration
```python
import logging
import time

def monitored_keprompt_call(prompt_name, **params):
    start_time = time.time()
    try:
        result = call_keprompt(prompt_name, **params)
        duration = time.time() - start_time
        
        # Log successful call
        logging.info(f"KePrompt success: {prompt_name}, duration: {duration:.2f}s")
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logging.error(f"KePrompt failed: {prompt_name}, duration: {duration:.2f}s, error: {e}")
        raise
```

### Caching Pattern
```python
import hashlib
import json
from functools import lru_cache

def cached_keprompt_call(prompt_name, cache_ttl=300, **params):
    # Create cache key from prompt name and parameters
    cache_key = hashlib.md5(
        json.dumps({"prompt": prompt_name, "params": params}, sort_keys=True).encode()
    ).hexdigest()
    
    # Check cache (implementation depends on your caching system)
    cached_result = get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    # Call KePrompt and cache result
    result = call_keprompt(prompt_name, **params)
    set_cache(cache_key, result, ttl=cache_ttl)
    return result
```

### Batch Processing Pattern
```python
async def batch_process_prompts(items, prompt_name, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_item(item):
        async with semaphore:
            return await async_keprompt_call(prompt_name, **item)
    
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## Debugging Patterns

### Development Debugging
```bash
# Full debug output
keprompt -e my_prompt --debug --param input "test data"

# Log to file for analysis
keprompt -e my_prompt --log debug_session --param input "test data"
```

### Production Debugging
```python
def debug_keprompt_call(prompt_name, **params):
    # Add debug flag in development/staging
    cmd = ['keprompt', '-e', prompt_name]
    if os.getenv('ENVIRONMENT') != 'production':
        cmd.append('--debug')
    
    for key, value in params.items():
        cmd.extend(['--param', key, str(value)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Log debug info in non-production
    if os.getenv('ENVIRONMENT') != 'production':
        logger.debug(f"KePrompt debug output: {result.stderr}")
    
    return result.stdout.strip()
```

## Configuration Management

### Environment-Specific Models
```python
def get_model_for_environment():
    env_models = {
        'development': 'gpt-4o-mini',  # Cheaper for dev
        'staging': 'gpt-4o-mini',      # Same as dev
        'production': 'gpt-4o'         # Best quality for prod
    }
    return env_models.get(os.getenv('ENVIRONMENT', 'development'))

# Use in prompt files with variable substitution
# .llm {"model": "<<model>>"}
```

### Dynamic Parameter Injection
```python
def build_prompt_params(base_params, context):
    params = base_params.copy()
    
    # Add environment-specific context
    params['environment'] = os.getenv('ENVIRONMENT', 'development')
    params['timestamp'] = datetime.now().isoformat()
    params['user_context'] = json.dumps(context.get('user', {}))
    
    return params
