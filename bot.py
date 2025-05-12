import os
import discord
from discord.ext import commands
import openai
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class PhishNet:
    BASE_URL = "https://phish.net"
    
    @staticmethod
    async def get_latest_setlist():
        try:
            response = requests.get(f"{PhishNet.BASE_URL}/setlists/latest")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the setlist content
            setlist_div = soup.find('div', class_='setlist-body')
            if not setlist_div:
                return "No setlist found."
            
            # Extract date and venue
            header = soup.find('h1', class_='setlist-header')
            date_venue = header.text.strip() if header else "Date/Venue not found"
            
            # Extract setlist content
            setlist_text = setlist_div.get_text(separator='\n').strip()
            
            return f"**{date_venue}**\n\n{setlist_text}"
        except Exception as e:
            return f"Error fetching setlist: {str(e)}"

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='setlist')
async def setlist(ctx):
    """Get the latest Phish setlist"""
    setlist_info = await PhishNet.get_latest_setlist()
    await ctx.send(setlist_info)

@bot.command(name='ask')
async def ask(ctx, *, question):
    """Ask ChatGPT about Phish"""
    try:
        # Create a chat completion with context about Phish
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant focused on the band Phish. Provide accurate and helpful information about the band, their music, and their performances."},
                {"role": "user", "content": question}
            ]
        )
        
        # Send the response
        await ctx.send(response.choices[0].message.content)
    except Exception as e:
        await ctx.send(f"Sorry, I encountered an error: {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try !help to see available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
