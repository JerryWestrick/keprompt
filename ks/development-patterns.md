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
.prompt "name":"Descriptive Prompt Name", "version":"1.0.0", "params":{"model":"gpt-4o-mini", "context":"input_context", "user_input":"user_request"}
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

## Cost Analysis Patterns

### Cost Monitoring Integration
```python
import subprocess
import json

def get_prompt_costs(prompt_name, days=7):
    """Get cost analysis for a specific prompt"""
    result = subprocess.run([
        'python', '-m', 'keprompt.cost_cli', 'prompt', prompt_name, '--days', str(days)
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        return result.stdout
    else:
        raise Exception(f"Cost analysis failed: {result.stderr}")

def get_recent_costs(limit=10):
    """Get recent cost entries with semantic names"""
    result = subprocess.run([
        'python', '-m', 'keprompt.cost_cli', 'recent', '--limit', str(limit)
    ], capture_output=True, text=True)
    
    return result.stdout if result.returncode == 0 else None
```

### Cost-Aware Prompt Selection
```python
def select_model_by_budget(prompt_complexity, budget_per_call):
    """Select appropriate model based on budget constraints"""
    model_costs = {
        'gpt-4o-mini': 0.000150,      # per 1K tokens (input)
        'gpt-4o': 0.0025,             # per 1K tokens (input)
        'claude-3-haiku': 0.00025,    # per 1K tokens (input)
        'claude-3-5-sonnet': 0.003,   # per 1K tokens (input)
    }
    
    # Estimate tokens based on complexity
    estimated_tokens = prompt_complexity * 1000
    
    # Select cheapest model within budget
    for model, cost_per_1k in sorted(model_costs.items(), key=lambda x: x[1]):
        estimated_cost = (estimated_tokens / 1000) * cost_per_1k
        if estimated_cost <= budget_per_call:
            return model
    
    return 'gpt-4o-mini'  # Fallback to cheapest

# Usage in prompt parameter building
def build_cost_aware_params(base_params, budget=0.01):
    params = base_params.copy()
    complexity = params.get('complexity', 1)  # 1-5 scale
    params['model'] = select_model_by_budget(complexity, budget)
    return params
```

### Prompt Version Performance Tracking
```python
def compare_prompt_versions(prompt_name, version1, version2, days=30):
    """Compare performance between prompt versions"""
    # This would require extending the cost CLI to filter by version
    # For now, manual analysis of cost data
    
    cost_data = get_prompt_costs(prompt_name, days)
    
    # Parse cost data to extract version-specific metrics
    # Implementation would depend on cost CLI output format
    
    return {
        'version1_avg_cost': 0.0,  # Calculated from data
        'version2_avg_cost': 0.0,  # Calculated from data
        'performance_delta': 0.0,  # Percentage difference
        'recommendation': 'Use version X for better cost efficiency'
    }
```
