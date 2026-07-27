# Multi-User Hermes Routing Checklist

Use this checklist when Amar wants a user to text Hermes from Telegram/iMessage and work in an isolated project.

## Desired Shape

Message flow:

```text
Tenant texts Telegram/iMessage
→ default gateway routes message to tenant profile
→ tenant profile loads only its own config, memory, skills, SOUL, .env, sessions
→ tools start in tenant workspace
→ outputs deliver to tenant-owned Discord/channel
```

## Create Tenant

```bash
hermes profile create sports-betting-user1 --description "Sports betting automation profile for one assigned user. Builds scraping, browser automation, odds analysis, and Discord reports."
mkdir -p /Users/admin/Projects/hermes-tenants/sports-betting-user1
sports-betting-user1 config set terminal.cwd /Users/admin/Projects/hermes-tenants/sports-betting-user1
```

Use blank profiles when possible. Avoid `--clone-all`; it copies operational state that can cause cross-project bleed.

## Tenant Secrets

Use only the tenant env path:

```bash
sports-betting-user1 config env-path
```

Put only tenant/project secrets there, such as Telegram/Discord tokens, odds APIs, browser automation credentials, or scraper credentials. Do not put tenant keys in `default` unless the default profile must administer that integration.

## Multiplexed Gateway Routing

In default profile config:

```yaml
gateway:
  multiplex_profiles: true
  profile_routes:
    - name: sports-betting-user1-telegram
      platform: telegram
      chat_id: "<tenant_telegram_chat_id>"
      profile: sports-betting-user1

    - name: sports-betting-user1-imessage
      platform: imessage
      chat_id: "<tenant_imessage_sender_or_chat_id>"
      profile: sports-betting-user1

    - name: sports-betting-user1-discord-output
      platform: discord
      guild_id: "<guild_id>"
      chat_id: "<channel_id>"
      profile: sports-betting-user1
```

Then restart the default gateway:

```bash
hermes config set gateway.multiplex_profiles true
hermes gateway restart
```

## One Gateway Per Profile Alternative

Use this when each tenant has its own bot token or you want process-level isolation:

```bash
sports-betting-user1 setup
sports-betting-user1 gateway install
sports-betting-user1 gateway start
```

## Hard Isolation Escalation

Profiles isolate Hermes data, not filesystem permissions. If tenant users can run browser automation, scraping, downloads, or shell commands, consider one of:

1. Docker terminal backend per profile.
2. SSH terminal backend to a tenant VM/container.
3. Separate macOS/Linux user per tenant.
4. Separate VPS/container per tenant.

## Dashboard Admin View Idea

A future admin tab should show:

- Profile name and owner.
- iMessage/Telegram/Discord route bindings.
- Workspace path and terminal backend.
- Enabled toolsets.
- Env present/missing status without revealing secrets.
- Cron jobs and running workflows.
- Memory/session counts.
- Last active timestamp.
- Discord output destination.
- Isolation level: local cwd, Docker, SSH, OS user, VPS.
