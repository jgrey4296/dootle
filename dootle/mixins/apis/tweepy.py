#!/usr/bin/env py
# pylint: disable=no-memberthon3
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as logmod
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast, Final)

import requests
##-- end imports

logging = logmod.getLogger(__name__)

import webbrowser
import time
import json
import uuid
import doot
from doot.mixins.batch import BatchMixin
import tomler
import tweepy

tweet_size         : Final[int] = doot.config.on_fail(250, int).twitter.tweet_size()
tweet_img_types    : Final[list] = doot.config.on_fail([".jpg", ".png", ".gif"], list).twitter.image_types()
tweet_image_size   : Final[int] = doot.config.on_fail(4_500_000, int).twitter.max_image()
sleep_batch        : Final[int|float] = doot.config.on_fail(2.0,   int|float).batch.sleep()
twitter_batch_size : Final[int] = doot.config.on_fail(100, int).twitter.batch_size()

REPLY              : Final[str] = 'in_reply_to_status_id_str'
QUOTE              : Final[str] = 'quoted_status_id_str'
ID_STR             : Final[str] = "id_str"

class TweepyMixin:

    twitter : TwitterApi
    todos : TweetTodoFile
    library_ids : set

    def setup_twitter(self, config:pl.Path|str):
        logging.debug("---------- Initialising Tweepy")
        secrets      = tomler.load(pl.Path(config).expanduser())
        match secrets.twitter.method:
            case "v1bearer":
                self.setup_twitter_v1_bearer(secrets)
            case "v1uc":
                self.setup_twitter_v1_user_context(secrets)
            case "v2bearer":
                self.setup_twitter_v2_bearer(secrets)
            case "v2uc":
                self.setup_twitter_v2_user_context(secrets)
            case "v2pkce":
                self.setup_twitter_v2_pkce(secrets)
            case "v2pin":
                self.setup_twitter_v2_pin(secrets)

    def setup_twitter_v1_bearer(self, secrets):
        logging.debug("---------- Initialising V1 OAuth2 Bearer")
        auth         = tweepy.OAuth2BearerHandler(secrets.twitter.py.bearerToken)
        self.twitter = tweepy.API(auth)

        return True

    def setup_twitter_v1_user_context(self, secrets):
        logging.debug("---------- Initialising V1 OAuth1 User Context")
        auth         = tweepy.OAuth1UserHandler(
            secrets.twitter.py.apiKey, secrets.twitter.py.apiSecret,
            secrets.twitter.py.accessToken, secrets.twitter.py.accessSecret
            )
        self.twitter = tweepy.API(auth)

        return True

    def setup_twitter_v2_bearer(self, secrets):
        logging.debug("---------- Initialising V2 OAuth2 Bearer")
        self.twitter = tweepy.Client(secrets.twitter.py.bearerToken)
        return True

    def setup_twitter_v2_user_context(self, secrets):
        logging.debug("---------- Initialising V2 OAuth2 Bearer")
        self.twitter = tweepy.Client(
            consumer_key=secrets.twitter.py.apiKey,
            consumer_secret=secrets.twitter.py.apiSecret,
            access_token=secrets.twitter.py.accessToken,
            access_token_secret=secrets.twitter.py.accessSecret
            )
        return True

    def setup_twitter_v2_pkce(self, secrets):
        logging.debug("---------- Initialising V2 OAuth2 Bearer")
        handler = tweepy.OAuth2UserHandler(
            client_id=secrets.twitter.py.clientID,
            client_secret=secrets.twitter.py.clientSecret,
            redirect_uri=secrets.twitter.py.redirect,
            scope=["bookmark.read", "tweet.read", "users.read"],
            )
        webbrowser.open(handler.get_authorization_url())
        verifier = input("Input response: ").strip()
        token = handler.fetch_token(verifier)
        assert(isinstance(token, dict))
        self.twitter = tweepy.Client(token['access_token'])
        breakpoint()
        pass
        return True

    def setup_twitter_v2_pin(self, secrets):
        logging.debug("---------- Initialising V2 OAuth2 Bearer")
        oauth1_user_handler = tweepy.OAuth1UserHandler(
            secrets.twitter.py.apiKey, secrets.twitter.py.apiSecret,
            callback="oob"
        )
        webbrowser.open(oauth1_user_handler.get_authorization_url())
        verifier = input("Input PIN: ")
        access_token, access_token_secret = oauth1_user_handler.get_access_token(verifier)
        self.twitter = tweepy.Client(
            consumer_key=secrets.twitter.py.apiKey,
            consumer_secret=secrets.twitter.py.apiSecret,
            access_token=access_token,
            access_token_secret=access_token_secret
            )


    def get_bookmarks(self):
        return self.twitter.get_bookmarks()
