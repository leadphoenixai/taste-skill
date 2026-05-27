---
name: linkedin-viral-posts
description: Scrapes viral LinkedIn posts using two Apify actors — one for keyword/hashtag search sorted by engagement, one for LinkedIn's own curated top-content feed. Invoke when the user wants to research what's performing on LinkedIn in a given niche, find content inspiration, or analyse what angles are resonating with a specific audience.
---

# LinkedIn Viral Posts Research

## Purpose

We use this skill to understand what content is actually breaking through on LinkedIn in our target niches. The goal is not just to find popular posts — it's to identify:

- **Angles and framings** that resonate with a specific audience (e.g. CFOs, finance leaders)
- **Post formats** that drive comments vs reactions vs reposts
- **Topics at the intersection** of two audiences (e.g. CFOs who care about AI)
- **Creators** who consistently perform in a niche, worth following or referencing
- **Proof points and data** that the audience responds to (studies, stats, named examples)

This informs content strategy: what to write, how to frame it, and what the audience is already thinking about.

---

## Prerequisites

`APIFY_TOKEN` must be set in the environment. If unset, tell the user and stop.

**Critical:** Apify's free plan allows only ~8GB of concurrent actor memory. Running multiple queries in parallel will trigger a `actor-memory-limit-exceeded` error. Always run queries **sequentially** with a gap between each. If you hit the memory error, check for and abort any stuck runs first (see Error Handling below).

---

## Actor 1 — Keyword Search: `linkedin-viral-posts-finder`

**Actor ID:** `ZmISIboeU1FoHZPxh`
**Use for:** Searching by keyword/topic, sorted by engagement. Best for niche-specific research.
**Cost:** Pay per usage (low)

### API Call

```bash
curl -s -X POST \
  "https://api.apify.com/v2/acts/ZmISIboeU1FoHZPxh/run-sync-get-dataset-items?token=$APIFY_TOKEN&format=json&memory=1024" \
  -H "Content-Type: application/json" \
  -d '{
    "searchQueries": ["QUERY"],
    "maxPosts": 20,
    "sortBy": "engagement",
    "datePosted": "past-month",
    "minEngagement": 20
  }' \
  --max-time 150 \
  -o /tmp/linkedin-SLUG.json
```

### Input Fields

| Field | Values | Notes |
|---|---|---|
| `searchQueries` | Array of strings | Max 85 chars each. **One query per run** to avoid memory limits |
| `maxPosts` | Integer | 15–20 recommended. Higher = slower |
| `sortBy` | `"engagement"`, `"recent"`, `"reactions"`, `"comments"` | Use `"engagement"` for viral research |
| `datePosted` | `"past-24h"`, `"past-week"`, `"past-month"` | `"past-month"` gives best coverage |
| `minEngagement` | Integer | 20–50 filters noise; lower for niche topics |

### Output Fields (per post)

```
postUrl          — direct link to the post
authorName       — poster's name
authorHeadline   — their LinkedIn headline/title
postContent      — full post text
reactionCount    — 👍 likes
commentCount     — 💬 comments
repostCount      — 🔁 reposts
totalEngagement  — sum of all three
postedDate       — ISO timestamp
```

### Sequential Execution Pattern

Run one query at a time. Wait 8–10 seconds between runs to allow memory to release:

```python
import subprocess, json, time, os

queries = ["query one", "query two", "query three"]
token = os.environ.get("APIFY_TOKEN", "")
all_posts = []

for query in queries:
    print(f"Running: '{query}'...")
    payload = json.dumps({
        "searchQueries": [query],
        "maxPosts": 20,
        "sortBy": "engagement",
        "datePosted": "past-month",
        "minEngagement": 20
    })
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.apify.com/v2/acts/ZmISIboeU1FoHZPxh/run-sync-get-dataset-items?token={token}&format=json&memory=1024",
        "-H", "Content-Type: application/json",
        "-d", payload,
        "--max-time", "150"
    ], capture_output=True, text=True)

    if not result.stdout.strip():
        print("  Empty (timeout) — skipping")
        time.sleep(15)
        continue

    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "error" in data:
            print(f"  ERROR: {data['error']['type']}")
            time.sleep(20)
            continue
        for p in data:
            p["_query"] = query
        all_posts.extend(data)
        print(f"  {len(data)} posts | top eng: {max((p.get('totalEngagement',0) for p in data), default=0)}")
    except Exception as e:
        print(f"  Parse error: {e}")

    time.sleep(10)

# Deduplicate and sort
seen, unique = set(), []
for p in all_posts:
    if p.get("postUrl") not in seen:
        seen.add(p["postUrl"])
        unique.append(p)
unique.sort(key=lambda x: x.get("totalEngagement", 0), reverse=True)

with open("/tmp/linkedin-results.json", "w") as f:
    json.dump(unique, f)
print(f"Total unique posts: {len(unique)}")
```

---

## Actor 2 — Top Content Feed: `linkedin-top-content-scraper`

**Actor ID:** `ShVdhSjicSADHMJ4e`
**Use for:** Pulling from LinkedIn's own editorially-curated high-performing posts by topic. No keyword guessing needed — LinkedIn has already surfaced the top content.
**Cost:** $1.60 / 1,000 posts

### API Call

```bash
curl -s -X POST \
  "https://api.apify.com/v2/acts/ShVdhSjicSADHMJ4e/run-sync-get-dataset-items?token=$APIFY_TOKEN&format=json" \
  -H "Content-Type: application/json" \
  -d '{
    "startUrls": [
      {"url": "https://www.linkedin.com/top-content/finance/"},
      {"url": "https://www.linkedin.com/top-content/artificial-intelligence/"},
      {"url": "https://www.linkedin.com/top-content/leadership/"},
      {"url": "https://www.linkedin.com/top-content/business-strategy/"}
    ],
    "maxItems": 50
  }' \
  --max-time 180 \
  -o /tmp/linkedin-top-content.json
```

