---
name: youtube-transcript
description: Extracts the full transcript from a YouTube video using the Apify actor faVsWy9VTSNVIhWpR and saves it to a .md file. Invoke when the user provides a YouTube URL and wants the transcript saved locally.
---

# YouTube Transcript Extractor

## Overview
Fetch the transcript of any YouTube video via the Apify actor `faVsWy9VTSNVIhWpR` and write it to a clean Markdown file.

## Prerequisites
`APIFY_TOKEN` must be set in the environment. If it is not set, stop and tell the user:
> "APIFY_TOKEN is not set. See the setup instructions below."
Then show the setup instructions from the **Token Setup** section.

## Execution Steps

### 1. Validate input
- Extract the YouTube URL from the user's message.
- Accept any of these formats:
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - `https://www.youtube.com/shorts/VIDEO_ID`
- Derive a safe filename slug from the URL (use the video ID, e.g. `dQw4w9WgXcQ`).

### 2. Check for the token
Run:
```bash
echo "${APIFY_TOKEN:0:4}..."
```
If the variable is empty or unset, halt and show the Token Setup section.

### 3. Call the Apify actor (synchronous run)
Use a single `curl` command that runs the actor and waits for the result:

```bash
curl -s -X POST \
  "https://api.apify.com/v2/acts/faVsWy9VTSNVIhWpR/run-sync-get-dataset-items?token=$APIFY_TOKEN&format=json" \
  -H "Content-Type: application/json" \
  -d "{\"videoUrl\": \"YOUTUBE_URL\"}"
```

Replace `YOUTUBE_URL` with the actual URL. The response is a JSON array; each element may contain fields such as `transcript`, `text`, `captions`, or `subtitles` depending on the actor version.

### 4. Parse the response
Inspect the JSON response:
- If the HTTP status is not 200 or the body contains `"error"`, report the error message to the user and stop.
- If the array is empty, tell the user the video may have no captions available and stop.
- Extract the transcript text from the first result object. Try these field names in order until one is non-empty:
  1. `transcript`
  2. `text`
  3. `captions`
  4. `subtitles`

### 5. Write the Markdown file
Save the transcript to a file named `transcript-VIDEO_ID.md` in the current working directory.

File structure:
```markdown
# Transcript: [YouTube URL]

> Extracted on [ISO date] via Apify actor faVsWy9VTSNVIhWpR

---

[full transcript text, preserving paragraph breaks]
```

Use the `Write` tool to create the file.

### 6. Confirm to the user
Tell the user:
- The filename that was created.
- How many characters / approximate word count are in the transcript.
- Any warnings (e.g. transcript was auto-generated, no timestamps, etc.) if the API response contains that information.

---

## Token Setup

### How to add your Apify token to Claude Code

**Option A — Persistent (recommended): add it to Claude Code settings**

Run the `/update-config` skill and ask it to add `APIFY_TOKEN` to your environment. Alternatively, edit `~/.claude/settings.json` manually and add:

```json
{
  "env": {
    "APIFY_TOKEN": "apify_api_XXXXXXXXXXXXXXXXXXXX"
  }
}
```

After saving, restart Claude Code for the variable to take effect.

**Option B — Session only: export in your shell before launching Claude Code**

```bash
export APIFY_TOKEN="apify_api_XXXXXXXXXXXXXXXXXXXX"
claude  # or however you launch Claude Code
```

**Where to find your token:**
1. Go to [console.apify.com](https://console.apify.com)
2. Click your avatar → **Settings** → **Integrations**
3. Copy the value under **Personal API token** (starts with `apify_api_`)

---

## Error Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token is wrong or expired | Regenerate token at console.apify.com |
| `404 Not Found` | Actor ID is wrong | Confirm actor ID is `faVsWy9VTSNVIhWpR` |
| Empty dataset returned | Video has no captions | Try a video with CC / auto-captions enabled |
| `timeout` | Actor took > 120 s | Re-run; Apify may be under load |
