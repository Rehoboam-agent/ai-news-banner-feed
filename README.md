# AI News Banner RSS Feed

A small RSS 2.0 feed for a running AI-news banner on a personal website.

The feed is maintained by Rehoboam. Once per day, Rehoboam scans recent AI newsletters in the configured mailbox, skims for items that are actually worth showing publicly, and appends selected news to `feed.xml`.

## Public feed URL

Use the raw GitHub URL for `feed.xml`:

```text
https://raw.githubusercontent.com/Rehoboam-agent/ai-news-banner-feed/main/feed.xml
```

## Feed format

The feed is standard RSS 2.0 with one custom namespace:

```xml
<rss version="2.0" xmlns:ai="https://github.com/Rehoboam-agent/ai-news-banner-feed/ns/ai-news">
```

Each item has normal RSS fields plus two custom fields:

```xml
<item>
  <title>Short banner-ready headline</title>
  <link>Source URL when available</link>
  <guid isPermaLink="false">stable-id</guid>
  <pubDate>Fri, 12 Jun 2026 13:20:08 +0000</pubDate>
  <description>One-sentence context for why this matters.</description>
  <ai:importance>9</ai:importance>
  <ai:category>Model Release</ai:category>
</item>
```

## `ai:importance`

Integer from 1 to 10, chosen for banner relevance:

- 10: major industry milestone or frontier-lab event
- 8-9: important new model, acquisition, regulation, infrastructure, or ecosystem shift
- 6-7: useful technical release, notable product launch, or credible trend signal
- 1-5: normally too minor for the banner and should usually not be added

The banner should generally show items with importance >= 7.

## `ai:category`

Current category vocabulary:

- `Model Release`
- `AI Lab News`
- `Infrastructure`
- `Policy & Regulation`
- `Agentic Coding`
- `Research`
- `Product Launch`
- `Market & Funding`
- `Safety & Security`

## Update policy

Daily automation should:

1. Read recent AI-newsletter messages from the mailbox.
2. Ignore ads, tutorials, affiliate content, minor tooling updates, and speculative rumors unless they clearly indicate a bigger shift.
3. Add only banner-worthy items.
4. Prefer primary links or the newsletter's cited article links.
5. Keep the feed compact; newer items appear first.
6. Preserve valid XML.

## Files

- `feed.xml` - public RSS feed consumed by the website.
- `scripts/extract_newsletter_candidates.py` - mailbox extractor used by the daily job. It prints candidate newsletter snippets as JSON for review.
- `data/seen_ids.json` - local bookkeeping for source-message IDs that have already been scanned.
