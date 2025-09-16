# KePrompt Cost Tracking Usage Guide

## Overview

KePrompt now includes comprehensive, always-on cost tracking that automatically captures AI API usage costs, tokens, and execution metadata for all prompt executions. This guide explains how to use and integrate with the cost tracking system.

## Automatic Cost Tracking

### Always-On Operation

Cost tracking is **enabled by default** in all execution modes:
- ✅ **Production mode**: Full cost tracking with no performance impact
- ✅ **Debug mode**: Cost tracking + enhanced logging  
- ✅ **Log mode**: Cost tracking + file logging

**No CLI flags required** - cost data is always captured to `prompts/costs.db`.

### What Gets Tracked

Every prompt execution automatically captures:

**Core Data (Always Captured):**
- Prompt name and KePrompt version
- Execution timestamp and duration
- Input/output tokens and costs
- AI model and provider used
- Session and call identifiers

**Extended Metadata (When Available):**
- User ID and project (from environment variables)
- Model configuration (temperature, max_tokens)
- Execution success/failure status
- System information (hostname, git commit)

## Database Storage

### Location
- **File**: `./prompts/costs.db` (SQLite database)
- **Auto-creation**: Database and table created automatically on first execution
- **Per-project**: Each project gets its own cost database

### Management
```bash
# View current database
ls -la prompts/costs.db

# Clean all history (fresh start)
rm prompts/costs.db

# Backup cost data
cp prompts/costs.db backups/costs-$(date +%Y%m%d).db
```

## Application Integration

### Setting User and Project Context

Use environment variables to provide context for cost tracking:

```bash
# Set user identification
export KEPROMPT_USER_ID="alice@company.com"

# Set project/category
export KEPROMPT_PROJECT="customer-support"

# Run prompt - costs automatically tracked with context
keprompt -e support_prompt
```

### Programmatic Integration

```python
import os

# Set context before running KePrompt
os.environ['KEPROMPT_USER_ID'] = 'data-team@company.com'
os.environ['KEPROMPT_PROJECT'] = 'analytics-pipeline'

# Run KePrompt subprocess or direct integration
# Cost data will include user_id and project fields
```

### Integration Examples

**Customer Support System:**
```bash
#!/bin/bash
export KEPROMPT_USER_ID="$SUPPORT_AGENT_EMAIL"
export KEPROMPT_PROJECT="customer-support"
keprompt -e resolve_ticket --param ticket_id="$1"
```

**Data Processing Pipeline:**
```python
import os
import subprocess

def run_analysis_prompt(dataset_name, user_email):
    os.environ['KEPROMPT_USER_ID'] = user_email
    os.environ['KEPROMPT_PROJECT'] = 'data-analysis'
    
    result = subprocess.run([
        'keprompt', '-e', 'analyze_dataset',
        '--param', f'dataset={dataset_name}'
    ], capture_output=True, text=True)
    
    return result.stdout
```

## Cost Reporting and Analysis

### CLI Commands

KePrompt provides built-in cost analysis commands:

```bash
# View recent cost entries
python -m keprompt.cost_cli recent --limit 20

# Cost summary for last 7 days
python -m keprompt.cost_cli summary --days 7

# Cost breakdown by prompt
python -m keprompt.cost_cli by-prompt --days 30

# Cost breakdown by model
python -m keprompt.cost_cli by-model --days 30

# Export cost data to CSV
python -m keprompt.cost_cli export costs.csv --days 90
```

### Direct Database Queries

The SQLite database can be queried directly for custom analysis:

```sql
-- Total costs by user this month
SELECT user_id, SUM(estimated_costs) as total_cost, COUNT(*) as calls
FROM cost_tracking 
WHERE timestamp >= date('now', 'start of month')
GROUP BY user_id
ORDER BY total_cost DESC;

-- Most expensive prompts
SELECT prompt_name, AVG(estimated_costs) as avg_cost, COUNT(*) as usage_count
FROM cost_tracking
GROUP BY prompt_name
ORDER BY avg_cost DESC
LIMIT 10;

-- Token efficiency by model
SELECT model, 
       AVG(CAST(tokens_out AS REAL) / tokens_in) as output_ratio,
       AVG(estimated_costs) as avg_cost
FROM cost_tracking 
WHERE tokens_in > 0
GROUP BY model;
```

### Programmatic Access

```python
import sqlite3
from pathlib import Path

def get_project_costs(project_name, days=30):
    """Get cost summary for a specific project."""
    db_path = Path("prompts/costs.db")
    if not db_path.exists():
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT COUNT(*) as calls, SUM(estimated_costs) as total_cost
        FROM cost_tracking 
        WHERE project = ? AND timestamp >= datetime('now', '-{} days')
    """.format(days), (project_name,))
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        "project": project_name,
        "calls": row[0] if row else 0,
        "total_cost": row[1] if row else 0.0
    }

# Usage
costs = get_project_costs("customer-support", days=7)
print(f"Project: {costs['project']}")
print(f"Calls: {costs['calls']}")
print(f"Cost: ${costs['total_cost']:.6f}")
```

## Database Schema Reference

