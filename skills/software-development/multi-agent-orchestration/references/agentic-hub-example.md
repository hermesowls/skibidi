# Example: Agentic Hub

This is the exact architecture built in a real session. Use it as a template for your own multi-agent system.

## User's Request

> "Build out your agentic workflow... I need 4 different modes from you."
> 1. Ideation for SaaS/automations
> 2. Content generation (Higgsfield/Remotion)
> 3. Financial advisor (stocks/options/Trump tracking)
> 4. AI research + self-improvement

## Resulting Architecture

### 4 Profiles Created
- `ideation` — SaaS business builder, automation blueprints
- `content-gen` — Video generation, social media, YouTube automation
- `financial` — Stocks, options, crypto, market tracking
- `ai-research` — AI news, papers, self-improvement

### 4 Cron Jobs Scheduled
| Job | Schedule |
|-----|----------|
| `ai-research-morning-digest` | Daily at 7:00 AM |
| `financial-morning-briefing` | Weekdays at 6:30 AM |
| `ideation-opportunity-scan` | Mondays at 9:00 AM |
| `content-gen-batch-production` | 1st of month at 10:00 AM |

### Key Learnings from This Session

1. **Rate limit handling**: `delegate_task` hit 429 errors from the model provider. The fix: use `hermes --profile <name>` direct invocation instead, which avoids subagent overhead and rate limits entirely.

2. **Profile AGENTS.md**: Each profile needs its own `AGENTS.md` file at `~/.hermes/profiles/<name>/AGENTS.md` to define that agent's personality. This is separate from the main project's `AGENTS.md`.

3. **Shared knowledge directory**: `~/Workspace/agentic-hub/shared/knowledge-base/` serves as the cross-cutting memory for all modes.

4. **Orchestrator script**: A shell script (`orchestrator.sh`) provides an interactive menu for mode selection and pipeline execution.

## Minimal Reproduction

```bash
# 1. Create a project directory
mkdir -p ~/Workspace/agentic-hub && cd ~/Workspace/agentic-hub

# 2. Create profiles (run for each mode)
hermes profile create ideation
hermes profile create content-gen
hermes profile create financial
hermes profile create ai-research

# 3. Write AGENTS.md in each profile dir
echo "<system prompt>" > ~/.hermes/profiles/ideation/AGENTS.md

# 4. Create shared knowledge base
mkdir -p shared/knowledge-base/{tool-evaluations,market-intelligence,lessons-learned,capabilities,integrations}

# 5. Schedule cron jobs (via hermes cron create or the cronjob tool)
```
