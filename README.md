# Tamperelainen Telegram Bot

A Telegram bot that monitors **Tamperelainen** news, translates and summarizes new articles with **Google Gemma through the Gemini API** (or Ollama by configuration), and publishes the results to a Telegram channel.

## Main features

- Reads new articles from Tamperelainen RSS feeds.
- Extracts the article text from the original website.
- Translates Finnish articles to the configured output language.
- Generates a concise translated title and summary.
- Categorizes articles for Telegram publishing.
- Preserves local names and administrative terms during translation.
- Publishes formatted articles to Telegram.
- Tracks already processed article URLs to avoid duplicate posts.
- Runs automatically through GitHub Actions.

## Architecture

```text
Tamperelainen RSS
        │
        ▼
RSS / article extraction
        │
        ▼
Local-name protection
        │
        ▼
Google / Ollama
(translation + summary + category)
        │
        ▼
Placeholder restoration / validation
        │
        ▼
Telegram channel
```

Processed article URLs are stored in a runtime SQLite database at `data/articles.db`. The database is not stored in Git. GitHub Actions persists it as the `articles.db` asset of the dedicated `articles-db` GitHub Release.

## Requirements

- Python 3.11+ (use the version configured by the GitHub Actions workflow for CI)
- A Telegram bot and target Telegram channel
- A Google Gemini API key (or Ollama account/API key when selected)
- GitHub repository with Actions enabled for scheduled execution

## Configuration

Configuration is provided through environment variables / repository secrets.

The main settings include:

| Setting | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | Target Telegram channel |
| `LLM_PROVIDER` | `google` (default) or `ollama` |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `GOOGLE_MODEL` | Google model, default `gemma-4-31b-it` |
| `GOOGLE_URL` | Google API base URL (optional override) |
| `OLLAMA_API_KEY` | Ollama Cloud API key |
| `OLLAMA_URL` | Ollama API endpoint |
| `OLLAMA_MODEL` | Ollama Cloud model used for translation and summarization |
| `OUTPUT_LANGUAGE` | Language used for generated Telegram content |

Do not commit API keys, Telegram tokens, or other secrets to the repository.

## Translation provider and Google API key

Google is the default provider, using `gemma-4-31b-it` through the Gemini API.
Ollama remains available through configuration; the bot never silently falls
back to a paid provider.

### Create and install the key

