---
name: multi-agent-orchestration
description: >
  Design and build hub-and-spoke multi-agent systems with Hermes profiles,
  cron jobs, and shared knowledge bases for autonomous business operations.
  Covers specialist-mode architecture, inter-mode communication, scheduled
  automation, and cross-profile orchestration patterns.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, orchestration, profiles, cron, automation, hub-and-spoke, business-automation]
    related_skills: [hermes-agent, plan, spike]
---

# Multi-Agent Orchestration

Build autonomous multi-agent systems where specialist agents ("modes") work collaboratively under a central orchestrator, with scheduled automation and a shared knowledge base.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOU (User/Person)                          │
│                         ↕                                    │
│              HERMES ORCHESTRATOR (this session)              │
│                         ↕                                    │
│    ┌─────────┬──────────┬───────────┬──────────────────┐  │
│    │ MODE A  │  MODE B  │  MODE C   │     MODE D       │  │
│    └─────────┴──────────┴───────────┴──────────────────┘  │
│                         ↕                                    │
│              SHARED KNOWLEDGE BASE                           │
└─────────────────────────────────────────────────────────────┘
```

## When to Use This Pattern

- Building autonomous business operations (SaaS ideation, content pipelines, financial tracking, research)
- Multiple distinct workflows that need to run independently but share learnings
- Scheduled automation combined with on-demand specialist access
- Self-evolving systems where one mode discovers capabilities that others adopt

## When NOT to Use This Pattern

- Simple single-task jobs (overhead of profiles/cron is not worth it)
- Tight real-time loops requiring sub-100ms coordination (profiles have startup cost)
- State where a single monolithic prompt or `delegate_task` suffices

## The Profile-as-Mode Pattern

Each "mode" is a Hermes **profile** with its own isolated memory, skills, and context.

### Creating Specialist Profiles

```bash
# Create profiles for each specialist mode
hermes profile create ideation      # Business builder
hermes profile create content-gen   # Video/content factory
hermes profile create financial     # Financial advisor
hermes profile create ai-research   # News scanner / upgrader
```

### Configuring Each Profile

Write an `AGENTS.md` in each profile directory to define that agent's personality, capabilities, and workflow:

```
~/.hermes/profiles/ideation/AGENTS.md
~/.hermes/profiles/content-gen/AGENTS.md
~/.hermes/profiles/financial/AGENTS.md
~/.hermes/profiles/ai-research/AGENTS.md
```

**AGENTS.md structure per profile:**
- **System prompt**: Who this agent is, its mission, core competencies
- **Trigger conditions**: When this mode should activate (scheduled or on-demand)
- **Capabilities list**: What it can do
- **Output artifacts**: Where it writes results
- **Cross-mode communication**: How it feeds into other modes

See `references/agentic-hub-example.md` for a complete worked example.

### Switching Modes

```bash
# Direct profile switch (preferred for live work)
hermes --profile ideation chat

# One-shot mode execution
hermes --profile ideation chat -q "Find me SaaS ideas in the fitness AI space"

# The orchestrator can also switch mode by spawning the profile:
terminal(command="hermes --profile financial chat -q 'Morning market briefing'")
```

## Shared Knowledge Base

All modes write to and read from a shared directory, preventing re-invention and enabling cross-pollination.

### Directory Structure

```
~/Workspace/agentic-hub/
├── agents/
│   ├── ideation/output/
│   ├── content-gen/output/
│   ├── financial/output/
│   └── AI-research/output/
└── shared/
    ├── knowledge-base/
    │   ├── tool-evaluations/     # Cost/performance benchmarks
    │   ├── market-intelligence/  # Trends, competitor analysis
    │   ├── lessons-learned/      # What worked/failed
    │   ├── capabilities/         # New workflows/templates
    │   └── integrations/         # Cross-mode connection patterns
    ├── skills/                   # Shared Hermes skills
    └── output/                   # Final deliverables
```

### Knowledge Flow

| Mode | Writes | Reads |
|------|--------|-------|
| **Ideation** | Business ideas, automation blueprints, MVP specs | Content formats (content-gen), market data (financial), new tools (AI research) |
| **Content Gen** | Videos, scripts, templates, performance data | Business ideas to create marketing for (ideation) |
| **Financial** | Portfolio reports, alerts, market learnings | Business models to price (ideation), new fintech tools (AI research) |
| **AI Research** | Digests, tool evaluations, capability suggestions | ALL — upgrades every mode |

## Scheduled Automation with Cron

Use the `cronjob` tool (not `cron` CLI) to create durable, recurring tasks that survive the conversation.

### Creating Scheduled Jobs

```python
cronjob(action="create",
    name="ai-research-morning-digest",
    schedule="0 7 * * *",  # Daily at 7:00 AM
    model={"model": "moonshotai/kimi-k2.6"},
    prompt="""You are the AI Research Agent...""")
```

### Critical Pitfall: Rate Limits with Subagents

**DO NOT use `delegate_task` for mode work** — it can hit rate limits (429) when spawning subagents, and the error is silent from the user's perspective. Instead, use direct `hermes --profile <name>` invocation or the `cronjob` tool with a profile-specific model override.

### Recommended Cron Schedule Pattern

| Job | Schedule | Purpose |
|-----|----------|---------|
| Morning brief | `30 6 * * 1-5` | Market/financial snapshot (weekdays) |
| Daily digest | `0 7 * * *` | News/research scan (every day) |
| Weekly scan | `0 9 * * 1` | Opportunity/ideation review (Mondays) |
| Monthly batch | `0 10 1 * *` | Content production batch (1st of month) |

## Pipeline Chains (Cross-Mode Workflows)

Chain multiple modes so the output of A feeds into B:

```
IDEATION ──► Generates business idea "AI Discord Bot"
     │
     ├──► CONTENT GEN creates demo videos
     ├──► FINANCIAL prices and models it
     ├──► AI RESEARCH finds best frameworks
     └──► IDEATION refines based on all feedback
```

### Implementing Pipeline Chains

```python
# Step 1: Run ideation (save output to shared directory)
terminal(command="hermes --profile ideation chat -q 'Generate 3 SaaS ideas and save to ~/Workspace/agentic-hub/agents/ideation/output/'")

# Step 2: Feed ideation output to content gen
terminal(command="hermes --profile content-gen chat -q 'Read the latest ideation output and create marketing content'")

# Step 3: Financial evaluation
terminal(command="hermes --profile financial chat -q 'Read the latest ideation output and assess pricing/unit economics'")
```

## Token Efficiency Rules

- **Each profile is isolated** — no context pollution between modes
- **Cron jobs run on schedule** — not every request, reducing token burn
- **Shared knowledge base** prevents re-work (read past outputs instead of re-researching)
- **Pipeline mode** chains tasks efficiently without redundant context
- **Prefer `hermes --profile` over `delegate_task`** for mode work to avoid rate limits and keep context clean

## Orchestrator Commands (Conventions)

These are user-side commands, not Hermes CLI commands:

- `/mode [name]` — Switch context to a specific mode
- `/broadcast` — Send same task to multiple modes
- `/pipeline` — Chain modes: output of A → input of B → input of C
- `/status` — Check all mode health and recent outputs
- `/upgrade` — Trigger AI Research to scan for new capabilities

## Verification

After setting up the hub:
- [ ] All profiles created and have `AGENTS.md`
- [ ] Shared knowledge base directory exists
- [ ] At least one cron job scheduled and confirmed via `hermes cron list`
- [ ] Tested mode switching with `hermes --profile <name>`
- [ ] First cross-mode pipeline completed end-to-end
