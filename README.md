# Tamperelainen Telegram Bot

A Telegram bot that monitors **Tamperelainen** news, translates and summarizes new articles with **Ollama Cloud**, and publishes the results to a Telegram channel.

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
Ollama Cloud
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
- An Ollama Cloud account/API access
- An Ollama Cloud model available to your account
- GitHub repository with Actions enabled for scheduled execution

## Configuration

Configuration is provided through environment variables / repository secrets.

The main settings include:

| Setting | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | Target Telegram channel |
| `OLLAMA_API_KEY` | Ollama Cloud API key |
| `OLLAMA_URL` | Ollama API endpoint |
| `OLLAMA_MODEL` | Ollama Cloud model used for translation and summarization |
| `OUTPUT_LANGUAGE` | Language used for generated Telegram content |

Do not commit API keys, Telegram tokens, or other secrets to the repository.

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
