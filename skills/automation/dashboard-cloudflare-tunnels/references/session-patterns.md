# Session Patterns for Dashboard Cloudflare Tunnels

## Hermes dashboard through Cloudflare

Observed reliable pattern:

- Local dashboard healthy on `127.0.0.1:9119` with page title `Hermes Agent - Dashboard` and `/api/health` returning JSON.
- Plain Cloudflare tunnel to `http://127.0.0.1:9119` can create a valid trycloudflare URL but still return dashboard-side `400` publicly.
- Re-run tunnel with `--http-host-header 127.0.0.1:9119` to preserve the expected local Host header.
- `curl -I` / HEAD may return `405` even when the dashboard is healthy because the app only allows GET on the route.
- Public GET verification should check both HTTP 200 and a page marker/title before reporting the link.

## Cleanup

When multiple tunnel attempts exist, kill the failed/duplicate tunnel processes and report only the verified working URL.

## User-facing wording

Keep the final response short:

- give the verified URL,
- state `200 OK` / page marker,
- mention the local port,
- warn not to share the link publicly.
