# FXStreet News Extraction & Fallbacks

## FXStreet Algolia Payload Technique
FXStreet (https://www.fxstreet.com/news) is a Next.js application that embeds its news feed as a JSON payload inside `<script>` tags. No API key is required to extract headlines.

### Extraction Command
```bash
curl -sL https://www.fxstreet.com/news | grep -o '"Title":"[^"]*"' | head -10 | sed 's/"Title":"//;s/"//'
```

### Why It Works
The page hydrates with an Algolia search response stored in `window.__next_f`. The `Title` fields are plaintext strings in the HTML, so a simple `grep` extracts them reliably.

### Example Output
```
Breaking:Fed Chair Warsh says US will be a big winner in AI
Lagarde speech:Risks are more broadly balanced than a few weeks ago
European Central Bank:July risks reduced on softer data – Nordea
BoE's Bailey:Rate cuts off the table at the moment
ISM Manufacturing PMI expected to underline resilient US manufacturing activity
Japanese Yen:Softer footing risk as intervention fades – DBS
Gold steadies above $4,000 as traders await Fed Chair Warsh's speech
US Dollar:Modest upside risk with Sintra focus – OCBC
US equities:AI-led earnings support – HSBC
Euro hits one-year low vs. British Pound after Eurozone inflation misses forecasts
```

### Pitfalls
- **Fragility:** If FXStreet changes their Next.js bundle structure or switches to a different hydration strategy, `grep` will return nothing.
- **Rate limiting:** Heavy scraping may trigger Cloudflare or similar protections. Use `-A "Mozilla/5.0"`, add delays, or cache results.

## Fallback News Sources
If FXStreet extraction fails, use these alternatives:

| Source | URL | Format | Notes |
|--------|-----|--------|-------|
| Hacker News | https://news.ycombinator.com | HTML | Tech/business bias; headlines are `<a class="titleline">` |
| TechCrunch RSS | https://feeds.feedburner.com/TechCrunch | RSS/XML | Standard RSS; parse `<title>` tags |
| SEC EDGAR | https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent | HTML | Requires `User-Agent` header with company info; blocks generic bots |
| Reuters Topics | https://www.reuters.com/business/ | HTML | Often blocked by JS challenge; less reliable |

## Priority for Market Brief
When selecting headlines for the morning brief, rank by estimated market impact:
1. Central bank announcements (Fed, ECB, BOE, BOJ)
2. Geopolitical / policy events (tariffs, sanctions, elections, major legislation)
3. Earnings surprises or big-tech guidance changes
4. Commodity price shocks (oil, gold)
5. Regional market circuit breakers or flash crashes
