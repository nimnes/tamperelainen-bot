# Tamperelainen News Telegram Bot

A small Python bot that monitors the Tamperelainen RSS feed, fetches new
articles, translates them, creates a short AI-generated summary, classifies
the article, and publishes the result to Telegram.

RSS source:

https://www.tamperelainen.fi/feed/rss/

## Output language

The bot is **English by default**.

Set the `OUTPUT_LANGUAGE` environment variable to change the output language:

```text
OUTPUT_LANGUAGE=en
```

or:

```text
OUTPUT_LANGUAGE=ru
```

Only `en` and `ru` are currently supported.

This repository's GitHub Actions workflow explicitly sets:

```yaml
OUTPUT_LANGUAGE: ru
```

Therefore **this repository publishes Russian**, while someone cloning the
repository and running the bot without setting `OUTPUT_LANGUAGE` gets English
output by default.

For local use, put the setting in `.env`:

```text
OUTPUT_LANGUAGE=ru
```

or:

```text
OUTPUT_LANGUAGE=en
```

## Processing flow

```text
Tamperelainen RSS
       ↓
Find new article
       ↓
Fetch full article
       ↓
Finnish → configured output language
       ↓
Ollama Cloud
       ├── category
       └── 2-4 sentence summary
       ↓
Telegram
       ↓
Save article URL
```

## Features

- Checks Tamperelainen every 30 minutes on GitHub Actions.
- Publishes only articles that have not been processed before.
- First deployment creates an RSS baseline and does not publish existing
  articles.
- Translates Finnish to the configured output language.
- Generates a concise AI summary with Ollama Cloud.
- Automatically classifies articles.
- Includes the article's main image when available.
- Uses Telegram HTML so the title is displayed in bold.
- Includes a link to the original article.
- Stores processed URLs in `data/articles.db`.
- GitHub Actions commits the database so duplicate tracking survives between
  runners.
- An article is marked as processed only after Telegram delivery succeeds.
- The database save step exits cleanly when there are no database changes.
- GitHub Actions uses Node-24-compatible `actions/checkout@v5` and
  `actions/setup-python@v6`.

## Categories

The classifier uses a controlled set of categories:

- 🏙️ Local / Местные новости
- 🚗 Traffic / Транспорт
- 🚓 Crime / Происшествия и преступления
- 🏛️ Politics / Политика
- 💼 Business / Бизнес
- 🏠 Housing / Недвижимость
- 🏥 Health / Здоровье
- 🎓 Education / Образование
- 🎭 Culture / Культура
- ⚽ Sports / Спорт
- 🌦️ Weather / Погода
- 🎉 Events / События
- 🍴 Food / Еда
- ✈️ Travel / Путешествия
- 🌿 Environment / Экология
- 💻 Technology / Технологии
- 📰 News / Новости

The category is returned by Ollama as a controlled identifier such as
`TRAFFIC`, then Python maps it to the configured language's display label.
Invalid categories fall back to `News`.

## Local setup

Python 3.11+ is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
OLLAMA_API_KEY=...
```

The default is English:

```text
OUTPUT_LANGUAGE=en
```

To use Russian:

```text
OUTPUT_LANGUAGE=ru
```

Test without sending to Telegram:

```bash
python bot.py --test
```

Run one real batch:

```bash
python bot.py --once
```

## Ollama Cloud

The bot uses Ollama's direct API.

Create an API key:

https://ollama.com/settings/keys

Set:

```text
OLLAMA_API_KEY=...
```

The default model is:

```text
gpt-oss:20b
```

## Telegram

Create a bot with BotFather and give it permission to post to your channel.

Set:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## GitHub Actions deployment

The included workflow is:

```text
.github/workflows/publish.yml
```

It runs every 30 minutes.

Add these repository secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
OLLAMA_API_KEY
```

The workflow also contains:

```yaml
OUTPUT_LANGUAGE: ru
```

Change that line to:

```yaml
OUTPUT_LANGUAGE: en
```

if you want this repository's published Telegram output to be English.

This is intentionally separate from the application's default. The source
code defaults to English so another user can clone the repository and use it
without unexpectedly getting Russian output.

## Publishing behavior

On the first successful run, the bot saves all currently visible RSS article
URLs as a baseline and sends nothing.

On subsequent runs:

```text
URL already in database → skip
URL not in database     → translate → summarize → publish → save URL
```

The URL is saved only after Telegram successfully accepts the message. If
publishing fails, the article remains unprocessed and can be retried on the
next run.

The RSS limit defaults to 20 articles. Increase `RSS_LIMIT` if necessary.

## Security

Never commit:

- `.env`
- Telegram bot tokens
- Ollama API keys

If a secret is exposed, revoke and replace it immediately.

## Copyright

The bot publishes translated headlines and short summaries with a link to
the original article rather than automatically republishing full articles.
Check Tamperelainen's terms and applicable copyright rules before public
distribution.


### Database persistence

`data/articles.db` is intentionally committed to the repository because
GitHub Actions runners are ephemeral. The repository's `.gitignore` ignores
SQLite database files generally, so the workflow uses:

```bash
git add -f data/articles.db
```

to force-add only the bot's persistent article database.


### RSS reliability

The RSS request uses browser-like headers and retries once after a failed
request. If the feed still cannot be fetched, the bot logs a warning and
returns no articles instead of failing the GitHub Actions job. The next
scheduled run will try again.

### Translation pipeline

The bot sends the original Finnish headline and article text directly to
Ollama Cloud. Ollama produces the translated headline, 2-4 sentence summary,
and category in one request. No separate translation service is required.

### Proper-name protection

Local Finnish place names are protected before the Ollama request. Known
Tampere-area names such as Tullin, Koskipuisto, Hervannan Duo, Hämeenkatu and
Pyynikintie are replaced with immutable placeholders while Ollama generates
the translation. They are restored afterwards in their original Finnish form.
An explicit major-city allowlist permits established translations such as
Tampere -> Тампере and Helsinki -> Хельсинки in Russian. When uncertain, the
bot keeps the Finnish name.

### Mixed-script protection

Russian output is checked for accidental words containing both Latin and
Cyrillic characters, such as `оazис`. If detected, Ollama corrects only the
accidental script mixing while preserving Finnish proper names, brands,
abbreviations and intentionally Latin text.
