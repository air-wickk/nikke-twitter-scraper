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
GUILD_ID = int(os.getenv("GUILD_ID"))  # Add this to your .env

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

"""
async def random_human_sleep():
    # Wait between 15 and 40 minutes between "human" actions
    await asyncio.sleep(random.randint(900, 2400))

@tasks.loop(seconds=10)
async def human_like_activity():
    await random_human_sleep()
    try:
        action = random.choice(["bookmark", "notifications", "like", "search"])
        if action == "bookmark":
            tweets = await twitter.search_tweet('NIKKE', limit=1)
            tweet = next(iter(tweets), None)
            if tweet:
                await twitter.bookmark_tweet(tweet)
                logging.info(f"Simulated human: bookmarked tweet {tweet.id}.")
        elif action == "notifications":
            notifications = await twitter.get_notifications()
            logging.info(f"Simulated human: checked notifications, got {len(notifications)} items.")
        elif action == "like":
            tweets = await twitter.search_tweet('NIKKE', limit=1)
            tweet = next(iter(tweets), None)
            if tweet:
                await twitter.like_tweet(tweet)
                logging.info(f"Simulated human: liked tweet {tweet.id}.")
        elif action == "search":
            await twitter.search_tweet('NIKKE', limit=1)
            logging.info("Simulated human: performed a search.")
    except Exception as e:
        logging.warning(f"Human-like activity failed: {e}")
"""
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    guild = discord.Object(id=GUILD_ID)
    # Sync commands only to your guild
    await bot.tree.sync(guild=guild)
    print(f"Synced commands to guild {GUILD_ID}")

    # Load cogs (only once)
    if not hasattr(bot, "cogs_loaded"):
        await bot.load_extension("suggestions")
        await bot.load_extension("ownersync")
        await bot.load_extension("joincode")
        bot.cogs_loaded = True

    check_tweets.start()
    change_status.start()
    #human_like_activity.start() 

async def random_sleep(min_seconds=30, max_seconds=90): # 120 300
    await asyncio.sleep(random.randint(min_seconds, max_seconds))

@tasks.loop(seconds=1)
async def check_tweets():
    global last_tweet_url, sent_tweet_ids, tweet_message_map
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    await random_sleep()
    try:
        tweets = await twitter.get_user_tweets(TRACKED_USER_ID, limit=3)
        # logging.info(f"Fetched {len(tweets)} tweets: {[getattr(t, 'id', None) for t in tweets]}")
        if not tweets:
            # logging.info("No recent tweets found.")
            return

        # Gather sent tweet IDs from recent bot messages in Discord
        sent_ids = set()
        async for msg in channel.history(limit=300):
            if msg.author == bot.user:
                parts = msg.content.strip().split("/")
                if parts and parts[-1].isdigit():
                    sent_ids.add(parts[-1])
        # logging.info(f"Sent tweet IDs found: {sent_ids}")

        # Find tweets that haven't been sent yet, stop at first already sent
        tweets_to_send = []
        for tweet in tweets:
            # Send in reverse order
            if hasattr(tweet, "tweets"):
                for t in reversed(tweet.tweets):
                    if hasattr(t, "id"):
                        tweet_id = str(t.id)
                        if tweet_id not in sent_ids:
                            tweets_to_send.append(t)
            elif hasattr(tweet, "id"):
                tweet_id = str(tweet.id)
                if tweet_id not in sent_ids:
                    tweets_to_send.append(tweet)
            # Handle tweets with a card or quoted_status
            elif hasattr(tweet, "card"):
                card = tweet.card
                # If the card has a tweet id, send it
                if hasattr(card, "id"):
                    tweet_id = str(card.id)
                    if tweet_id not in sent_ids:
                        tweets_to_send.append(card)
            elif hasattr(tweet, "quoted_status"):
                quoted = tweet.quoted_status
                if hasattr(quoted, "id"):
                    tweet_id = str(quoted.id)
                    if tweet_id not in sent_ids:
                        tweets_to_send.append(quoted)

        # Send new tweets in order from oldest to newest
        for tweet in reversed(tweets_to_send):
            tweet_url = f"https://vxtwitter.com/{tweet.author.username}/status/{tweet.id}"
            msg = await channel.send(tweet_url)
            # logging.info(f"Sent tweet {tweet.id} to channel {channel.id} as message {msg.id}")
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