import os
from twikit import Client
from dotenv import load_dotenv

load_dotenv()

class TwitterClient:
    def __init__(self):
        self.username = os.getenv('LOGIN_USERNAME')
        self.email = os.getenv('LOGIN_EMAIL')
        self.password = os.getenv('LOGIN_PASSWORD')
        self.client = Client('en-US')
        self.logged_in = False
        self.cookies_file = 'cookies.json'

    async def login(self):
        if self.logged_in:
            return
        if os.path.exists(self.cookies_file):
            try:
                self.client.load_cookies(self.cookies_file)
                await self.client.get_home_timeline()
                self.logged_in = True
                return
            except Exception as e:
                print(f"Failed to load cookies or cookies expired: {e}")
        # if loading cookies failed, do a full login
        await self.client.login(
            auth_info_1=self.username,
            auth_info_2=self.email,
            password=self.password,
            cookies_file=self.cookies_file
        )
        self.logged_in = True
        # save cookies after successful login
        self.client.save_cookies(self.cookies_file)

    async def get_latest_tweet_url(self, user_id):
        await self.login()
        tweets = await self.client.get_user_tweets(user_id, 'Tweets')
        if tweets:
            tweet = tweets[0]
            return f"https://girlcockx.com/{tweet.user.screen_name}/status/{tweet.id}"
        return None

    async def check_tweet_exists(self, tweet_id):
        await self.login()
        try:
            tweet = await self.client.get_tweet_detail(tweet_id)
            return tweet is not None
        except Exception as e:
            # detect rate limit or ambiguous errors
            if "rate limit" in str(e).lower() or "429" in str(e):
                print(f"Rate limit hit while checking tweet {tweet_id}: {e}")
                return None  # ambiguous, do NOT delete
            return None  # ambiguous, do NOT delete

    async def get_recent_tweets(self, user_id, count=3):
        await self.login()
        try:
            tweets = await self.client.get_user_tweets(user_id, 'Tweets')
            filtered = [tweet for tweet in tweets if getattr(tweet, "in_reply_to_status_id", None) is None]
            return filtered[:count] if filtered else []
        except Exception as e:
            # handle rate limit, etc.
            return []