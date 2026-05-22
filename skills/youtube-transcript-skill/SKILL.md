---
name: youtube-transcript
description: Extracts the full transcript from a YouTube video using the Apify actor faVsWy9VTSNVIhWpR, saves it to a .md file, commits it to git, then produces a structured summary with key takeaways and direct quotes. Invoke when the user provides a YouTube URL.
---

# YouTube Transcript Extractor + Summariser

## Overview
Given any YouTube URL, this skill:
1. Calls the Apify actor `faVsWy9VTSNVIhWpR` to fetch the raw transcript
2. Parses the response into clean paragraphs and saves a `.md` file
3. Commits and pushes the file to git
4. Reads the transcript and produces a structured summary with key takeaways

## Prerequisites
`APIFY_TOKEN` must be set in the environment. If it is not set, stop and tell the user:
> "APIFY_TOKEN is not set. See the Token Setup section below."

---

## Execution Steps

### Step 1 — Extract the video ID

Accept any of these URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://www.youtube.com/watch?v=VIDEO_ID&si=...` (strip query params after `v=`)
- `https://youtu.be/VIDEO_ID`
- `https://youtu.be/VIDEO_ID?si=...` (strip `?si=...`)
- `https://www.youtube.com/shorts/VIDEO_ID`

The video ID is the 11-character alphanumeric string. Use it as `VIDEO_ID` throughout.

### Step 2 — Check the token

```bash
echo "${APIFY_TOKEN:0:8}..."
```

If empty or unset, halt and show the **Token Setup** section.

### Step 3 — Call the Apify actor and save raw JSON

Run the following, replacing `VIDEO_ID` and `YOUTUBE_URL`:

```bash
curl -s -X POST \
  "https://api.apify.com/v2/acts/faVsWy9VTSNVIhWpR/run-sync-get-dataset-items?token=$APIFY_TOKEN&format=json" \
  -H "Content-Type: application/json" \
  -d '{"videoUrl": "YOUTUBE_URL"}' \
  --max-time 120 \
  -o /tmp/transcript-VIDEO_ID-raw.json
```

**Important:** The input field is `videoUrl` (not `urls`, not `url`). Use the canonical `https://www.youtube.com/watch?v=VIDEO_ID` form as the value even if the user supplied a `youtu.be` short link.

Check the response:
```bash
head -c 200 /tmp/transcript-VIDEO_ID-raw.json
```

If it contains `"error"` or is empty, report the error and stop.

### Step 4 — Parse and write the Markdown file

Run this Python script (replacing `VIDEO_ID` in the two string literals):

```python
import json, datetime, re

with open("/tmp/transcript-VIDEO_ID-raw.json") as f:
    data = json.load(f)

segments = data[0]["data"]

lines = []
for seg in segments:
    t = seg["text"].strip()
    t = re.sub(r'\[.*?\]', '', t).strip()   # strip [music], [applause], etc.
    if t:
        lines.append(t)

full_text = " ".join(lines)

# Chunk into ~600-char paragraphs on sentence boundaries
sentences = re.split(r'(?<=[.!?])\s+', full_text)
paragraphs, chunk = [], []
for s in sentences:
    chunk.append(s)
    if len(" ".join(chunk)) > 600:
        paragraphs.append(" ".join(chunk))
        chunk = []
if chunk:
    paragraphs.append(" ".join(chunk))

body = "\n\n".join(paragraphs)
today = datetime.date.today().isoformat()

md = f"""# Transcript: https://www.youtube.com/watch?v=VIDEO_ID

> Extracted on {today} via Apify actor faVsWy9VTSNVIhWpR

---

{body}
"""

out = "/home/user/taste-skill/transcript-VIDEO_ID.md"
with open(out, "w") as f:
    f.write(md)

print(f"Written: {out}")
print(f"Segments: {len(segments)}, Paragraphs: {len(paragraphs)}, Chars: {len(body)}")
```

Use the `Bash` tool to run this as `python3 -c "..."` or write it to a temp file and execute it.

### Step 5 — Commit and push

```bash
cd /home/user/taste-skill
git add transcript-VIDEO_ID.md
git commit -m "$(cat <<'EOF'
feat: add transcript for VIDEO_ID

https://claude.ai/code/session_019WsQjiQuMYD2jXfmiygHfB
EOF
)"
git push -u origin claude/youtube-transcript-extractor-ngjP7
```

### Step 6 — Read the transcript

Use the `Read` tool on `/home/user/taste-skill/transcript-VIDEO_ID.md`.

If the file is longer than 2000 lines, read it in chunks:
- First call: `limit: 2000` (no offset)
- Subsequent calls: `offset: 2000`, `limit: 2000`, etc.
Continue until you have read the full file.

### Step 7 — Produce the structured summary

Output the summary in this exact format:

---

**Speaker / Creator**
Name and context (channel name, credentials, what they do).

**Video context**
One sentence: what the video is about and why it matters.

**Key numbers / metrics**
Bullet list of any concrete figures mentioned (revenue, time, token counts, percentages, prices, etc.).

**Key takeaways**

1. **Takeaway title** — explanation in 2–3 sentences.
   > "Direct quote from the transcript that supports this point."

2. **Takeaway title** — explanation in 2–3 sentences.
   > "Direct quote."

*(Continue for all major points — typically 5–10 takeaways.)*

**Tools / tech mentioned** *(only if relevant)*

| Tool | What it does in this context |
|---|---|
| Tool name | Brief description |

---

Guidelines for the summary:
- Identify the speaker by name if mentioned; otherwise use the channel name or "the presenter".
- Pull at least one direct quote per takeaway — use the exact words from the transcript.
- Capture concrete metrics, prices, time savings, and benchmarks — these are the most re-usable facts.
- If the video covers a step-by-step process, number the steps and preserve the order.
- Keep each takeaway self-contained so it can be read without the others.
- If the video is a product demo or tutorial, include a "How it works" section before the takeaways.

---

## Token Setup

### How to add your Apify token to Claude Code

**Recommended — add it to Claude Code settings permanently**

Edit `~/.claude/settings.json` and add:

```json
{
  "env": {
    "APIFY_TOKEN": "apify_api_XXXXXXXXXXXXXXXXXXXX"
  }
}
```

Restart Claude Code after saving. Never commit this file to git.

**Session-only alternative**

```bash
export APIFY_TOKEN="apify_api_XXXXXXXXXXXXXXXXXXXX"
```

**Where to find your token**
1. Go to console.apify.com
2. Click your avatar → Settings → Integrations
3. Copy the Personal API token (starts with `apify_api_`)

---

## Error Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `"Field input.videoUrl is required"` | Wrong input field name | Use `videoUrl`, not `urls` or `url` |
| `401 Unauthorized` | Token is wrong or expired | Regenerate token at console.apify.com |
| `404 Not Found` | Actor ID typo | Confirm actor ID is `faVsWy9VTSNVIhWpR` |
| Empty dataset `[]` | Video has no captions | Try a video with CC or auto-captions |
| `curl: (28) timeout` | Actor took > 120 s | Re-run; Apify may be under load |
| `KeyError: 'data'` in Python | Unexpected response shape | `print(data[0].keys())` to inspect fields |
| File > 2000 lines | Large transcript | Read in chunks with `offset` and `limit` |
