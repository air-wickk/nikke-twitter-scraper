import os
import asyncio
import json
from discord.ext import commands, tasks
from discord import Intents
from dotenv import load_dotenv
from twitterclient import TwitterClient
from collections import deque

PERSIST_FILE = "sent_tweets.json"

def load_sent_tweet_ids():
    if os.path.exists(PERSIST_FILE):
        try:
            with open(PERSIST_FILE, "r") as sent_file:
                data = json.load(sent_file)
                return deque(data, maxlen=25)
        except Exception:
            # if file is empty or invalid, start fresh
            return deque(maxlen=25)
    return deque(maxlen=25)

def save_sent_tweet_ids(sent_tweet_ids):
    with open(PERSIST_FILE, "w") as sent_file:
        json.dump(list(sent_tweet_ids), sent_file)

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
TRACKED_USER_ID = os.getenv("TRACKED_USER_ID")

intents = Intents.default()
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
twitter = TwitterClient()
last_tweet_url = None
sent_tweet_ids = load_sent_tweet_ids()  # deque with maximum length of 25

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_tweets.start()

@tasks.loop(minutes=0.1)
async def check_tweets():
    global last_tweet_url, sent_tweet_ids
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        tweet_url = await twitter.get_latest_tweet_url(TRACKED_USER_ID)
        if tweet_url:
            tweet_id = tweet_url.split('/')[-1]
            if tweet_id not in sent_tweet_ids:
                await channel.send(tweet_url)
                sent_tweet_ids.append(tweet_id)
                save_sent_tweet_ids(sent_tweet_ids)
    except Exception as e:
        print(f"Error fetching tweets: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)