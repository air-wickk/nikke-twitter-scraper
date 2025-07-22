import os
import asyncio
import json
import random
from discord.ext import commands, tasks
from discord import Intents, Activity, ActivityType
from dotenv import load_dotenv
from twitterclient import TwitterClient
from collections import deque
from threading import Thread
from flask import Flask
import logging
import time
import discord

PERSIST_FILE = "sent_tweets.json"
MESSAGE_MAP_FILE = "tweet_message_map.json"

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

def load_tweet_message_map():
    if os.path.exists(MESSAGE_MAP_FILE):
        try:
            with open(MESSAGE_MAP_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_tweet_message_map(tweet_message_map):
    with open(MESSAGE_MAP_FILE, "w") as f:
        json.dump(tweet_message_map, f)

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
TRACKED_USER_ID = os.getenv("TRACKED_USER_ID")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
twitter = TwitterClient()
last_tweet_url = None
sent_tweet_ids = load_sent_tweet_ids()  # deque with maximum length of 25
tweet_message_map = load_tweet_message_map()  # {tweet_id: discord_message_id}

shifty_statuses = [
    "analysis of the Commander's data",
    "scans for raptures",
    "over classified files",
    "Central Government feeds",
    "tutorials on squad tactics",
    "diagnostics run",
    "the Outpost's security feeds",
    "the Ark's mainframe logs",
    "suspicious activity in the Ark",
    "squad formation tutorials",
    "encrypted transmissions",
    "mission briefings",
    "for rapture threats",
    "for anomalies in the system",
    "for Pilgrim transmissions.",
    "the Outpost's coffee machine",
    "the Ark's communication channels",
    "videos on Blabla",
    "Tetra's Got Talent",
]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

@tasks.loop(minutes=5)
async def change_status():
    status = random.choice(shifty_statuses)
    await bot.change_presence(activity=Activity(type=ActivityType.watching, name=status))

async def random_human_sleep():
    # Wait between 10 and 30 minutes between "human" actions
    await asyncio.sleep(random.randint(600, 1800))

@tasks.loop(seconds=10)
async def human_like_activity():
    await random_human_sleep()
    try:
        action = random.choice(["trends", "search", "like"])
        if action == "trends":
            # Get trending topics
            trends = await twitter.client.get_trends('trending')
            logging.info(f"Simulated human: fetched trends: {trends}")
        elif action == "search":
            # Search for latest tweets with a query
            tweets = await twitter.client.search_tweet('NIKKE', 'Latest')
            if tweets:
                for tweet in tweets:
                    logging.info(f"Simulated human: found tweet {tweet.id}")
                # Search more tweets (pagination)
                more_tweets = await tweets.next()
                for tweet in more_tweets:
                    logging.info(f"Simulated human: found more tweet {tweet.id}")
            else:
                logging.info("Simulated human: no tweets found for search.")
        elif action == "like":
            # Like a random tweet from search
            tweets = await twitter.client.search_tweet('NIKKE', 'Latest')
            if tweets:
                tweet = random.choice(list(tweets))
                try:
                    await tweet.favorite()
                    logging.info(f"Simulated human: liked tweet {tweet.id}.")
                except Exception as e:
                    logging.warning(f"Failed to like tweet {tweet.id}: {e}")
            else:
                logging.info("Simulated human: no tweets found to like.")
    except Exception as e:
        logging.warning(f"Human-like activity failed: {e}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    # Load cogs (only once)
    if not hasattr(bot, "cogs_loaded"):
        await bot.load_extension("suggestions")
        await bot.load_extension("ownersync")
        await bot.load_extension("joincode")
        bot.cogs_loaded = True

    check_tweets.start()
    change_status.start()
    human_like_activity.start()  # Start the human-like activity loop

async def random_sleep(min_seconds=120, max_seconds=300): # 120 300
    await asyncio.sleep(random.randint(min_seconds, max_seconds))

@tasks.loop(seconds=1)  # We'll control the interval manually
async def check_tweets():
    global last_tweet_url, sent_tweet_ids, tweet_message_map
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await random_sleep()  # Sleep 2-3 minutes randomly before each poll
    try:
        tweets = await twitter.get_recent_tweets(TRACKED_USER_ID, count=3)
        if not tweets:
            logging.info("No recent tweets found.")
            return

        # Gather sent tweet IDs from recent bot messages in Discord
        sent_ids = set()
        async for msg in channel.history(limit=75):
            if msg.author == bot.user:
                parts = msg.content.strip().split("/")
                if parts and parts[-1].isdigit():
                    sent_ids.add(parts[-1])

        # Find tweets that haven't been sent yet, stop at first already sent
        tweets_to_send = []
        for tweet in tweets:
            tweet_id = str(tweet.id)
            if tweet_id in sent_ids:
                break
            tweets_to_send.append(tweet)

        # Send new tweets in order from oldest to newest
        for tweet in reversed(tweets_to_send):
            tweet_url = f"https://vxtwitter.com/{tweet.user.screen_name}/status/{tweet.id}"
            msg = await channel.send(tweet_url)
            logging.info(f"Sent tweet {tweet.id} to channel {channel.id} as message {msg.id}")
    except Exception as e:
        logging.error(f"Error fetching tweets: {e}")

# flask server for render web service compatibility
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# start flask server in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)