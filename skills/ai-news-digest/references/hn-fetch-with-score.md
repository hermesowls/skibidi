# HN Shell Fetch with Score Filtering

A refined shell-based fetch recipe for Hacker News that captures all story fields using `sed` for JSON key extraction, without relying on `python` or `execute_code`.

## Command (AI-filtered, 100 stories)

```bash
curl -sL "https://hacker-news.firebaseio.com/v0/topstories.json" | tr -cd '0-9,' | tr ',' '\n' | head -100 | while IFS= read -r id; do
  story=$(curl -sL "https://hacker-news.firebaseio.com/v0/item/${id}.json")
  title=$(echo "$story" | sed -n 's/.*"title":"\([^"]*\)".*/\1/p')
  if [ -n "$title" ]; then
    url=$(echo "$story" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')
    score=$(echo "$story" | sed -n 's/.*"score":\([0-9]*\).*/\1/p')
    echo "$title | $url | Score: $score"
  fi
done | grep -iE "(AI|LLM|GPT|OpenAI|Anthropic|Claude|Gemini|model|neural|deep.?learning|transformer|LLaMa|Mistral|Llama|Agent|AGI|Mythos)" || echo "No AI stories found in first 100"
```

## Notes

- `sed -n 's/.*"key":"\([^"]*\)".*/\1/p'` is a reliable pattern for extracting string values from JSON in shell.
- `tr -cd '0-9,'` strips whitespace and brackets from the HN ID list, making it safe for `tr ',' '\n'`.
- This approach was proven effective on macOS 12.7.6 (`mnc` environment) during cron execution where `execute_code` was unavailable.