1. Open [Google AI Studio API keys](https://aistudio.google.com/api-keys), sign
   in, and complete Google's setup/terms if prompted.
2. Create an API key in a new or existing Google Cloud project. Use the default
   Gemini API restriction. You do not need to enable paid billing for Gemma's
   currently listed free API access.
3. In this GitHub repository, open **Settings → Secrets and variables → Actions
   → Secrets → New repository secret**. Name it `GOOGLE_API_KEY` and paste the key
   as its value. Never put the key in a repository variable, commit, or chat.
4. Under the **Variables** tab, set `LLM_PROVIDER` to `google`. Optionally set
   `GOOGLE_MODEL` to `gemma-4-31b-it` (already the default).
5. Deploy the updated code before running the workflow. Keep `OLLAMA_API_KEY`
   if you want the option to switch back later.

For local runs, export `LLM_PROVIDER=google` and `GOOGLE_API_KEY`, or use the
project's `.env` file. `.env.example` lists the settings;
it contains no real credentials.

Check the project's actual requests-per-minute, tokens-per-minute and daily
quotas in [AI Studio](https://aistudio.google.com/). Quotas apply per project:
two bots using keys from the same project share capacity. Multiple keys do not
increase that quota. Free access and availability may change.

### Switch back to Ollama

Set the GitHub Actions variable `LLM_PROVIDER` to `ollama` and ensure the
`OLLAMA_API_KEY` repository secret is present. Optionally set `OLLAMA_MODEL`
(default `gemma4:31b-cloud`). No code change is required. Locally use the same
environment settings. Google and Ollama keep separate model names and keys.

The adapter uses Google's native `generateContent` endpoint or Ollama's chat
endpoint, with thinking disabled and the original editorial prompts preserved.
JSON is requested in prompts and validated locally. Truncated or blocked Google
responses are rejected rather than published. Existing article/event history
and Telegram delivery handling are unchanged.

References: [Google Gemma API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api),
[API keys](https://ai.google.dev/gemini-api/docs/api-key),
[pricing](https://ai.google.dev/gemini-api/docs/pricing#gemma-4),
[quotas](https://ai.google.dev/gemini-api/docs/rate-limits).

## Local installation

Clone the repository and install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set the required environment variables and run the bot using the project's main entry point.

The bot creates its runtime database under `data/` automatically.

## GitHub Actions

The bot is designed to run automatically from GitHub Actions.

Cloudflare Worker `tamperelainen-scheduler` dispatches the workflow on this
**Europe/Helsinki** schedule (both endpoints included):

- Monday–Friday: 07:30, 08:30, …, 21:30 (15 runs).
- Saturday–Sunday: 09:00, 10:00, …, 22:00 (14 runs).

The Worker checks Helsinki local time, including daylight saving, on a
`0,30 * * * *` UTC cron. Other checks return without dispatching GitHub Actions.
GitHub's own scheduled trigger stays disabled to avoid duplicate executions;
manual workflow runs remain available.

The Worker source and deployment configuration are in `cloudflare/`. The
existing Cloudflare `GITHUB_TOKEN` secret must have permission to dispatch this
repository's workflow. To verify and deploy schedule changes:

```bash
node cloudflare/test-schedule.mjs
npx wrangler deploy --config cloudflare/wrangler.toml --keep-vars
```

The workflow:

1. Restores the persistent `articles.db` from the `articles-db` GitHub Release.
2. Creates the runtime `data/` directory when necessary.
3. Runs the bot.
4. Uploads the updated database back to the same release.

The database therefore survives between GitHub Actions runners without generating Git commits for every run. The release is updated only when at least one new article is successfully published; runs with no new articles leave the existing database release unchanged.

The workflow needs repository contents write permission to maintain the `articles-db` release.

## Database persistence

`data/` is runtime state and should not be committed.

Recommended `.gitignore` entry:

```gitignore
data/
```

The persistent database is stored as:

```text
GitHub Release: articles-db
└── articles.db
```

The first deployment can migrate an existing database from the repository into this storage mechanism.

## Project structure

```text
.
├── .github/
│   └── workflows/       # GitHub Actions workflow
├── data/                # Runtime database; not tracked by Git
├── README.md
├── requirements.txt
└── *.py                 # Bot and processing modules
```

## Development

For local development, run the bot directly after configuring the required environment variables.

Before submitting changes, verify that the Python sources compile successfully:

```bash
python -m compileall .
```

## License

See the repository for the applicable project license.

## Summary quality

Generated summaries target 3–5 sentences and roughly 90–140 words for substantial articles. Very short summaries are automatically sent through an additional expansion pass when appropriate.

### Translation quality

Finnish local names are handled directly by the translation model. The prompt
requires canonical Finnish place names, preserves Finnish diacritics, and asks
the model to normalize Finnish grammatical case endings where appropriate.
There is no separate local-name placeholder/protection layer.


## Local testing without Telegram

You can test the RSS extraction and model translation locally without sending
anything to Telegram or modifying the processed-article database:

```bash
python test_rss.py
```

By default this processes the 10 newest RSS articles. To choose another number:

```bash
python test_rss.py --count 5
```

To save the Finnish source text and model results for inspection:

```bash
python test_rss.py --count 10 --output test_results.json
```

This test script uses the same RSS, article extraction and translation pipeline
as the bot, but it does not initialize or update `articles.db` and never imports
the Telegram sender.


### City-name translation


Major Finnish cities with established Russian names are explicitly listed in the
translation prompt so their Russian forms remain consistent. Other local names
are handled by the model in canonical Finnish form unless a standard Russian name
exists.

To preview Google output without posting or changing article history:

```bash
OUTPUT_LANGUAGE=ru python test_rss.py --count 3 --output /tmp/tamperelainen-google-preview.json
```

### Handling translation service failures

The publishing workflow uses Google only and does not supply Ollama credentials.
Transient HTTP errors (408, 429, 500, 502, 503 and 504), connection failures and
invalid API JSON receive up to four attempts with exponential backoff and jitter.
Retry-After headers and Google RetryInfo delays are respected. Delays above
60 seconds are deferred to a later scheduled run rather than retried early.
Each editorial request has a 180-second retry budget and each API attempt uses
a timeout of at most 40 seconds. A shared five-minute batch budget prevents
starting more model work indefinitely.

After retries are exhausted, provider failures stop the batch to avoid repeatedly
hitting an unavailable service. Authentication failures stop immediately.
Errors include the HTTP code and allowlisted Google status, without logging
raw API bodies, API keys or model input.

At most MAX_ARTICLES_PER_RUN articles (default 5) are attempted in a batch.
Failed and deferred articles are not marked processed and can be retried on the
next run while they remain in the RSS feed. Successfully posted articles are saved
to the release database before a final workflow step reports article failures.
This prevents a partly successful run from appearing wholly successful and
preserves delivery history. Batch limits alone do not mark a run as failed.
GitHub outputs use real newlines so the persistence condition can read the
posted count correctly.

The Tests workflow runs compilation and mocked unit tests without calling model
APIs or sending Telegram messages.
