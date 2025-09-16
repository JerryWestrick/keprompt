# Current Cost Storage Analysis in KePrompt

## Where AI Call Costs Are Stored

### 1. **In-Memory Storage (Session Level)**

**Location**: `keprompt_vm.py` - VM class instance variables
```python
class VM:
    def __init__(self, ...):
        self.cost_in = 0      # Cumulative input costs for session
        self.cost_out = 0     # Cumulative output costs for session  
        self.total = 0        # Total session cost
        self.toks_in = 0      # Total input tokens
        self.toks_out = 0     # Total output tokens
```

**Lifecycle**: These costs are accumulated during VM execution but **lost when the session ends**.

### 2. **Log Files (Persistent Storage)**

**Location**: `prompts/logs-{identifier}/keprompt.log`

**Format**: Text-based log entries via `keprompt_logger.py`
```
[2025-01-15 15:30:25][abc123-exec001][LLM]> abc123-exec001 tokens in: 150, out: 75, cost in: $0.000750, out: $0.002250, total: $0.003000
[2025-01-15 15:30:30][abc123-exec001][LLM]> SESSION TOTAL: Tokens In: 150, Out: 75, Cost In: $0.000750, Out: $0.002250, Total: $0.003000
```

**When Created**: Only when using `--debug` or `--log` flags

### 3. **STDERR Output (Immediate Visibility)**

**Location**: Standard error stream
```bash
Session Total Cost: $0.003000 (In: $0.000750, Out: $0.002250)
```

**When Shown**: At the end of every session that incurs costs

## Cost Calculation Flow

```
1. AI API Response → Provider.extract_token_usage()
2. Provider.calculate_costs(tokens_in, tokens_out) 
3. VM accumulates: vm.cost_in += cost_in, vm.cost_out += cost_out
4. Logger.log_llm_tokens_and_cost() → writes to log file
5. On session end: Logger.log_total_costs() → writes total + prints to STDERR
```

## Current Storage Limitations

### ❌ **No Persistent Database**
- Costs are only stored in text log files
- No structured data for analysis
- No historical aggregation across sessions

### ❌ **No Centralized Cost History**
- Each prompt execution creates separate log files
- No way to query "total costs this month"
- No cost trends or analytics

### ❌ **Log Files Only Created in Debug/Log Mode**
- Production runs (default mode) don't store costs anywhere
- Only STDERR output shows session total
- No persistent record of production costs

### ❌ **No Cost Metadata**
- No user identification
- No project/prompt categorization
- No business context (department, cost center, etc.)

## What's Missing for Better Cost Management

### 1. **Structured Database Storage**
```sql
-- Proposed schema
CREATE TABLE ai_costs (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    session_id TEXT,
    prompt_name TEXT,
    model TEXT,
    provider TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_in REAL,
    cost_out REAL,
    total_cost REAL,
    user_id TEXT,
    project TEXT
);
```

### 2. **Always-On Cost Tracking**
- Store costs even in production mode
- Lightweight background cost recording
- No dependency on debug/log flags

### 3. **Cost Aggregation & Reporting**
- Daily/weekly/monthly cost summaries
- Cost per prompt/model/user analysis
- Spending trend identification
- Budget tracking and alerts

## Current Cost Data Access

**To see costs today, you must:**
1. Run with `--debug` or `--log` flags
2. Check log files in `prompts/logs-{identifier}/keprompt.log`
3. Parse text-based log entries manually
4. Or check STDERR output for session totals

**Example**:
```bash
keprompt -e my_prompt --debug
# Costs logged to: prompts/logs-my_prompt/keprompt.log
# Session total printed to STDERR at end
```

## Recommendation

The current system tracks costs accurately but stores them poorly. We need:
1. **Always-on structured storage** (SQLite database)
2. **Cost aggregation tools** for analysis
3. **Better cost visibility** without requiring debug mode
4. **Historical cost tracking** across all sessions
