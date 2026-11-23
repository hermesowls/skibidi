---
name: dashboard-cloudflare-tunnels
description: Use when exposing dashboards via Cloudflare tunnels.
version: 1.0.0
author: Skibidi
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [dashboard, cloudflare, tunnel, remote-access, verification]
---

# Dashboard Cloudflare Tunnels

Use this skill when Amar asks for a temporary public link to a locally running dashboard, web UI, table, or browser-accessible artifact, especially from a Telegram/remote context.

## Core workflow

1. Identify the local service port and verify it is listening.
2. Verify the service locally with `GET` before exposing it.
3. Before starting any public tunnel, verify an appropriate authentication gate. Hermes loopback mode may inject an admin session token into HTML (`auth_required:false`); NEVER expose that mode or use a localhost Host override to bypass protection. Current official dashboard docs explicitly restrict the bundled basic/password provider to trusted networks/VPN, not the public internet. For public dashboards require Nous/OIDC or an independently approved internet-facing access gate. If Nous login is absent, ask the user to run `hermes auth add nous` (or `hermes setup`) before registration. Set the exact `dashboard.public_url` through supported configuration commands; it engages native auth even on a loopback bind. Then start a Cloudflare quick tunnel to the gated local URL.
4. Read the generated `https://*.trycloudflare.com` URL from the tunnel logs.
5. Verify the public URL with `GET` and a page-specific marker/title.
6. Kill broken duplicate tunnels so the user only receives a working link.
7. Warn the user that quick tunnel links are sensitive temporary public access URLs.

## Hermes dashboard pattern

Hermes dashboard commonly listens on `127.0.0.1:9119`. Verify both root and health locally:

```bash
pgrep -af 'hermes dashboard|9119' || true
lsof -nP -iTCP:9119 -sTCP:LISTEN || true
curl -i --max-time 10 http://127.0.0.1:9119/
curl -i --max-time 10 http://127.0.0.1:9119/api/health
```

Only AFTER independently verifying the public-appropriate login gate, a localhost Host header override can solve Host validation errors. Prefer configuring the exact `dashboard.public_url` instead. Never apply this workaround to ungated loopback mode:

```bash
/Users/admin/.local/bin/cloudflared tunnel \
  --url http://127.0.0.1:9119 \
  --http-host-header 127.0.0.1:9119
```

Without the Host header override, the quick tunnel may be created successfully but the dashboard backend can return `400` through Cloudflare.

## Verification rule

Do not rely on `HEAD` alone. Some dashboard routes allow `GET` but return `405 Method Not Allowed` for `HEAD`. Verify with a real `GET` and a marker, for example:

```bash
python3 - <<'PY'
import re, urllib.request
url='https://REPLACE.trycloudflare.com'
with urllib.request.urlopen(url, timeout=25) as r:
    body=r.read(2000).decode('utf-8','ignore')
    title=re.search(r'<title>(.*?)</title>', body, re.I|re.S)
    print('status', r.status)
    print('title', title.group(1).strip() if title else '[no title]')
    print('dashboard_marker', 'Hermes Agent - Dashboard' in body)
PY
```

## Safety

A quick tunnel is public to anyone with the URL. Never paste secrets from the page or logs. If a tunnel is wrong, duplicate, or points at the wrong service, kill it before giving Amar the final link.

## Reference files

- `references/session-patterns.md` — condensed notes from real dashboard tunnel sessions and common failure modes.
