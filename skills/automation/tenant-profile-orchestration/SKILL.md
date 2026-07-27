---
name: tenant-profile-orchestration
description: Use when partitioning Hermes for multi-user/project tenants.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, profiles, multi-tenant, gateway, isolation, permissions, telegram, imessage]
---

# Tenant Profile Orchestration

Use this when Amar wants multiple outside users or projects to work through Hermes while keeping memory, context, secrets, skills, automations, and outputs siloed.

## Core Architecture

Default to **one Hermes profile per user/project**, with the `default` profile treated as Amar's admin/master control plane.

Each tenant profile owns its own:

1. `config.yaml` for model, tools, terminal backend, approvals, gateway config.
2. `.env` for that tenant/project's secrets only.
3. `SOUL.md` for tenant/project-specific operating instructions.
4. `state.db`, memories, sessions, transcripts, skills, cron jobs, plugins, and logs.
5. Project workspace folder, set explicitly with `terminal.cwd`.

Do **not** let tenant project work happen inside the `default` profile unless Amar explicitly says to.

## Recommended Setup Flow

1. Create the profile:

```bash
hermes profile create <tenant-profile> --description "<role and project scope>"
```

2. Create an explicit workspace:

```bash
mkdir -p /Users/admin/Projects/hermes-tenants/<tenant-profile>
<tenant-profile> config set terminal.cwd /Users/admin/Projects/hermes-tenants/<tenant-profile>
```

3. Configure only the needed tools:

```bash
<tenant-profile> tools enable browser
<tenant-profile> tools enable web
<tenant-profile> tools enable terminal
<tenant-profile> tools enable file
<tenant-profile> tools enable cronjob
```

4. Put project/user secrets in the profile-scoped env file only:

```bash
<tenant-profile> config env-path
```

5. Add a restrictive `SOUL.md` scoped to the tenant/project:

```md
You are the automation agent for <tenant/project>.
Work only in this tenant's project workspace.
Do not access or modify other Hermes profiles, memories, skills, projects, or credentials.
When uncertain about permissions, ask Amar/admin.
```

## Gateway Models

### Separate Gateway Per Profile

Use when each tenant gets its own Telegram/Discord/Slack bot token or hard crash isolation matters.

```bash
<tenant-profile> setup
<tenant-profile> gateway install
<tenant-profile> gateway start
```

Pros: stronger process isolation, simpler token ownership, independent restarts.
Cons: more processes and gateway services.

### Multiplexed Gateway With Profile Routes

Use when one default gateway should route messages from Telegram/iMessage/Discord to tenant profiles.

```bash
hermes config set gateway.multiplex_profiles true
hermes gateway restart
```

Route by platform identifiers in default profile config:

```yaml
gateway:
  multiplex_profiles: true
  profile_routes:
    - name: tenant-telegram
      platform: telegram
      chat_id: "<telegram_chat_id>"
      profile: <tenant-profile>

    - name: tenant-discord-channel
      platform: discord
      guild_id: "<guild_id>"
      chat_id: "<channel_id>"
      profile: <tenant-profile>

    - name: tenant-imessage
      platform: imessage
      chat_id: "<imessage_sender_or_chat_id>"
      profile: <tenant-profile>
```

Routed turns resolve the target profile's config, skills, memory, SOUL, sessions, and provider keys.

## Isolation Guarantees and Pitfalls

Profiles isolate Hermes state; they do **not** sandbox the whole filesystem when using the local terminal backend. For true tenant security, combine profiles with a stronger boundary:

1. Basic: profile + explicit `terminal.cwd` + restrictive SOUL.
2. Better: profile + Docker/SSH terminal backend.
3. Stronger: profile + separate OS user.
4. Strongest: separate VPS/container per tenant.

Avoid `--clone-all` for tenants because it can copy old memories, cron jobs, plugins, and operational baggage. Use a blank profile or `--clone` only when shared config/skills are intentional.

## Admin Pattern

Keep `default` as Amar/admin. Use it for:

1. Profile creation/deletion.
2. Gateway route management.
3. Dashboard monitoring.
4. Permission approvals/revocations.
5. Cross-tenant status checks.

Tenant profiles should have their own Discord delivery target or channel mapping and should not inherit Amar's private trading or business secrets unless explicitly needed.

## References

See `references/multi-user-routing.md` for a concrete setup checklist and example profile route layout.
