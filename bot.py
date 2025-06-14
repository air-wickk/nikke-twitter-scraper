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

intents = Intents.default()
intents.guilds = True
intents.messages = True

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
    "for leaks about my true identity",
    "for Pilgrim transmissions.",
    "the Outpost's coffee machine",
    "the Ark's communication channels",
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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_tweets.start()
    check_deleted_tweets.start()
    change_status.start()

@tasks.loop(minutes=2)
async def check_tweets():
    global last_tweet_url, sent_tweet_ids, tweet_message_map
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        tweets = await twitter.get_recent_tweets(TRACKED_USER_ID, count=3)
        if not tweets:
            logging.info("No recent tweets found.")
            return
        # post from oldest to newest
        for tweet in reversed(tweets):
            tweet_url = f"https://girlcockx.com/{tweet.user.screen_name}/status/{tweet.id}"
            tweet_id = str(tweet.id)
            if tweet_id in sent_tweet_ids:
                continue
            # Check last 10 messages from the bot for duplicates
            bot_messages_checked = 0
            duplicate_found = False
            async for msg in channel.history(limit=200): # Number of messages in general to check
                if msg.author == bot.user:
                    bot_messages_checked += 1
                    if tweet_url in msg.content:
                        duplicate_found = True
                        break
                    if bot_messages_checked >= 10:
                        break
            if duplicate_found:
                continue
            msg = await channel.send(tweet_url)
            logging.info(f"Sent tweet {tweet_id} to channel {channel.id} as message {msg.id}")
            sent_tweet_ids.append(tweet_id)
            tweet_message_map[tweet_id] = msg.id
            save_sent_tweet_ids(sent_tweet_ids)
            save_tweet_message_map(tweet_message_map)
    except Exception as e:
        logging.error(f"Error fetching tweets: {e}")

@tasks.loop(minutes=10)
async def check_deleted_tweets():
    global sent_tweet_ids, tweet_message_map
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    # check only the most recent tweet/message (1)
    tweet_ids = list(tweet_message_map.keys())[-1:]
    if not tweet_ids:
        logging.info("No tweet IDs to check for deletion.") # logging
        return
    try:
        deleted_ids = set()
        for tweet_id in tweet_ids:
            try:
                exists = await twitter.check_tweet_exists(tweet_id)
                logging.info(f"Checked tweet {tweet_id}: exists={exists}") # logging
            except Exception as e:
                logging.warning(f"Error checking tweet {tweet_id}: {e}") # logging
                continue
            if exists is False:
                logging.info(f"Tweet {tweet_id} confirmed deleted on Twitter, marking for Discord deletion.") # logging
                deleted_ids.add(tweet_id)
            else:
                # if exists is true or none/ambiguous, do NOT delete
                continue
        if deleted_ids:
            for tweet_id in deleted_ids:
                msg_id = tweet_message_map.get(tweet_id)
                if msg_id:
                    try:
                        msg = await channel.fetch_message(msg_id)
                        await msg.delete()
                        logging.info(f"Deleted Discord message {msg_id} for tweet {tweet_id}.") # logging
                    except Exception as e:
                        logging.error(f"Could not delete Discord message for tweet {tweet_id}: {e}") # logging
                if tweet_id in sent_tweet_ids:
                    sent_tweet_ids.remove(tweet_id)
                tweet_message_map.pop(tweet_id, None)
            save_sent_tweet_ids(sent_tweet_ids)
            save_tweet_message_map(tweet_message_map)
    except Exception as e:
        logging.error(f"Error checking/deleting tweets: {e}") # logging

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