# Logging Architecture Test

This document provides test cases to verify the new `.print` statement and logging architecture.

## Test 1: Basic .print functionality

```bash
# Run the test prompt normally (development mode)
python -m keprompt -e print_test

# Expected: You should see rich development logs AND the .print output mixed together
```

## Test 2: Output redirection to separate STDOUT and STDERR

```bash
# Redirect STDOUT and STDERR to separate files
python -m keprompt -e print_test > production_output.txt 2> development_logs.txt

# Check what went to production output (STDOUT)
echo "=== PRODUCTION OUTPUT (STDOUT) ==="
cat production_output.txt

# Check what went to development logs (STDERR) 
echo "=== DEVELOPMENT LOGS (STDERR) ==="
cat development_logs.txt
```

## Test 3: Production pipeline usage

```bash
# Use .print output in a pipeline (only production data should flow through)
python -m keprompt -e print_test 2>/dev/null | grep "result:"

# Expected: Only the .print statement outputs should appear
```

## Test 4: Capture production output in variable

```bash
# Capture only the production output
result=$(python -m keprompt -e print_test 2>/dev/null)
echo "Captured result: $result"
```

## Current Status

- ✅ `.print` statement works and outputs to STDOUT
- ⚠️  Development logs still go to STDOUT (needs Phase 3 implementation)
- ✅ Variable substitution works with `<<last_response>>`
- ✅ Multiple `.print` statements work in sequence

## Expected Behavior After Full Implementation

After completing Phase 3 (VM refactoring), the output separation should be:

**STDOUT (production_output.txt):**
```
Math result: 4
Geography result: Paris
Final summary: Math=Paris, but we need the previous math result too
```

**STDERR (development_logs.txt):**
```
╭──print_test.prompt─────────────────────────────────────────╮
│00 .#       Test prompt for the new .print statement...     │
│01 .llm     {"model": "gpt-4o-mini"}                        │
│02 .system  You are a helpful assistant...                  │
│03 .user    What is 2 + 2? Answer with just the number.    │
│04 .exec    Calling OpenAI::gpt-4o-mini                     │
│            Call-01 Elapsed: 1.23 seconds...                │
│05 .print   Math result: <<last_response>>                  │
│06 .user    What is the capital of France?...               │
│07 .exec    Calling OpenAI::gpt-4o-mini                     │
│            Call-02 Elapsed: 0.98 seconds...                │
│08 .print   Geography result: <<last_response>>             │
│09 .print   Final summary: Math=<<last_response>>...        │
│10 .exit                                                    │
╰────────────────────────────────────────────────────────────╯
Wrote logs/print_test.svg to disk
