# KePrompt Examples Collection

This document contains practical, real-world examples of using keprompt for various tasks. Each example includes the complete prompt file and usage instructions.

## Table of Contents

1. [Content Creation](#content-creation)
2. [Code Analysis & Review](#code-analysis--review)
3. [Research & Analysis](#research--analysis)
4. [Data Processing](#data-processing)
5. [Automation & Workflows](#automation--workflows)
6. [Learning & Education](#learning--education)
7. [Business & Productivity](#business--productivity)

## Content Creation

### Blog Post Generator

**File: `prompts/content/blog_generator.prompt`**
```
.# Blog Post Generator with SEO optimization
.llm {"model": "gpt-4o"}
.system You are a professional content writer and SEO expert. Create engaging, well-structured content optimized for search engines.

.user Create a file called "blog_<<topic>>.md" with a comprehensive blog post about: <<topic>>
Target audience: <<audience>>
Tone: <<tone>>
Word count: approximately <<word_count>> words
Include:
- Compelling headline
- Introduction with hook
- Well-structured body with subheadings
- Conclusion with call-to-action
- SEO meta description
- 5 relevant tags
.exec

.user Now create a file called "social_<<topic>>.md" with social media posts to promote this blog:
- Twitter thread (5 tweets)
- LinkedIn post
- Facebook post
.exec
```

**Usage:**
```bash
keprompt -e content/blog_generator \
  --param topic "AI_productivity_tools" \
  --param audience "software_developers" \
  --param tone "informative_yet_engaging" \
  --param word_count "1200" \
  --debug
```

### Technical Documentation

**File: `prompts/content/tech_docs.prompt`**
```
.# Technical Documentation Generator
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a technical writer specializing in clear, comprehensive documentation for developers.

.user Create a file called "docs_<<project_name>>.md" with technical documentation for: <<project_name>>

Based on this code/information:
.include <<source_file>>
Generate:
1. Overview and purpose
2. Installation instructions
3. API reference (if applicable)
4. Usage examples
5. Configuration options
6. Troubleshooting guide
7. Contributing guidelines
.exec

.user Now create a file called "quickstart_<<project_name>>.md" with a quick start guide (max 500 words) for new users:
.exec
```

**Usage:**
```bash
keprompt -e content/tech_docs \
  --param project_name "my_api" \
  --param source_file "src/main.py" \
  --debug
```

## Code Analysis & Review

### Comprehensive Code Review

**File: `prompts/coding/code_review.prompt`**
```
.# Comprehensive Code Review System
.llm {"model": "gpt-4o"}
.system You are a senior software engineer and security expert. Provide thorough, constructive code reviews focusing on quality, security, performance, and maintainability.

.user Create a file called "review_<<codefile>>.md" with a comprehensive review of this code:
.include <<codefile>>

Provide a comprehensive review covering:
1. Code Quality & Style
2. Security Vulnerabilities
3. Performance Issues
4. Bug Potential
5. Maintainability Concerns
6. Best Practices Adherence
7. Testing Recommendations
.exec

.user Based on your review, create a file called "improvements_<<codefile>>.md" with specific improvement recommendations and code examples:
.exec

.user Generate a file called "checklist_<<codefile>>.md" with a checklist for the developer to address the issues:
.exec
```

**Usage:**
```bash
keprompt -e coding/code_review --param codefile "src/auth.py" --debug
```

### Git Repository Analysis

**File: `prompts/coding/repo_analysis.prompt`**
```
.# Git Repository Analysis
.llm {"model": "gpt-4o"}
.system You are a senior developer and project manager. Analyze git repositories for code quality, development patterns, and project health.

.user Analyze this git repository and create a file called "repo_analysis.md":
.cmd execcmd(cmd="git log --oneline -20")
.cmd execcmd(cmd="git status --porcelain")
.cmd execcmd(cmd="find . -name '*.py' -o -name '*.js' -o -name '*.java' | head -20")
.cmd execcmd(cmd="git shortlog -sn --all")

Based on this repository information, provide:
1. Project health assessment
2. Development activity analysis
3. Code organization review
4. Contributor analysis
5. Recommendations for improvement
.exec

.user Create a file called "development_roadmap.md" with a development roadmap based on the current state:
.exec
```

**Usage:**
```bash
cd /path/to/your/repo
keprompt -e coding/repo_analysis --debug
```

## Research & Analysis

### Market Research Assistant

**File: `prompts/research/market_research.prompt`**
```
.# Comprehensive Market Research Assistant
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a market research analyst with expertise in technology trends, competitive analysis, and business intelligence.

.user Gather initial information and create a file called "research_<<market_topic>>_initial.md":
.cmd wwwget(url="https://en.wikipedia.org/wiki/<<market_topic>>")

Conduct comprehensive market research on: <<market_topic>>
Focus areas: <<focus_areas>>
Target market: <<target_market>>
.exec

.user Based on the initial research, create a file called "research_<<market_topic>>_analysis.md" with detailed analysis of:
1. Market size and growth trends
2. Key players and competitive landscape
3. Technology trends and innovations
4. Opportunities and challenges
5. Future outlook and predictions
6. Investment and funding trends
.exec

.user Create a file called "research_<<market_topic>>_executive_summary.md" with an executive summary suitable for stakeholders:
.exec

.user Generate a file called "research_<<market_topic>>_recommendations.md" with actionable recommendations for businesses in this space:
.exec
```

**Usage:**
```bash
keprompt -e research/market_research \
  --param market_topic "artificial_intelligence" \
  --param focus_areas "enterprise_AI,consumer_applications" \
  --param target_market "B2B_software" \
  --debug
```

### Academic Research Helper

**File: `prompts/research/academic_research.prompt`**
```
.# Academic Research Assistant
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are an academic researcher with expertise in literature review, citation analysis, and scholarly writing.

.user Create a file called "literature_review_<<research_topic>>.md" with a comprehensive literature review:
Research topic: <<research_topic>>
Academic field: <<field>>
Research question: <<research_question>>

Provide a comprehensive literature review covering:
1. Key concepts and definitions
2. Historical development
3. Current state of research
4. Major theories and frameworks
5. Research gaps and opportunities
6. Methodological approaches
.exec

.user Create a file called "methodology_<<research_topic>>.md" with a research methodology framework for investigating: <<research_question>>
.exec

.user Generate a file called "hypotheses_<<research_topic>>.md" with potential research hypotheses and study designs:
.exec
```

**Usage:**
```bash
keprompt -e research/academic_research \
  --param research_topic "machine_learning_ethics" \
  --param field "computer_science" \
  --param research_question "How do bias mitigation techniques affect ML model performance?" \
  --debug
```

## Data Processing

### CSV Data Analyzer

**File: `prompts/data/csv_analyzer.prompt`**
```
.# CSV Data Analysis Assistant
.llm {"model": "gpt-4o"}
.system You are a data analyst expert in statistical analysis, data visualization recommendations, and business insights.

.user Read this CSV data file and create a file called "analysis_<<csv_file>>.md":
.cmd readfile(filename="<<csv_file>>")

Provide comprehensive data analysis including:
1. Data structure and schema overview
2. Statistical summary (if numeric data present)
3. Data quality assessment
4. Missing values and anomalies
5. Key patterns and trends
6. Business insights and recommendations
7. Suggested visualizations
.exec

.user Create a file called "visualizations_<<csv_file>>.py" with Python code to generate the recommended visualizations:
.exec

.user Generate a file called "queries_<<csv_file>>.sql" with SQL queries for common analysis tasks on this data:
.exec
```

**Usage:**
```bash
keprompt -e data/csv_analyzer --param csv_file "sales_data.csv" --debug
```

### Log File Analyzer

**File: `prompts/data/log_analyzer.prompt`**
```
.# Log File Analysis System
.llm {"model": "gpt-4o"}
.system You are a system administrator and security expert specializing in log analysis, anomaly detection, and system monitoring.

.user Read this log file and create a file called "log_analysis_<<log_file>>.md":
.cmd readfile(filename="<<log_file>>")

Provide comprehensive log analysis:
1. Log format and structure identification
2. Error patterns and frequency
3. Security incidents or suspicious activity
4. Performance issues and bottlenecks
5. System health indicators
6. Recommendations for monitoring and alerting
.exec

.user Create a file called "monitoring_rules_<<log_file>>.md" with monitoring rules and alerts based on the analysis:
.exec

.user Generate a file called "executive_summary_<<log_file>>.md" with a summary report for management:
.exec
```

**Usage:**
```bash
keprompt -e data/log_analyzer --param log_file "application.log" --debug
```

## Automation & Workflows

### Daily Standup Generator

**File: `prompts/automation/daily_standup.prompt`**
```
.# Daily Standup Report Generator
.llm {"model": "gpt-4o-mini"}
.system You are a project manager assistant. Generate concise, actionable daily standup reports.

.user Create a file called "standup_<<date>>.md" with a daily standup report:
Team: <<team_name>>
Project: <<project_name>>
Date: <<date>>

Based on recent git activity:
.cmd execcmd(cmd="git log --since='24 hours ago' --pretty=format:'%h - %an: %s'")

And current project status:
.cmd execcmd(cmd="git status --porcelain")

Create a standup report including:
1. Yesterday's accomplishments
2. Today's planned work
3. Blockers and challenges
4. Team updates needed
.exec
```

**Usage:**
```bash
keprompt -e automation/daily_standup \
  --param date "$(date +%Y-%m-%d)" \
  --param team_name "Backend Team" \
  --param project_name "API Redesign" \
  --debug
```

### Release Notes Generator

**File: `prompts/automation/release_notes.prompt`**
```
.# Release Notes Generator
.llm {"model": "gpt-4o"}
.system You are a technical writer specializing in release documentation. Create clear, user-friendly release notes.

.user Create a file called "release_notes_<<version>>.md" with release notes:
Version: <<version>>
Product: <<product_name>>
Release date: <<release_date>>

Based on git commits since last release:
.cmd execcmd(cmd="git log <<last_version>>..HEAD --pretty=format:'%h - %s'")

And current changes:
.cmd execcmd(cmd="git diff --name-only <<last_version>>..HEAD")

Create comprehensive release notes with:
1. New features and enhancements
2. Bug fixes and improvements
3. Breaking changes (if any)
4. Migration guide (if needed)
5. Known issues
6. Acknowledgments
.exec

.user Create a file called "release_announcement_<<version>>.md" with a shorter version for social media announcement:
.exec
```

**Usage:**
```bash
keprompt -e automation/release_notes \
  --param version "2.1.0" \
  --param product_name "MyApp" \
  --param release_date "2024-01-15" \
  --param last_version "v2.0.0" \
  --debug
```

## Learning & Education

### Concept Explainer

**File: `prompts/education/concept_explainer.prompt`**
```
.# Educational Concept Explainer
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are an expert educator who excels at explaining complex concepts in simple, engaging ways. Adapt your explanations to the learner's level.

.user Create a file called "explanation_<<concept>>.md" with a comprehensive explanation of this concept:
Concept: <<concept>>
Target audience: <<audience_level>>
Learning style preference: <<learning_style>>

Provide a comprehensive explanation including:
1. Simple definition and overview
2. Why it's important/relevant
3. Key components or principles
4. Real-world examples and analogies
5. Common misconceptions
6. Practice exercises or questions
7. Further learning resources
.exec

.user Create a file called "quiz_<<concept>>.md" with a quiz to test understanding of this concept:
.exec

.user Generate a file called "study_guide_<<concept>>.md" with a study guide with key points and mnemonics:
.exec
```

**Usage:**
```bash
keprompt -e education/concept_explainer \
  --param concept "machine_learning" \
  --param audience_level "beginner" \
  --param learning_style "visual_and_practical" \
  --debug
```

### Code Tutorial Generator

**File: `prompts/education/code_tutorial.prompt`**
```
.# Programming Tutorial Generator
.llm {"model": "gpt-4o"}
.system You are a programming instructor who creates clear, step-by-step tutorials with practical examples.

.user Create a file called "tutorial_<<topic>>.md" with a comprehensive tutorial:
Topic: <<topic>>
Programming language: <<language>>
Skill level: <<skill_level>>
Tutorial length: <<length>>

Generate a comprehensive tutorial including:
1. Learning objectives
2. Prerequisites and setup
3. Step-by-step instructions
4. Code examples with explanations
5. Common pitfalls and solutions
6. Practice exercises
7. Next steps and advanced topics
.exec

.user Create a file called "examples_<<topic>>.<<language>>" with working code examples for the tutorial:
.exec

.user Generate a file called "exercises_<<topic>>.md" with practice exercises and solutions:
.exec
```

**Usage:**
```bash
keprompt -e education/code_tutorial \
  --param topic "REST_API_development" \
  --param language "python" \
  --param skill_level "intermediate" \
  --param length "comprehensive" \
  --debug
```

## Business & Productivity

### Meeting Minutes Generator

**File: `prompts/business/meeting_minutes.prompt`**
```
.# Meeting Minutes Generator
.llm {"model": "gpt-4o"}
.system You are an executive assistant skilled at creating professional, actionable meeting minutes.

.user Create a file called "minutes_<<meeting_date>>.md" with meeting minutes based on these notes:
.include <<notes_file>>

Meeting details:
- Date: <<meeting_date>>
- Attendees: <<attendees>>
- Meeting type: <<meeting_type>>

Create professional meeting minutes with:
1. Meeting overview and objectives
2. Key discussion points
3. Decisions made
4. Action items with owners and deadlines
5. Next steps and follow-up meetings
.exec

.user Extract action items into a file called "action_items_<<meeting_date>>.md":
.exec

.user Create a file called "followup_email_<<meeting_date>>.md" with a follow-up email template:
.exec
```

**Usage:**
```bash
keprompt -e business/meeting_minutes \
  --param notes_file "raw_meeting_notes.txt" \
  --param meeting_date "2024-01-15" \
  --param attendees "Alice,Bob,Charlie" \
  --param meeting_type "project_planning" \
  --debug
```

### Business Proposal Generator

**File: `prompts/business/proposal_generator.prompt`**
```
.# Business Proposal Generator
.llm {"model": "gpt-4o"}
.system You are a business development expert who creates compelling, professional proposals that win clients.

.user Create a file called "proposal_<<client_name>>.md" with a business proposal.

Requirements:
.include <<requirements_file>>

Create a business proposal for:
- Client: <<client_name>>
- Project: <<project_description>>
- Budget range: <<budget_range>>
- Timeline: <<timeline>>
- Our company: <<company_name>>

Generate a comprehensive proposal including:
1. Executive summary
2. Understanding of client needs
3. Proposed solution and approach
4. Timeline and milestones
5. Team and qualifications
6. Investment and pricing
7. Terms and next steps
.exec

.user Create a file called "presentation_outline_<<client_name>>.md" with a presentation outline based on the proposal:
.exec

.user Generate a file called "client_questions_<<client_name>>.md" with follow-up questions to ask the client:
.exec
```

**Usage:**
```bash
keprompt -e business/proposal_generator \
  --param client_name "TechCorp" \
  --param project_description "Mobile app development" \
  --param budget_range "50k-100k" \
  --param timeline "6_months" \
  --param company_name "DevStudio" \
  --param requirements_file "client_requirements.txt" \
  --debug
```

## Subprocess Integration Examples

When using keprompt as a subprocess, the stdout should contain the actual result, not status messages. Here are examples optimized for subprocess usage:

### SQL Query Generator

**File: `prompts/database/sql_generator.prompt`**
```
.# SQL Query Generator
.llm {"model": "gpt-4o"}
.system You are a PostgreSQL database expert. You create clean, efficient SQL statements.

.user Here is the current schema:
.include <<schema_file>>

Generate SQL to add a user with:
Name: <<name>>
Email: <<email>>
Age: <<age>>
Address: <<address>>
Phone: <<phone>>
.exec
```

**Usage in subprocess:**
```bash
# Returns clean SQL on stdout
sql_query=$(keprompt -e database/sql_generator \
  --param schema_file "db_schema.sql" \
  --param name "John Smith" \
  --param email "john@example.com" \
  --param age "36" \
  --param address "1234 Long St, Short Town, GA 33000" \
  --param phone "305-999-3338")

echo "$sql_query" | psql mydb
```

### API Response Parser

**File: `prompts/api/response_parser.prompt`**
```
.# API Response Parser
.llm {"model": "gpt-4o-mini"}
.system You are a data extraction expert. Extract specific information from API responses and return only the requested data.

.user Extract the following fields from this API response:
.include <<response_file>>

Extract and return only:
- User ID: <<field1>>
- Status: <<field2>>
- Created Date: <<field3>>

Return as JSON format.
.exec
```

**Usage in subprocess:**
```bash
# Returns clean JSON on stdout
parsed_data=$(keprompt -e api/response_parser \
  --param response_file "api_response.json" \
  --param field1 "user_id" \
  --param field2 "status" \
  --param field3 "created_at")

echo "$parsed_data" | jq '.user_id'
```

### Text Summarizer

**File: `prompts/text/summarizer.prompt`**
```
.# Text Summarizer
.llm {"model": "claude-3-haiku-20240307"}
.system You are a text summarization expert. Create concise, accurate summaries.

.user Summarize this text in exactly <<word_count>> words:
.include <<input_file>>

Focus on: <<focus_areas>>
.exec
```

**Usage in subprocess:**
```bash
# Returns clean summary on stdout
summary=$(keprompt -e text/summarizer \
  --param input_file "long_article.txt" \
  --param word_count "50" \
  --param focus_areas "key findings and conclusions")

echo "$summary" > brief_summary.txt
```

## Usage Tips

### Running Multiple Examples

Create a script to run multiple related prompts:

```bash
#!/bin/bash
# comprehensive_analysis.sh

PROJECT_NAME="my_project"
DATE=$(date +%Y-%m-%d)

echo "Running comprehensive project analysis..."

# Code review
keprompt -e coding/code_review --param codefile "src/main.py" --log "review_$DATE"

# Repository analysis  
keprompt -e coding/repo_analysis --log "repo_$DATE"

# Generate documentation
keprompt -e content/tech_docs --param project_name "$PROJECT_NAME" --param source_file "README.md" --log "docs_$DATE"

# Create release notes
keprompt -e automation/release_notes --param version "1.2.0" --param product_name "$PROJECT_NAME" --param release_date "$DATE" --param last_version "v1.1.0" --log "release_$DATE"

echo "Analysis complete! Check the logs/ directory for detailed output."
```

### Customizing Examples

All examples can be customized by:

1. **Modifying the system prompt** to change the AI's role and expertise
2. **Adding or removing analysis sections** in the user prompts
3. **Changing the model** to balance cost vs. quality
4. **Adding custom functions** for specific data sources or tools
5. **Adjusting output formats** by modifying the writefile commands

### Cost Optimization

For development and testing:
- Use `gpt-4o-mini` instead of `gpt-4o`
- Use `claude-3-haiku-20240307` instead of `claude-3-5-sonnet-20241022`
- Test with smaller files first
- Use `--debug` to monitor token usage

For production:
- Use higher-quality models for final output
- Batch similar requests
- Cache results when appropriate
- Monitor costs with `keprompt -m` to check pricing

These examples demonstrate the power and flexibility of keprompt for automating complex, multi-step workflows across various domains. Each can be adapted to your specific needs and integrated into larger automation systems.
