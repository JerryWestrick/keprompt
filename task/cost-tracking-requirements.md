# Cost Tracking Requirements Investigation

**Status**: Draft - Requires Confirmation  
**Date**: 2025-01-15  
**Purpose**: Investigate and define requirements for enhanced cost tracking in KePrompt

## Current State Analysis

### Existing Cost Tracking Capabilities
- ✅ Real-time token extraction from all AI providers
- ✅ Immediate cost calculation using current pricing data
- ✅ Session-level cost accumulation in VM
- ✅ Structured logging of costs to files
- ✅ Multi-provider support (OpenAI, Anthropic, Google, etc.)

### Current Architecture Flow
```
API Response → Provider.extract_token_usage() → Provider.calculate_costs() → VM.cost_tracking → Logger.log_costs
```

### Identified Limitations
1. **No Budget Controls** - Cannot set spending limits or receive alerts
2. **Limited Visibility** - Costs only visible in debug mode or log files
3. **No Historical Analysis** - Cannot track spending trends over time
4. **No Cost Optimization** - No automatic model selection based on cost/quality
5. **No Pre-execution Estimation** - Cannot predict costs before running prompts

## Proposed Requirements (To Be Confirmed)

### Phase 1: Essential Cost Controls
**Priority**: High - Immediate business need

1. **Budget Limit System**
   - Set daily/weekly/monthly spending limits
   - Hard stops when budget exceeded
   - Configurable via CLI or prompt files
   - Grace period warnings before hitting limits

2. **Pre-execution Cost Estimation**
   - Estimate costs before API calls
   - Show estimated vs actual costs
   - Confirmation prompts for expensive operations
   - Token estimation algorithms

3. **Enhanced Cost Visibility**
   - Show costs in standard output (not just debug)
   - Real-time cost display during execution
   - Cost per statement/operation breakdown
   - Session cost summaries

### Phase 2: Smart Optimization
**Priority**: Medium - Operational efficiency

1. **Auto-Model Selection**
   - Define quality thresholds and cost limits
   - Automatically select cheapest model meeting requirements
   - Fallback chains: expensive → medium → cheap
   - A/B testing for cost/quality trade-offs

2. **Historical Cost Database**
   - SQLite database for cost history
   - Track costs per prompt, model, provider
   - Cost trends and analytics
   - Export capabilities (CSV, JSON)

3. **Cost Reporting Tools**
   - Daily/weekly/monthly spending reports
   - Cost per project/prompt analysis
   - Model efficiency comparisons
   - Spending pattern analysis

### Phase 3: Advanced Features
**Priority**: Low - Nice to have

1. **Cost Forecasting**
   - Predict costs for batch operations
   - Budget planning tools
   - Spending trend projections
   - Resource planning assistance

2. **Team Cost Management**
   - Multi-user cost allocation
   - Department/project cost tracking
   - Cost center reporting
   - User spending limits

3. **Integration APIs**
   - Webhook notifications for spending thresholds
   - External monitoring system integration
   - Cost alert systems
   - Business intelligence connectors

## Technical Implementation Considerations

### Database Schema (Proposed)
```sql
CREATE TABLE cost_tracking (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    prompt_name TEXT,
    model TEXT,
    provider TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_in REAL,
    cost_out REAL,
    total_cost REAL,
    call_id TEXT,
    user_id TEXT
);
```

### CLI Extensions (Proposed)
```bash
# Cost estimation
keprompt -e prompt_name --estimate-cost

# Budget setting
keprompt -e prompt_name --budget 0.50

# Cost reporting
keprompt --cost-report daily
keprompt --cost-report --prompt prompt_name
```

### Prompt Language Extensions (Proposed)
```
.# Cost-aware prompt
.llm {"model": "auto", "max_cost": 0.10, "quality": "high"}
.budget 1.00  # Set session budget
.cost_check   # Check current spending
```

## Questions for Confirmation

1. **Budget Priority**: Are budget controls the highest priority feature?
2. **Cost Visibility**: Should costs be shown in standard output by default?
3. **Historical Data**: Do we need persistent cost tracking or just session-level?
4. **Auto-Selection**: Is automatic model selection based on cost/quality desired?
5. **Integration**: Are external integrations (webhooks, alerts) needed?
6. **User Management**: Do we need multi-user cost tracking?

## Success Criteria (To Be Defined)

- [ ] Users can set and enforce spending budgets
- [ ] Cost estimation accuracy within X% of actual costs
- [ ] Cost visibility without requiring debug mode
- [ ] Historical cost analysis capabilities
- [ ] Automatic cost optimization features
- [ ] Integration with existing KePrompt workflows

## Next Steps

1. **Confirm requirements** with stakeholders
2. **Prioritize features** based on business needs
3. **Define success metrics** and acceptance criteria
4. **Create detailed technical specifications**
5. **Plan implementation phases**
6. **Begin development of Phase 1 features**

---

**Note**: This document represents initial requirements investigation and needs stakeholder review and confirmation before proceeding with implementation.
