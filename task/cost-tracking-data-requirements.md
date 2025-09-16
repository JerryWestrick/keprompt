# Cost Tracking Data Requirements

## Core Required Fields (Confirmed)

1. **`{promptname}.prompt`** - The prompt file that was executed
2. **`version number`** - Version of KePrompt that executed the prompt
3. **`timestamp`** - When the execution occurred
4. **`tokens_in`** - Input tokens consumed
5. **`tokens_out`** - Output tokens generated
6. **`estimated_costs`** - Calculated cost for the execution
7. **`elapsed_time`** - Duration of the execution

## Additional Recommended Fields

### Essential for Cost Engineering

8. **`model`** - AI model used (e.g., "gpt-4o", "claude-3-5-sonnet")
9. **`provider`** - AI provider (e.g., "OpenAI", "Anthropic", "Google")
10. **`cost_in`** - Input token costs (separate from output)
11. **`cost_out`** - Output token costs (separate from input)
12. **`session_id`** - Unique identifier for the execution session
13. **`call_id`** - Unique identifier for each API call within session

### Valuable for Analysis

14. **`user_id`** - Who executed the prompt (NULL if not provided by application)
15. **`project`** - Project or category the prompt belongs to
16. **`parameters`** - Key parameters passed to the prompt (JSON)
17. **`success`** - Whether execution completed successfully (boolean)
18. **`error_message`** - Error details if execution failed
19. **`context_length`** - Total context window used
20. **`temperature`** - Model temperature setting used
21. **`max_tokens`** - Maximum tokens setting used

### Operational Metadata

22. **`hostname`** - Machine that executed the prompt
23. **`environment`** - Environment (dev, staging, prod)
24. **`git_commit`** - Git commit hash when executed
25. **`execution_mode`** - Mode used (production, debug, log)

## Proposed Database Schema

```sql
CREATE TABLE cost_tracking (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Core required fields
    prompt_name TEXT NOT NULL,           -- {promptname}.prompt
    version TEXT NOT NULL,               -- KePrompt version
    timestamp DATETIME NOT NULL,         -- Execution time
    tokens_in INTEGER NOT NULL,          -- Input tokens
    tokens_out INTEGER NOT NULL,         -- Output tokens
    estimated_costs REAL NOT NULL,       -- Total estimated cost
    elapsed_time REAL NOT NULL,          -- Execution duration in seconds
    
    -- Essential for cost engineering
    model TEXT NOT NULL,                 -- AI model used
    provider TEXT NOT NULL,              -- AI provider
    cost_in REAL NOT NULL,              -- Input token cost
    cost_out REAL NOT NULL,             -- Output token cost
    session_id TEXT NOT NULL,           -- Session identifier
    call_id TEXT NOT NULL,              -- API call identifier
    
    -- Valuable for analysis
    user_id TEXT,                       -- User who executed
    project TEXT,                       -- Project/category
    parameters TEXT,                    -- JSON of parameters
    success BOOLEAN NOT NULL DEFAULT 1, -- Execution success
    error_message TEXT,                 -- Error details if failed
    context_length INTEGER,             -- Context window used
    temperature REAL,                   -- Model temperature
    max_tokens INTEGER,                 -- Max tokens setting
    
    -- Operational metadata
    hostname TEXT,                      -- Execution machine
    environment TEXT,                   -- Environment (dev/staging/prod)
    git_commit TEXT,                    -- Git commit hash
    execution_mode TEXT,                -- Mode (production/debug/log)
    
    -- Indexes for common queries
    INDEX idx_timestamp (timestamp),
    INDEX idx_prompt_name (prompt_name),
    INDEX idx_model (model),
    INDEX idx_user_id (user_id),
    INDEX idx_project (project),
    INDEX idx_session_id (session_id)
);
```

## Data Collection Points

### Where to Capture This Data

1. **VM Initialization** - prompt_name, version, session_id, user_id, environment
2. **LLM Configuration** - model, provider, temperature, max_tokens
3. **API Call Start** - timestamp, call_id, parameters
4. **API Response** - tokens_in, tokens_out, cost_in, cost_out, context_length
5. **Execution End** - elapsed_time, success, error_message

### Current vs Required Data Availability

| Field | Currently Available | Location | Notes |
|-------|-------------------|----------|-------|
| prompt_name | ✅ | `vm.filename` | Need to strip path/extension |
| version | ✅ | `keprompt.version.__version__` | |
| timestamp | ✅ | `time.time()` | Need to capture at start |
| tokens_in | ✅ | `provider.extract_token_usage()` | |
| tokens_out | ✅ | `provider.extract_token_usage()` | |
| estimated_costs | ✅ | `provider.calculate_costs()` | |
| elapsed_time | ✅ | `time.time()` difference | |
| model | ✅ | `vm.model_name` | |
| provider | ✅ | `vm.provider` | |
| cost_in | ✅ | `provider.calculate_costs()` | |
| cost_out | ✅ | `provider.calculate_costs()` | |
| session_id | ✅ | `vm.prompt_uuid` | |
| call_id | ✅ | Generated in StmtExec | |
| user_id | ❌ | Need to implement | |
| project | ❌ | Could derive from path | |
| parameters | ❌ | Need to capture vm.vdict | |
| success | ❌ | Need to track execution state | |
| error_message | ❌ | Need to capture exceptions | |

