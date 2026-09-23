# MeetRecap

MeetRecap uses AI-style text analysis to distill raw meeting notes into
concise, accurate summaries — freeing professionals from tedious note-taking
and surfacing action items and decisions for faster, data-driven follow-up.

## Features

- **Free tier** — `POST /summarize/basic`
  A short extractive summary (top N sentences) of your meeting notes.
  No license key required — try it instantly.

- **Pro tier** — `POST /summarize/full` (requires a paid license key)
  Full meeting recap including:
  - Extractive summary
  - Key points
  - Action items (with owner detection via `@name` or `Name:` prefixes)
  - Decisions made
  - Top keywords

## Running locally

