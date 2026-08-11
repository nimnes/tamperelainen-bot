# Tamperelainen English Telegram Bot

Reads Tamperelainen RSS, fetches each new article, translates it from Finnish
to English, asks Ollama Cloud for a concise Russian summary, and publishes the
summary to Telegram.

RSS:
https://www.tamperelainen.fi/feed/rss/

## What it publishes

Each new article becomes:

🇬🇧 Russian headline

2-4 sentence Russian summary generated from the full article.

📰 Category
🕒 Publication time

🔗 Read original article

The full article is not republished.

## Local setup/test

Python 3.11+ recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set your credentials in `.env`.

Test without sending to Telegram:

```bash
python bot.py --test
```

Send one real batch:

```bash
python bot.py --once
```

## Ollama Cloud

The project uses Ollama's direct API at:

https://ollama.com/api/chat

Create an Ollama API key at:

https://ollama.com/settings/keys

Then set:

```text
OLLAMA_API_KEY=...
```

The default model is:

```text
gpt-oss:20b
```

Ollama currently lists `gpt-oss:20b-cloud` as a low-usage cloud model and
`gpt-oss:120b-cloud` as a medium-usage cloud model. The direct API examples
use `gpt-oss:20b` with the Ollama Cloud API endpoint, so this project uses
`gpt-oss:20b`.

Ollama's Free plan is currently $0 and includes access to cloud models, but
cloud usage is subject to Ollama's current service limits.

## Telegram

Create the bot with BotFather.

Add it as an administrator to your Telegram channel with permission to post.

Set:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Telegram HTML parse mode is enabled, so `<b>...</b>` is rendered as bold.
The automatic Finnish webpage preview is disabled because the message already
contains a dedicated original-article link.

## Free 24/7 hosting: GitHub Actions

This repository contains:

`.github/workflows/publish.yml`

It runs every 10 minutes, then exits. It does not need a permanent server.

Flow:

Tamperelainen RSS
-> article extraction
-> Finnish -> English translation
-> Ollama Cloud summary
-> Telegram
-> save processed URL database

### 1. Create a GitHub repository

Create a repository and upload the project files.

A public repository is the simplest option because standard GitHub-hosted
runners are free for public repositories.

Do NOT put secrets in the repository.

### 2. Add secrets

Open:

Settings -> Secrets and variables -> Actions -> New repository secret

Add:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
OLLAMA_API_KEY
```

### 3. Enable Actions

Open the Actions tab and enable the workflow if GitHub asks.

Use:

Actions -> Tamperelainen news -> Run workflow

for the first manual test.

### 4. Check the log

A successful run should look roughly like:

```text
Found 20 RSS articles.
NEW: ...
Extracted 12345 Finnish chars.
Sent.
New articles processed: 1
```

The workflow commits `data/articles.db` after a successful run so future
runs know which URLs have already been published.

### GitHub scheduling

GitHub supports scheduled workflows as frequently as every 5 minutes. This
project uses every 10 minutes.

Scheduled workflows run from the repository's default branch.

GitHub says standard GitHub-hosted runner use is free for public repositories.
GitHub Free also has a monthly allowance for private repositories.

GitHub may automatically disable scheduled workflows in public repositories
after 60 days without repository activity, so keep the repository active or
switch to another hosting method if that becomes relevant.

## Alternative hosting

### Render

Render currently offers free web services, but free services can spin down
when idle, and free background workers are not the right fit for this bot.
Because this bot is naturally a scheduled job, GitHub Actions is simpler.

### Oracle Cloud Free Tier

A free VM can run a normal 24/7 Python process, but setup is more involved and
free VM capacity can be difficult to obtain.

### Your Mac

Excellent for development/testing, but it must stay running.

## Security

Never commit:

- `.env`
- Telegram bot token
- Ollama API key

If a token is accidentally exposed, revoke/rotate it immediately.

## Copyright

The bot publishes translated headlines and short summaries plus a link to
the original article rather than automatically republishing full articles.
Check Tamperelainen's terms and applicable copyright rules before public
distribution.


## Publishing behavior

The bot is intentionally designed to publish only new articles.

On the **first successful run**, it creates a baseline from the articles
currently present in the RSS feed and does NOT publish those existing articles.
This prevents a fresh deployment from dumping the latest 20 RSS items into
your Telegram channel.

On later runs:

```text
RSS article URL already in database -> skip
RSS article URL not in database   -> translate, summarize, publish, save URL
```

The workflow runs every 30 minutes.

The processed-article database is committed back to the repository after each
successful run, so the history survives between GitHub Actions runners.

If more than `RSS_LIMIT` new articles appear between two runs, increase
`RSS_LIMIT` in the workflow/environment before deploying. The default is 20.


## Article images

The scraper looks for the article's `og:image` first and falls back to
Twitter's image metadata.

If an image is available, Telegram receives it as the post's photo with the
Russian headline and summary as the caption.

If there is no image, the bot sends the normal text-only message.

Telegram photo captions have a 1024-character limit. The generated message is
normally well below this; if it ever exceeds the limit, the bot falls back to
a normal text message so the article is not lost.

## Automatic article categories

The RSS category is no longer shown directly. Ollama Cloud classifies each
article into one controlled English category:

- 🏙️ Local
- 🚗 Traffic
- 🚓 Crime
- 🏛️ Politics
- 💼 Business
- 🏠 Housing
- 🏥 Health
- 🎓 Education
- 🎭 Culture
- ⚽ Sports
- 🌦️ Weather
- 🎉 Events
- 🍴 Food
- ✈️ Travel
- 🌿 Environment
- 💻 Technology
- 📰 News

Classification and summarization are returned as structured JSON. Python
validates the category; an invalid category safely becomes `📰 News`.


## Russian output

The Telegram channel output is Russian:

Finnish article
-> Finnish-to-Russian translation
-> Russian title
-> Russian 2-4 sentence summary
-> Russian category

The displayed categories are:
🏙️ Местные новости, 🚗 Транспорт, 🚓 Происшествия и преступления,
🏛️ Политика, 💼 Бизнес, 🏠 Недвижимость, 🏥 Здоровье, 🎓 Образование,
🎭 Культура, ⚽ Спорт, 🌦️ Погода, 🎉 События, 🍴 Еда, ✈️ Путешествия,
🌿 Экология, 💻 Технологии, 📰 Новости.

Publication timestamps from the RSS feed are formatted as Russian dates,
for example `11 августа 2026, 18:07`.
