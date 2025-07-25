import os
from dotenv import load_dotenv
from tweety import TwitterAsync

load_dotenv()

class TwitterClient:
    def __init__(self):
        self.username = os.getenv('LOGIN_USERNAME')
        self.email = os.getenv('LOGIN_EMAIL')
        self.password = os.getenv('LOGIN_PASSWORD')
        self.session_dir = "session"
        self.client = TwitterAsync(self.session_dir)
        self.logged_in = False

    async def login(self):
        if self.logged_in:
            return
        try:
            await self.client.sign_in(self.username, self.password)
            self.logged_in = True
        except Exception as e:
            print(f"Login failed or extra action required: {e}")
            # Optionally prompt for extra info here if you want
            self.logged_in = False

    async def search_tweet(self, query, limit=1):
        await self.login()
        try:
            tweets = await self.client.asyncsearch_tweet(query, product="Latest", count=limit)
            return tweets
        except Exception as e:
            print(f"Error searching tweets: {e}")
            return []

    async def like_tweet(self, tweet):
        await self.login()
        try:
            await self.client.favorite_tweet(tweet.id)
        except Exception as e:
            print(f"Error liking tweet: {e}")

    async def bookmark_tweet(self, tweet):
        await self.login()
        try:
            await self.client.bookmark_tweet(tweet.id)
        except Exception as e:
            print(f"Error bookmarking tweet: {e}")

    async def get_notifications(self):
        await self.login()
        try:
            notifs = await self.client.get_notifications("Mentions")
            return notifs
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return []

    async def get_user_tweets(self, username, limit=3):
        await self.login()
        try:
            user_tweets = await self.client.get_tweets(username, pages=1)
            return user_tweets.tweets[:limit]
        except Exception as e:
            print(f"Error fetching user tweets: {e}")
            return []