### Available Topic URLs

| Topic | URL |
|---|---|
| Finance | `https://www.linkedin.com/top-content/finance/` |
| Artificial Intelligence | `https://www.linkedin.com/top-content/artificial-intelligence/` |
| Leadership | `https://www.linkedin.com/top-content/leadership/` |
| Business Strategy | `https://www.linkedin.com/top-content/business-strategy/` |
| Technology | `https://www.linkedin.com/top-content/technology/` |
| Innovation | `https://www.linkedin.com/top-content/innovation/` |
| Consulting | `https://www.linkedin.com/top-content/consulting/` |
| Recruitment & HR | `https://www.linkedin.com/top-content/recruitment-hr/` |

### Output Fields (per post)

```
postUrl          — direct link to the post
author           — poster's name
authorTitle      — their headline
followers        — follower count string (e.g. "44,930 followers")
content          — full post text
reactions        — reaction count (integer)
comments         — comment count string (e.g. "381 Comments")
sourceUrl        — which top-content topic page it came from
title            — topic category name
```

---

## Pre-Built Query Sets

### Set A — CFO General
*Purpose: Understand what CFOs and finance leaders are posting and engaging with. Baseline niche research.*

```
"CFO"
"Chief Financial Officer"
"CFO leadership"
"CFO finance strategy"
"fractional CFO"
```

**What to expect:** ~60% job postings (noise), ~40% thought leadership. Filter for authors whose headline contains "CFO", "Finance", "FP&A", or "Controller" to isolate signal.

---

### Set B — CFO × AI Intersection
*Purpose: Find content at the exact intersection of CFOs and AI — the highest-value zone for positioning AI tools to finance leaders.*

```
"CFO AI"
"CFO AI agents"
"CFO artificial intelligence"
"CFO automation"
"finance AI agents"
"AI finance transformation"
```

**What to expect:** Lower volume than Set A but much higher signal. Posts here reveal:
- What fear/opportunity angles land with this audience (replacement vs augmentation)
- Which specific AI use cases CFOs care about (forecasting, close, reporting)
- Named proof points (e.g. OpenAI × PwC, Anthropic's own CFO using Claude)

**Known high-performer to reference:** OpenAI × PwC "Office of the CFO" announcement hit 6,478 engagement — the largest post in this entire niche in recent months. Any content that hooks into this story will have tailwind.

---

### Set C — Claude × Finance (Niche Proof Points)
*Purpose: Find posts where Claude or Anthropic is mentioned in a finance or business context — direct proof points for positioning.*

```
"Claude finance"
"Claude CFO"
"Anthropic finance"
"Claude accounting"
"Claude business strategy"
```

**What to expect:** Very low volume. But the posts that exist are gold — they show real practitioners sharing results, which is exactly the social proof that moves a CFO audience.

**Known high-performer:** "Anthropic's CFO closes Anthropic's own books with Claude" (321 eng, 224 comments from a small account) — this story is underexplored and has room to run.

---

### Set D — Finance AI Tools Landscape
*Purpose: Understand who is talking about AI tools for finance broadly — useful for competitive positioning and identifying key voices.*

```
"AI for finance teams"
"FP&A AI"
"finance automation AI"
"AI financial reporting"
```

---

## Output Format

After collecting results, present them as follows:

### Per post:
```
#N | {totalEngagement} eng (👍{reactions} 💬{comments} 🔁{reposts}) | [{query}]
   {authorName} — {authorHeadline truncated to 80 chars}
   "{first 150 chars of postContent}..."
   🔗 {postUrl}
```

### Summary after listing all posts:
- Total posts collected, unique posts after deduplication
- Top 3 posts by engagement with key observation on why each worked
- Pattern analysis: what formats, angles, and topics are driving the most engagement
- Notable authors to follow in this niche
- Any direct proof points relevant to Claude/Anthropic

---

## Error Handling

### Memory limit exceeded
```
{"error": {"type": "actor-memory-limit-exceeded", ...}}
```
**Fix:** Check for and abort stuck runs, then retry:

```bash
# List active runs
curl -s "https://api.apify.com/v2/actor-runs?token=$APIFY_TOKEN&status=RUNNING&limit=10"

# Abort a stuck run
curl -s -X POST "https://api.apify.com/v2/actor-runs/{RUN_ID}/abort?token=$APIFY_TOKEN"
```

Wait 10 seconds after aborting before retrying.

### Empty response / timeout
The actor occasionally times out on queries with few results. If `result.stdout` is empty, skip and move on. Niche queries like `"CFO Claude AI"` may return nothing — that's expected.

### Wrong field for post content
Actor 1 stores post text in `postContent`. Actor 2 stores it in `content`. Always check both when parsing.

---

## Notes from Prior Runs

- **"CFO" query is dominated by job postings** — recruiters flood this keyword. Filter by author headline or use `minEngagement: 100` to surface real thought leadership.
- **Sweet spot for CFO niche:** `minEngagement: 20–50` with `datePosted: "past-month"`. The audience is small so engagement ceilings are lower (50–700 is normal; 1,000+ means the post touched a broader audience).
- **Actor 2 Finance topic** returns macro finance content (Fed rates, ESG, fintech), not CFO-specific content. Pair with Actor 1 Set A/B for full coverage.
- **Best comment-to-reaction ratio posts** are the most debate-worthy — prioritise these for angle research.
