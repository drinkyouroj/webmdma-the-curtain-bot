# Phish Discord Bot

A Discord bot that provides real-time Phish setlist information and ChatGPT-powered interactions.

## Features
- Fetch recent setlists from phish.net
- ChatGPT integration for natural language interactions
- Real-time setlist information

## Setup
1. Create a `.env` file with your credentials:
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
   python src/bot.py
   ```

## Commands
- `!setlist` - Get the most recent Phish setlist
- `!ask [question]` - Ask ChatGPT a question about Phish
