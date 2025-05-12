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

async def fetch_latest_setlist(band='phish', last_song_only=False, return_raw=False):
    """Fetch the most recent setlist from phish.net
    
    Args:
        band (str): The band to fetch setlist for ('phish', 'trey', 'mike', etc.)
        last_song_only (bool): Whether to return only the last song
        return_raw (bool): If True, return raw data dict instead of formatted string
    Returns:
        str: Formatted setlist text if return_raw is False
        dict: Raw setlist data if return_raw is True
    """
    try:
        base_url = 'https://phish.net/setlists/'
        url = f'{base_url}{band}/' if band else base_url
        print(f"Fetching setlist from: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    print("Got HTML response, looking for setlist...")
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find the most recent setlist
                    setlist_div = soup.find('div', class_='setlist')
                    if not setlist_div:
                        # Try to find any div that might contain setlist info
                        print("No div with class 'setlist' found. Looking for alternatives...")
                        # Print all div classes we find
                        all_divs = soup.find_all('div')
                        print("Found these div classes:")
                        for div in all_divs:
                            if div.get('class'):
                                print(f"- {' '.join(div.get('class'))}")
                        return f"No recent setlist found for {band}."
                    
                    # Extract date and venue
                    print("Looking for date and venue...")
                    date_span = setlist_div.find('span', class_='setlist-date')
                    
                    if not date_span:
                        print("Couldn't find date span")
                        return f"Could not parse setlist information for {band}."
                    
                    # Parse the date text which is in format "PHISH, DAY MM/DD/YYYY"
                    date_text = date_span.text.strip()
                    # Extract raw date
                    date_raw = date_text.split(',')[1].strip() if ',' in date_text else date_text
                    # Format date (capitalize day and format month name)
                    parts = date_raw.split(' ', 1)
                    if len(parts) == 2:
                        day = parts[0].capitalize()
                        try:
                            dt = datetime.strptime(parts[1], "%m/%d/%Y")
                            date = f"{day}, {dt.strftime('%B %d, %Y')}"
                        except ValueError:
                            date = f"{day} {parts[1]}"
                    else:
                        date = date_raw
                    
                    # Try to find venue information
                    venue_heading = setlist_div.find('h4')
                    venue = ""
                    if venue_heading:
                        venue_text = venue_heading.text.strip()
                        if '@' in venue_text:
                            venue = venue_text.split('@')[1].strip()
                
                # Extract setlist content: process each <p> with a set-label only once
                print("Looking for setlist content...")
                import re
                setlist_dict = {}  # label_text -> songs_text
                all_songs = []
                set_paragraphs = setlist_div.find_all('p')
                for p in set_paragraphs:
                    # Find all set-label spans in this paragraph
                    labels = p.find_all('span', class_='set-label')
                    if not labels:
                        continue
                    # Get the full text of the paragraph, with labels as markers
                    full_text = p.decode_contents()
                    # Find all set-labels and their positions
                    label_matches = list(re.finditer(r'<span class="set-label">(.*?)</span>', full_text))
                    # For each label, extract the text until the next label or end
                    for i, match in enumerate(label_matches):
                        label_text = match.group(1).strip()
                        # Normalize set label capitalization ("SET 1" -> "Set 1", "ENCORE" -> "Encore")
                        norm_label = label_text.title()
                        if norm_label in setlist_dict:
                            continue  # Only first occurrence of each set label
                        start = match.end()
                        end = label_matches[i+1].start() if i+1 < len(label_matches) else len(full_text)
                        # Extract the raw songs HTML and strip tags
                        songs_html = full_text[start:end]
                        raw = re.sub('<.*?>', '', songs_html)
                        raw = raw.replace('&gt;', '>').replace('&amp;', '&')
                        # Split songs on commas, arrows (->), or greater-than (>)
                        parts = [s.strip() for s in re.split(r'\s*->\s*|\s*>\s*|,\s*', raw) if s.strip()]
                        # Reconstruct songs text
                        songs_text = ', '.join(parts)
                        if parts:
                            setlist_dict[norm_label] = songs_text
                            all_songs.extend(parts)
                # Order: SET 1, SET 2, ... ENCORE
                setlist_text = [f"{label}: {setlist_dict[label]}" for label in setlist_dict]
                # Remove duplicate songs while preserving order
                all_songs = [x for i, x in enumerate(all_songs) if x not in all_songs[:i]]
                
                if not setlist_text:
                    return f"Found setlist for {date} at {venue}, but couldn't parse the songs."
                
                if last_song_only and all_songs:
                    return f"The last song played was **{all_songs[-1]}** on {date} at {venue}"
                
                # Format the full response
                header = f"**{date}**" if not venue else f"**{date} - {venue}**"
                formatted_text = f"{header}\n\n" + "\n".join(setlist_text)
                
                if return_raw:
                    return {
                        'date': date,
                        'venue': venue,
                        'setlist_dict': setlist_dict,
                        'all_songs': all_songs,
                        'formatted_text': formatted_text
                    }
                return formatted_text
                
        return f"Error accessing {url}" if not return_raw else None
    
    except Exception as e:
        print(f"Error fetching setlist: {str(e)}")
        error_msg = f"Error fetching setlist information for {band}. Please try again later."
        return error_msg if not return_raw else None

async def ask_chatgpt(question):
    """Ask ChatGPT a question"""
    try:
        client = openai.AsyncOpenAI()
        response = await client.chat.completions.create(
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
        
        # Try to identify the band
        band = 'phish'  # default to Phish
        if 'trey' in content:
            band = 'trey'
        elif 'mike' in content:
            band = 'mike'
        elif 'tab' in content:
            band = 'tab'
        
        # Get the setlist data
        setlist_data = await fetch_latest_setlist(band=band, return_raw=True)
        if not setlist_data:
            await message.channel.send(f"Sorry, I couldn't fetch the setlist for {band}.")
            return

        # Handle set & encore queries
        import re
        requested_key = None
        # Encore query
        if 'encore' in content:
            requested_key = 'Encore'
        else:
            # Set number query, e.g., 'set 2'
            m = re.search(r'set\s*(\d+)', content)
            if m:
                requested_key = f"Set {m.group(1)}"
        if requested_key and requested_key in setlist_data['setlist_dict']:
            response = f"**{setlist_data['date']}{' - ' + setlist_data['venue'] if setlist_data['venue'] else ''}**\n\n"
            response += f"{requested_key}: {setlist_data['setlist_dict'][requested_key]}"
            await message.channel.send(response)
            return

        # Check for song queries only if user asked about playing songs
        if re.search(r"\bdid they play\b", content):
            # existing song query logic...
            import difflib, string
            # Extract quoted songs, or split by 'or', 'and', comma
            quoted_songs = re.findall(r'"([^"]+)"|\'([^\']+)\'', content)
            if quoted_songs:
                song_queries = [q[0] or q[1] for q in quoted_songs]
            else:
                # Remove 'did they play', 'was', etc., then split
                song_section = re.sub(r'(?:did they |was |were |did |play |played |in set.*|at that show.*|\?)', '', content)
                song_queries = re.split(r'\s*(?:or|and|,|/|\&|\|)\s*', song_section)
                song_queries = [s for s in song_queries if s.strip()]
            # Normalize: remove punctuation, lowercase, strip
            def normalize(s):
                return ''.join(c for c in s.lower() if c not in string.punctuation).strip()
            # Expanded Phish abbreviation map
            abbr = {
                'yem': 'you enjoy myself',
                '2001': 'also sprach zarathustra',
                'moma': 'the moma dance',
                'hood': 'harry hood',
                'ctb': 'cars trucks buses',
                'dwd': 'down with disease',
                'tweeprise': 'tweezer reprise',
                'tweezer reprise': 'tweezer reprise',
                'reba': 'reba',
                'slave': 'slave to the traffic light',
                'ghost': 'ghost',
                'divided sky': 'the divided sky',
                'bag': 'ac/dc bag',
                'stash': 'stash',
                'gin': 'bathtub gin',
                'halleys': 'halley’s comet',
                'halley': 'halley’s comet',
                'mikes': "mike's song",
                'groove': 'weekapaug groove',
                'maze': 'maze',
                'cities': 'cities',
                'wolfmans': "wolfman's brother",
                'wolfman': "wolfman's brother",
                'fee': 'fee',
                'tweezer': 'tweezer',
                'piper': 'piper',
                'antelope': 'run like an antelope',
                'llama': 'llama',
                'lizards': 'the lizards',
            }
            # Build all normalized song names for fuzzy matching
            all_song_names = []
            song_lookup = []  # tuple: (set_label, song, position)
            for set_label, songs in setlist_data['setlist_dict'].items():
                for idx, song in enumerate([s.strip() for s in songs.split(',') if s.strip()]):
                    norm_song = normalize(song)
                    all_song_names.append(norm_song)
                    song_lookup.append((set_label, song, idx+1))
            responses = []
            for query in song_queries:
                norm_query = normalize(query)
                expanded_query = abbr.get(norm_query, norm_query)
                found = []
                for set_label, song, pos in song_lookup:
                    # Match: exact, abbreviation, substring, or fuzzy
                    if (
                        expanded_query == normalize(song)
                        or expanded_query in normalize(song)
                        or normalize(song) in expanded_query
                        or difflib.SequenceMatcher(None, expanded_query, normalize(song)).ratio() > 0.8
                    ):
                        found.append((set_label, song, pos))
                if found:
                    # Group by set
                    sets = {}
                    for set_label, song, pos in found:
                        sets.setdefault(set_label, []).append(pos)
                    details = []
                    for set_label, positions in sets.items():
                        pos_str = ', '.join(str(p) for p in positions)
                        if len(positions) == 1:
                            details.append(f"{set_label} (song #{positions[0]})")
                        else:
                            details.append(f"{set_label} (songs #{pos_str})")
                    responses.append(f"Yes, '{found[0][1]}' was played in {', '.join(details)} on {setlist_data['date']}{' at ' + setlist_data['venue'] if setlist_data['venue'] else ''}.")
                else:
                    # Suggest closest match
                    close = difflib.get_close_matches(expanded_query, all_song_names, n=1, cutoff=0.6)
                    if close:
                        suggestion = close[0].title()
                        responses.append(f"No, but did you mean '{suggestion}'?")
                    else:
                        responses.append(f"No, '{query.title()}' wasn't played in the latest show.")
            for resp in responses:
                await message.channel.send(resp)
            return

        # If message contains a question mark and no set or song query, fallback to ChatGPT
        if '?' in content:
            response = await ask_chatgpt(content)
            await message.channel.send(response)
            return

        # Default to showing full setlist
        await message.channel.send(setlist_data['formatted_text'])

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
