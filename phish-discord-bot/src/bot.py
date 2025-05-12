import os
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import openai
import aiohttp
from datetime import datetime

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def fetch_latest_setlist(band='phish', last_song_only=False):
    """Fetch the most recent setlist from phish.net
    
    Args:
        band (str): The band to fetch setlist for ('phish', 'trey', 'mike', etc.)
        last_song_only (bool): Whether to return only the last song
    """
    try:
        base_url = 'https://phish.net/setlists/'
        url = f'{base_url}{band}/' if band else base_url
        print(f"Fetching setlist from: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find the most recent setlist
                    setlist_div = soup.find('div', class_='setlist')
                    if not setlist_div:
                        return f"No recent setlist found for {band}."
                    
                    # Extract date and venue
                    date_span = setlist_div.find('span', class_='setlist-date')
                    venue_span = setlist_div.find('span', class_='setlist-venue')
                    
                    if not date_span or not venue_span:
                        return f"Could not parse setlist information for {band}."
                    
                    date = date_span.text.strip()
                    venue = venue_span.text.strip()
                
                # Extract setlist content
                sets = setlist_div.find_all('p', class_='setlist-set')
                if not sets:
                    sets = setlist_div.find_all('p', class_='set')  # try alternate class
                
                setlist_text = []
                all_songs = []
                
                if not sets:
                    # Try to find any song information
                    songs_div = setlist_div.get_text(strip=True)
                    if songs_div:
                        setlist_text.append(songs_div)
                        all_songs = [songs_div]
                else:
                    for set_num, set_content in enumerate(sets, 1):
                        songs = set_content.get_text(strip=True)
                        if songs:
                            setlist_text.append(f"Set {set_num}: {songs}")
                            # Split songs and clean up the text
                            set_songs = [s.strip() for s in songs.split(',') if s.strip()]
                            all_songs.extend(set_songs)
                
                if not setlist_text:
                    return f"Found setlist for {date} at {venue}, but couldn't parse the songs."
                
                if last_song_only and all_songs:
                    return f"The last song played was **{all_songs[-1]}** on {date} at {venue}"
                
                # Format the full response
                return f"**{date} - {venue}**\n\n" + "\n".join(setlist_text)
                
        return f"Error accessing {url}"
    
    except Exception as e:
        print(f"Error fetching setlist: {str(e)}")
        return f"Error fetching setlist information for {band}. Please try again later."

async def ask_chatgpt(question):
    """Ask ChatGPT a question"""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant focused on Phish-related information."},
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='setlist')
async def setlist(ctx, band: str = 'phish'):
    """Get the most recent setlist for a specified band
    
    Usage:
        !setlist - Get latest Phish setlist
        !setlist trey - Get latest Trey setlist
        !setlist mike - Get latest Mike setlist
        !setlist tab - Get latest TAB setlist
    """
    await ctx.send(f"Fetching latest {band.title()} setlist...")
    setlist_info = await fetch_latest_setlist(band=band.lower())
    await ctx.send(setlist_info)

@bot.command(name='ask')
async def ask(ctx, *, question):
    """Ask ChatGPT a Phish-related question"""
    await ctx.send("Thinking...")
    response = await ask_chatgpt(question)
    await ctx.send(response)

@bot.event
async def on_message(message):
    """Handle messages that mention the bot"""
    print(f"Received message: {message.content}")
    
    # Ignore messages from the bot itself
    if message.author == bot.user:
        print("Message was from bot, ignoring")
        return

    # Process commands normally
    await bot.process_commands(message)

    # Check if the bot was mentioned
    if bot.user in message.mentions:
        print(f"Bot was mentioned! Content: {message.content}")
        content = message.content.lower()
        
        # Remove the mention from the content
        content = content.replace(f'<@{bot.user.id}>', '').strip()
        
        # Check for setlist/show queries
        if any(word in content for word in ['setlist', 'set', 'show']):
            # Try to identify the band
            band = 'phish'  # default to Phish
            if 'trey' in content:
                band = 'trey'
            elif 'mike' in content:
                band = 'mike'
            elif 'tab' in content:
                band = 'tab'
            
            # Check if it's a last song query
            if any(phrase in content for phrase in ['last song', 'latest song', 'most recent song']):
                await message.channel.send(await fetch_latest_setlist(band=band, last_song_only=True))
            else:
                await message.channel.send(await fetch_latest_setlist(band=band))
        elif any(phrase in content for phrase in ['last song', 'latest song', 'most recent song']):
            await message.channel.send(await fetch_latest_setlist(last_song_only=True))
        else:
            # Treat as a general question for ChatGPT
            response = await ask_chatgpt(content)
            await message.channel.send(response)

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
