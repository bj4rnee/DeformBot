DEBUG = True
import os
import random
import time
from urllib import request
import psutil
import requests
import uuid
import shutil
import asyncio
import traceback
import math
import gc
from numpy import interp
from argparse import ArgumentParser
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv, set_key
from io import BytesIO
from glob import glob
from PIL import Image
from pympler.tracker import SummaryTracker
from pympler import summary, muppy
import tweepy

load_dotenv("../discord/.env")
CONSUMER_KEY = os.getenv('TWITTER_OAUTH_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('TWITTER_OAUTH_CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN_MANAGE')
USER_ID = os.getenv('DB_USER_ID')
since_id = int(os.getenv('last_id'))

# UNFORTUNATELY THIS WORKS ONLY IN v1.1 API
# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Create API object
api = tweepy.API(auth, wait_on_rate_limit=True)
try:
    api.verify_credentials()
except Exception as e:
    raise e
print("[Twitter] Authentication Successful!")

# Create Client object FOR v2 API ONLY
tw_client = tweepy.Client(BEARER_TOKEN, CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, wait_on_rate_limit=True)


def check_mentions(api, s_id):
    """check mentions in v1.1 api"""
    # Retrieving mentions
    new_since_id = s_id
    twitter_media_url = ""
    for tweet in tweepy.Cursor(api.mentions_timeline, since_id=s_id, count=100, tweet_mode='extended').items():
        new_since_id = max(tweet.id, new_since_id)
        #os.environ['last_id'] = str(new_since_id)
        set_key("../discord/.env", 'last_id', str(new_since_id))
        if hasattr(tweet, 'text'):
            tweet_txt = tweet.text.lower()
        else:
            tweet_txt = ""
        if hasattr(tweet, 'possibly_sensitive'):
            sensitive = tweet.possibly_sensitive
        else:
            sensitive = False
        reply_og_id  = tweet.in_reply_to_status_id # original status (if 'tweet' is a reply)
        if DEBUG:
            print("[DEBUG] tweet from " + tweet.user.screen_name + ": '" + tweet_txt + "', sensitive: " + str(sensitive) + ", reply: " + str(reply_og_id))
        
        if 'media' in tweet.entities: # tweet that mentionions db contains image
            raw_image = tweet.entities.get('media', [])
            if(len(raw_image) > 0):
                twitter_media_url = raw_image[0]['media_url']
            else:
                twitter_media_url = "[ERROR] No url found"
            print(twitter_media_url)
        else: # tweet that the mentioner replies to contains image
            if isinstance(reply_og_id, str) or isinstance(reply_og_id, int):
                r_tweet = api.get_status(reply_og_id)
                if 'media' in r_tweet.entities:
                    raw_image = r_tweet.entities.get('media', [])
                    if(len(raw_image) > 0):
                        twitter_media_url = raw_image[0]['media_url']
                    else:
                        twitter_media_url = "[ERROR] No url found"
                    print(twitter_media_url)
                else:
                    api.update_status(status="[ERROR] no media found.", in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
                    continue
            else:
                continue

        #result_img = api.media_upload("created_image.png") # TODO 5MB FILESIZE LIMIT!!!!!!!!!!!!!

        api.update_status(status="[DEBUG] fetching image...", in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True, possibly_sensitive=sensitive)
        #api.update_status('@' + tweet.user.screen_name + " Here's your Quote", tweet.id, media_ids=[result_img.media_id])
    return new_since_id

def check_mentions_v2(s_id):
    """
    check mentions in v2 api
    - CURRENTLY NOT IN USE
    """
    new_since_id = s_id
    # Retrieving mentions
    mentions = tw_client.get_users_mentions(id=USER_ID, max_results=100, since_id=s_id)
    for tweet in mentions:
        new_since_id = max(tweet.id, new_since_id)

    print(mentions)
    return 0

#tw_client.create_tweet(text="Hello, Twitter!")
#api.update_status("This is the 2nd test!")
while True:
    since_id = check_mentions(api, since_id)
    #since_id = check_mentions_v2(since_id)
    time.sleep(60)
