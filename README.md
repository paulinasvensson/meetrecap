# meetrecap

Turn messy meeting notes into clean summaries and action items.

## What it does

Paste raw, unstructured meeting notes into the page and get:

- **Free**: a 3-line summary + up to 3 detected action items (text only).
- **Pro** (requires a license key): a full multi-sentence summary, an
  unlimited list of action items, plus automatic **owner** and **deadline**
  extraction and **priority** tagging (e.g. "urgent", "asap").

The extraction/summarization is done with real, dependency-free NLP
heuristics (word-frequency sentence scoring for the summary, regex/pattern
matching for action items, owners like `@name` or "Name will...", deadlines
like "by Friday" / "EOD", and urgency keywords).

## Run locally

