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

    async def login(self):
        if not self.logged_in:
            await self.client.login(
                auth_info_1=self.username,
                auth_info_2=self.email,
                password=self.password,
                cookies_file='cookies.json'
            )
            self.logged_in = True

    async def get_latest_tweet_url(self, user_id):
        await self.login()
        tweets = await self.client.get_user_tweets(user_id, 'Tweets')
        if tweets:
            tweet = tweets[0]
            return f"https://girlcockx.com/{tweet.user.screen_name}/status/{tweet.id}"
        return None

    async def check_existing_tweet_ids(self, user_id, tweet_ids):
        await self.login()
        tweets = await self.client.get_user_tweets(user_id, 'Tweets')
        existing_ids = [str(tweet.id) for tweet in tweets]
        # return only IDs from tweet_ids that still exist
        return [tid for tid in tweet_ids if tid in existing_ids]