### Complete Schema

```sql
CREATE TABLE cost_tracking (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Core required fields (always populated)
    prompt_name TEXT NOT NULL,           -- Prompt file name
    version TEXT NOT NULL,               -- KePrompt version  
    timestamp DATETIME NOT NULL,         -- Execution time
    tokens_in INTEGER NOT NULL,          -- Input tokens
    tokens_out INTEGER NOT NULL,         -- Output tokens
    estimated_costs REAL NOT NULL,       -- Total cost
    elapsed_time REAL NOT NULL,          -- Duration in seconds
    
    -- Essential for cost engineering (always populated)
    model TEXT NOT NULL,                 -- AI model used
    provider TEXT NOT NULL,              -- AI provider
    cost_in REAL NOT NULL,              -- Input token cost
    cost_out REAL NOT NULL,             -- Output token cost
    session_id TEXT NOT NULL,           -- Session identifier
    call_id TEXT NOT NULL,              -- API call identifier
    
    -- Application-provided fields (NULL if not provided)
    user_id TEXT,                       -- User who executed
    project TEXT,                       -- Project/category
    parameters TEXT,                    -- JSON of parameters
    
    -- Execution tracking (always populated)
    success BOOLEAN NOT NULL DEFAULT 1, -- Execution success
    error_message TEXT,                 -- Error details if failed
    
    -- Model configuration (captured when available)
    context_length INTEGER,             -- Context window used
    temperature REAL,                   -- Model temperature
    max_tokens INTEGER,                 -- Max tokens setting
    
    -- Operational metadata (auto-populated)
    hostname TEXT,                      -- Execution machine
    environment TEXT,                   -- Environment type
    git_commit TEXT,                    -- Git commit hash
    execution_mode TEXT                 -- Mode (production/debug/log)
);
```

### Key Indexes

```sql
CREATE INDEX idx_timestamp ON cost_tracking(timestamp);
CREATE INDEX idx_prompt_name ON cost_tracking(prompt_name);
CREATE INDEX idx_model ON cost_tracking(model);
CREATE INDEX idx_user_id ON cost_tracking(user_id);
CREATE INDEX idx_project ON cost_tracking(project);
CREATE INDEX idx_session_id ON cost_tracking(session_id);
```

## Best Practices

### For Application Developers

1. **Always Set Context**: Use `KEPROMPT_USER_ID` and `KEPROMPT_PROJECT` environment variables
2. **Monitor Costs**: Regularly check cost summaries and trends
3. **Archive Data**: Periodically backup and archive cost databases
4. **Set Budgets**: Implement application-level budget monitoring

### For System Administrators

1. **Disk Space**: Monitor `prompts/costs.db` file size growth
2. **Performance**: Cost tracking has minimal overhead but monitor in high-volume scenarios
3. **Security**: Protect cost databases as they contain usage patterns and user information
4. **Compliance**: Consider data retention policies for cost tracking data

### For Data Analysis

1. **Export Regularly**: Use CSV export for external analysis tools
2. **Aggregate Data**: Combine multiple project databases for organization-wide analysis
3. **Trend Analysis**: Track cost trends over time to optimize AI usage
4. **Model Comparison**: Compare costs and efficiency across different AI models

## Troubleshooting

### Common Issues

**Database Not Created:**
- Ensure `prompts/` directory exists and is writable
- Check file permissions on the directory
- Verify KePrompt has write access to the working directory

**Missing Cost Data:**
- Cost tracking is always-on, but requires successful API calls
- Check that prompts are actually executing (not just parsing)
- Verify the prompt contains `.exec` statements

**Performance Concerns:**
- Cost tracking uses SQLite with minimal overhead
- Database operations are asynchronous and don't block execution
- Consider archiving old data if database becomes very large

### Error Handling

Cost tracking is designed to never fail prompt execution:
- Database errors are logged to STDERR but don't stop execution
- Missing environment variables result in NULL values, not errors
- Schema mismatches trigger automatic database recreation

## Migration and Upgrades

### From Previous Versions

If upgrading from a version without cost tracking:
- Cost tracking starts immediately with no migration needed
- Previous log-based cost data remains in log files
- New SQLite database begins tracking from first execution

### Schema Updates

Future schema updates will be handled automatically:
- New columns added with default values
- Existing data preserved during upgrades
- Backward compatibility maintained

## Security and Privacy

### Data Sensitivity

Cost tracking databases may contain:
- User identification information
- Project names and categories
- Execution patterns and timing
- Model usage preferences

### Recommendations

1. **Access Control**: Restrict access to `prompts/costs.db` files
2. **Data Retention**: Implement policies for cost data lifecycle
3. **Anonymization**: Consider hashing user IDs for privacy
4. **Encryption**: Encrypt cost databases for sensitive environments

## Support and Feedback

For issues, questions, or feature requests related to cost tracking:
1. Check this documentation first
2. Review the database schema and CLI commands
3. Test with simple prompts to isolate issues
4. Report bugs with specific error messages and reproduction steps

The cost tracking system is designed to be transparent, reliable, and useful for both development and production AI operations.
