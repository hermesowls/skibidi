---
name: hermes-dashboard-plugins
description: Use when building Hermes dashboard tabs/plugins.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, dashboard, plugins, ui, fastapi, react]
---

# Hermes Dashboard Plugins

Use this when building or debugging user-level Hermes dashboard tabs, cards, or workflow monitoring UIs without editing Hermes core.

Prefer dashboard plugins for project-specific admin surfaces such as trading trackers, tenant admin panels, workflow monitors, and custom visual controls.

## Standard Plugin Layout

```text
~/.hermes/plugins/<plugin-name>/plugin.yaml
~/.hermes/plugins/<plugin-name>/dashboard/manifest.json
~/.hermes/plugins/<plugin-name>/dashboard/plugin_api.py
~/.hermes/plugins/<plugin-name>/dashboard/dist/index.js
~/.hermes/plugins/<plugin-name>/dashboard/dist/style.css
```

The plugin root `plugin.yaml` lets `hermes plugins enable <plugin-name>` discover and enable the plugin. The dashboard `manifest.json` defines the visible tab, bundle, CSS, and API file.

## Frontend Pattern

Use the dashboard plugin SDK:

```js
const SDK = window.__HERMES_PLUGIN_SDK__;
const React = SDK.React;
const h = React.createElement;
window.__HERMES_PLUGINS__.register('<plugin-name>', PluginPage);
```

For plugin API calls, use `SDK.fetchJSON('/api/plugins/<plugin-name>/<route>')`. Do not rely on plain `fetch()` as the primary path, because it can 401 under dashboard auth modes.

## Backend Pattern

Expose FastAPI routes from `dashboard/plugin_api.py`:

```python
from fastapi import APIRouter
router = APIRouter()

@router.get('/data')
async def get_data():
    return {'ok': True}
```

Routes mount under `/api/plugins/<plugin-name>/`.

## Verification Checklist

1. `node --check dashboard/dist/index.js`.
2. Import/call backend with the Hermes venv if the system Python lacks FastAPI.
3. `hermes plugins enable <plugin-name>`.
4. Restart dashboard if the plugin route/API does not appear.
5. Browser-verify the route and check console/API errors.

## References

See `references/trading-tracker-plugin.md` for the trading tracker implementation pattern and data sources.