## Implementation Priority

### Phase 1: Core Data Collection
- Implement the 7 required fields you specified
- Add model, provider, cost breakdown
- Create basic SQLite database storage

### Phase 2: Enhanced Metadata
- Add user_id, project, parameters
- Capture success/error states
- Add operational metadata

### Phase 3: Advanced Analytics
- Add performance metrics
- Environment tracking
- Git integration

## Implementation Decisions (Confirmed)

1. **Storage Location**: ✅ SQLite database in project directory (`costs.db`)
2. **Always-On Tracking**: ✅ Cost tracking enabled by default in all modes
3. **User ID Handling**: ✅ NULL when not provided by application programmers
4. **Data Management**: ✅ Application programmers handle cleanup and retention
5. **Schema Publication**: ✅ Publish schema for programmer integration

## Final Database Schema (Ready for Implementation)

```sql
CREATE TABLE cost_tracking (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Core required fields (always populated)
    prompt_name TEXT NOT NULL,           -- {promptname}.prompt
    version TEXT NOT NULL,               -- KePrompt version  
    timestamp DATETIME NOT NULL,         -- Execution time
    tokens_in INTEGER NOT NULL,          -- Input tokens
    tokens_out INTEGER NOT NULL,         -- Output tokens
    estimated_costs REAL NOT NULL,       -- Total estimated cost
    elapsed_time REAL NOT NULL,          -- Execution duration in seconds
    
    -- Essential for cost engineering (always populated)
    model TEXT NOT NULL,                 -- AI model used
    provider TEXT NOT NULL,              -- AI provider
    cost_in REAL NOT NULL,              -- Input token cost
    cost_out REAL NOT NULL,             -- Output token cost
    session_id TEXT NOT NULL,           -- Session identifier
    call_id TEXT NOT NULL,              -- API call identifier
    
    -- Application-provided fields (NULL if not provided)
    user_id TEXT,                       -- User who executed (app-provided)
    project TEXT,                       -- Project/category (app-provided)
    parameters TEXT,                    -- JSON of parameters (captured from vm.vdict)
    
    -- Execution tracking (always populated)
    success BOOLEAN NOT NULL DEFAULT 1, -- Execution success
    error_message TEXT,                 -- Error details if failed
    
    -- Model configuration (captured when available)
    context_length INTEGER,             -- Context window used
    temperature REAL,                   -- Model temperature
    max_tokens INTEGER,                 -- Max tokens setting
    
    -- Operational metadata (auto-populated)
    hostname TEXT,                      -- Execution machine
    environment TEXT,                   -- Environment (dev/staging/prod)
    git_commit TEXT,                    -- Git commit hash
    execution_mode TEXT,                -- Mode (production/debug/log)
    
    -- Indexes for efficient querying
    INDEX idx_timestamp (timestamp),
    INDEX idx_prompt_name (prompt_name),
    INDEX idx_model (model),
    INDEX idx_user_id (user_id),
    INDEX idx_project (project),
    INDEX idx_session_id (session_id)
);
```

## Database Location

**File**: `./prompts/costs.db` (in prompts directory)
- Each project gets its own cost database in the prompts folder
- Auto-created if not found (allows fresh start by deleting file)
- No single point of failure or collection
- Easy backup with project files
- Application programmers can manage per-project
- Simple history cleanup: just delete `prompts/costs.db`

## Always-On Implementation

Cost tracking will be enabled by default in all execution modes:
- ✅ Production mode: Full cost tracking
- ✅ Debug mode: Cost tracking + enhanced logging  
- ✅ Log mode: Cost tracking + file logging

No CLI flags required - cost data always captured.

## Application Integration Points

**For Application Programmers:**
1. **User ID**: Pass via environment variable `KEPROMPT_USER_ID` or CLI parameter
2. **Project**: Pass via environment variable `KEPROMPT_PROJECT` or CLI parameter  
3. **Parameters**: Automatically captured from prompt parameters
4. **Database Management**: Handle cleanup, archiving, analysis per project needs

**Example Integration:**
```bash
# Application sets context
export KEPROMPT_USER_ID="alice@company.com"
export KEPROMPT_PROJECT="customer-support"

# KePrompt automatically tracks costs to prompts/costs.db
keprompt -e support_prompt --param ticket_id 12345

# Clean history by deleting the database file
rm prompts/costs.db  # Fresh start!
```

## Database Management

**Auto-Creation**: Database and table created automatically on first execution
**History Cleanup**: Simple - just delete `prompts/costs.db` file
**Backup**: Include `prompts/costs.db` in project backups
**Analysis**: Query SQLite database directly or build custom tools

This approach gives maximum flexibility while ensuring comprehensive cost data collection.
