# Phish Discord Bot

A Discord bot that uses ChatGPT to provide information about Phish setlists and interact with phish.net data.

## Setup

1. Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   OPENAI_API_KEY=your_openai_api_key
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Features

- Real-time setlist information from phish.net
- ChatGPT-powered interactions
- Command to fetch latest setlists
- Command to search historical setlists
