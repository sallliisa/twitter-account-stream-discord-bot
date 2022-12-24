import tweepy
import asyncio
import string

class BaseUtils():
    def __init__(self):
        pass
    
    def list_diff(self, a, b):
        result = [x for x in a if x not in b]
        return None if result == [] else result

    def filter(self, tweet, keyword_config):
        if tweet.in_reply_to_user_id is not None:
            return None
        if keyword_config is None:
            return tweet
        else:
            tweet_cleaned = tweet.text.translate(str.maketrans('', '', string.punctuation)).lower()
            if any(keyword in tweet_cleaned.split() for keyword in keyword_config["keywords_include"]) and not any(keyword in tweet_cleaned.split() for keyword in keyword_config["keywords_exclude"]):
                return tweet

class DataStream(BaseUtils):
    def __init__(self, t_client: tweepy.Client, user_id, interval=40):
        BaseUtils.__init__(self)
        self.t_client = t_client
        self.user_id = user_id
        self.interval = interval
        self.status = False
        self.user = self.t_client.get_users(ids=self.user_id, user_fields=["profile_image_url"]).data[0]
        self.name = self.user.username
        self.data_previous = []
        self.data_current = []
        self.data_new = []
    
    def on_connect(self):
        self.status = True
        self.data_current = self.t_client.get_users_tweets(id=self.user_id, user_auth=True, max_results=10, tweet_fields=["in_reply_to_user_id", "created_at"]).data

    def stop_stream(self):
        self.status = False

    def update(self):
        self.data_previous = self.data_current
        self.data_current = self.t_client.get_users_tweets(id=self.user_id, user_auth=True, max_results=10, tweet_fields=["in_reply_to_user_id", "created_at"]).data
        self.data_new = self.list_diff(self.data_current, self.data_previous)

    async def stream(self):
        self.on_connect()
        while True:
            try:
                if not self.status:
                    break
                self.update()
                if self.data_new:
                    for tweet in reversed(self.data_new):
                        yield tweet
                await asyncio.sleep(self.interval)
            except Exception as e:
                with open("error.log", "a") as f:
                    f.write(f"FROM DATASTREAM {self.name}: {e}\r")

class FilterStream():
    def __init__(self, name, data_stream: DataStream, keyword_config=None, keyword_config_name=None):
        self.name = name
        self.data_stream = data_stream
        self.keyword_config = keyword_config
        self.keyword_config_name = keyword_config_name
        self.status = False
    
    def on_connect(self):
        self.status = True

    def stop_stream(self):
        self.status = False
    
    async def stream(self):
        self.on_connect()
        while True:
            try:
                if not self.status:
                    break
                async for tweet in self.data_stream.stream():
                    if self.data_stream.filter(tweet, self.keyword_config):
                        yield tweet
            except Exception as e:
                with open("error.log", "a") as f:
                    f.write(f"FROM FILTERSTREAM {self.data_stream.name}: {e}\r")