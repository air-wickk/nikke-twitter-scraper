import os
import asyncio
import json
from discord.ext import commands, tasks
from discord import Intents
from dotenv import load_dotenv
from twitterclient import TwitterClient
from collections import deque
from threading import Thread
from flask import Flask

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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_tweets.start()
    check_deleted_tweets.start()

@tasks.loop(minutes=1)
async def check_tweets():
    global last_tweet_url, sent_tweet_ids, tweet_message_map
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        tweet_url = await twitter.get_latest_tweet_url(TRACKED_USER_ID)
        if tweet_url:
            tweet_id = tweet_url.split('/')[-1]
            # Check JSON as before
            if tweet_id in sent_tweet_ids:
                return
            # fetch last message sent by the bot in the channel
            async for msg in channel.history(limit=50):  # check up to 50 recent messages
                if msg.author == bot.user:
                    if tweet_url in msg.content:
                        print("Last message sent by bot is the same tweet, skipping.")
                        return
                    break  # only check the most recent bot message
            # send the tweet if not duplicate
            msg = await channel.send(tweet_url)
            sent_tweet_ids.append(tweet_id)
            tweet_message_map[tweet_id] = msg.id
            save_sent_tweet_ids(sent_tweet_ids)
            save_tweet_message_map(tweet_message_map)
    except Exception as e:
        print(f"Error fetching tweets: {e}")

@tasks.loop(minutes=1)
async def check_deleted_tweets():
    global sent_tweet_ids, tweet_message_map
    # get all tweet IDs currently tracked
    tweet_ids = list(tweet_message_map.keys())
    if not tweet_ids:
        return
    # check which tweets still exist
    try:
        existing_tweet_ids = await twitter.check_existing_tweet_ids(TRACKED_USER_ID, tweet_ids)
        deleted_ids = set(tweet_ids) - set(existing_tweet_ids)
        if deleted_ids:
            channel = bot.get_channel(DISCORD_CHANNEL_ID)
            for tweet_id in deleted_ids:
                # delete the discord message
                msg_id = tweet_message_map.get(tweet_id)
                if msg_id:
                    try:
                        msg = await channel.fetch_message(msg_id)
                        await msg.delete()
                    except Exception as e:
                        print(f"Could not delete Discord message for tweet {tweet_id}: {e}")
                # remove from tracking
                if tweet_id in sent_tweet_ids:
                    sent_tweet_ids.remove(tweet_id)
                tweet_message_map.pop(tweet_id, None)
            save_sent_tweet_ids(sent_tweet_ids)
            save_tweet_message_map(tweet_message_map)
    except Exception as e:
        print(f"Error checking/deleting tweets: {e}")

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