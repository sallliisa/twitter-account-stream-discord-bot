import tweepy
import asyncio

class BaseUtils():
    def __init__(self):
        pass
    
    def list_diff(self, a, b):
        result = [x for x in a if x not in b]
        return None if result == [] else result

    def filter(self, data, keyword_config):
        data = [tweet for tweet in data if tweet.in_reply_to_user_id is None]
        if keyword_config is None:
            return data
        return [tweet for tweet in data if any(keyword in tweet.text.split() for keyword in keyword_config["keywords_include"]) and not any(keyword in tweet.text.split() for keyword in keyword_config["keywords_exclude"])]

class DataStream(BaseUtils):
    def __init__(self, t_client: tweepy.Client, user_id, name, keyword_config=None, interval=40):
        BaseUtils.__init__(self)
        self.t_client = t_client
        self.user_id = user_id
        self.name = name
        self.keyword_config = keyword_config
        self.interval = interval
        self.status = False
        self.user = self.t_client.get_users(ids=self.user_id, user_fields=["profile_image_url"]).data[0]
        self.data_previous = []
        self.data_current = []
        self.data_new = []
    
    def on_connect(self):
        self.status = True
        self.data_current = self.t_client.get_users_tweets(id=self.user_id, user_auth=True, max_results=10, tweet_fields=["in_reply_to_user_id", "created_at"]).data
        pass

    def stop_stream(self):
        self.status = False

    def update(self):
        self.data_previous = self.data_current
        self.data_current = self.t_client.get_users_tweets(id=self.user_id, user_auth=True, max_results=10, tweet_fields=["in_reply_to_user_id", "created_at"]).data
        self.data_new = self.list_diff(self.data_current, self.data_previous)

    async def stream(self):
        self.on_connect()
        while True:
            if not self.status:
                break
            self.update()
            if self.data_new:
                matching_data = self.filter(self.data_new, self.keywords_config)
                for tweet in reversed(matching_data):
                    yield tweet
            await asyncio.sleep(self.interval)