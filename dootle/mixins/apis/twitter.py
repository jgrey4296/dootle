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
import twitter as tw

tweet_size         : Final[int] = doot.config.on_fail(250, int).twitter.tweet_size()
tweet_img_types    : Final[list] = doot.config.on_fail([".jpg", ".png", ".gif"], list).twitter.image_types()
tweet_image_size   : Final[int] = doot.config.on_fail(4_500_000, int).twitter.max_image()
sleep_batch        : Final[int|float] = doot.config.on_fail(2.0,   int|float).batch.sleep()
twitter_batch_size : Final[int] = doot.config.on_fail(100, int).twitter.batch_size()

REPLY              : Final[str] = 'in_reply_to_status_id_str'
QUOTE              : Final[str] = 'quoted_status_id_str'
ID_STR             : Final[str] = "id_str"

class TwitterMixin:

    twitter : TwitterApi
    todos : TweetTodoFile
    library_ids : set

    def setup_twitter(self, config:pl.Path|str):
        logging.debug("---------- Initialising Twitter")
        secrets      = tomler.load(pl.Path(config).expanduser())
        should_sleep = secrets.DEFAULT.sleep
        logging.debug("Loaded Secrets")
        self.twitter = tw.Api(
            consumer_key=secrets.twitter.py.apiKey,
            consumer_secret=secrets.twitter.py.apiSecret,
            access_token_key=secrets.twitter.py.accessToken,
            access_token_secret=secrets.twitter.py.accessSecret,
            sleep_on_rate_limit=should_sleep,
            tweet_mode='extended'
            )
        logging.debug("Twitter Initialised")
        return True

    def post_tweet(self, task):
        try:
            logging.debug("Posting Tweet")
            msg = task.values['msg']
            if len(msg) >= tweet_size:
                logging.warning("Resulting Tweet too long for twitter: %s\n%s", len(msg), msg)
                return { "twitter_result": False }
            else:
                result   = self.twitter.PostUpdate(msg)
                logging.debug("Tweet Posted")
                return {"twitter_result": True}
        except Exception as err:
            logging.warning("Twitter Post Failure: %s", err, msg)
            return {"twitter_result": False}

    def post_twitter_image(self, task):
        try:
            logging.debug("Posting Image Tweet")
            msg          = task.values.get('msg', "")
            desc         = task.values.get('desc', '')
            the_file     = pl.Path(task.values['image']).expanduser()
            # if the_file.stat().st_size > tweet_image_size:
            #     the_file = compress_file(the_file)

            assert(the_file.exists())
            assert(the_file.stat().st_size < tweet_image_size)
            assert(the_file.suffix.lower() in tweet_img_types)
            result = self.twitter.UploadMediaChunked(str(the_file))
            self.twitter.PostMediaMetadata(result, alt_text=desc)
            result = self.twitter.PostUpdate(msg, media=result)
            logging.debug("Twitter Image Posted")
            return {"twitter_result": True }
        except Exception as err:
            logging.warning("Twitter Post Failed: %s %s %s", str(err), msg, the_file)
            return { "twitter_result": False }

    def tw_download_tweets(self, target_dir, missing_file, task):
        """
        Download all tweets and related tweets for a list,
        """
        assert(target_dir.is_dir())
        logging.debug("Downloading tweets to: %s", target_dir)
        queue : list[str] = task.values['target_ids']
        if not bool(queue):
            logging.debug("No Ids to Download")
            return { "downloaded": [], "missing": [] }

        downloaded  = set()
        missing_ids = set()
        # Download in batches:
        while bool(queue):
            logging.debug("Download Queue Remaining: %s", len(queue))
            # Pop group amount:
            current = list(set(queue[:twitter_batch_size]) - self.library_ids - missing_ids)
            queue   = queue[twitter_batch_size:]

            ## download tweets
            results = self.twitter.GetStatuses(current, trim_user=True)
            # update ids
            new_ids = [x.id_str for x in results]
            self.library_ids.update(new_ids)
            downloaded.update(new_ids)
            # Save as json
            self._save_downloaded(target_dir, results)

            # Add new referenced ids:
            for x in results:
                if REPLY in x._json and x._json[REPLY] is not None:
                    queue.append(str(x._json[REPLY]))
                if QUOTE in x._json and x._json[QUOTE] is not None:
                    queue.append(x._json[QUOTE])

            # Store missing ids
            batch_missing = set(current).difference([x._json[ID_STR] for x in results])
            if bool(batch_missing):
                missing_ids.update(batch_missing)
                self._save_missing(missing_file, batch_missing)
            if sleep_batch > 0:
                time.sleep(sleep_batch)


        return { "downloaded" : list(downloaded), "missing": list(missing_ids) }

    def _save_downloaded(self, target_dir, results):
        # add results to results dir
        new_json_file = target_dir / f"{uuid.uuid4().hex}.json"
        while new_json_file.exists():
            new_json_file = target_dir / f"{uuid.uuid4().hex}.json"

        dumped  = [json.dumps(x._json, indent=4) for x in results]
        as_json = "[{}]".format(",".join(dumped))
        new_json_file.write_text(as_json)


    def _save_missing(self, target_file, missing):
        with open(target_file, 'a') as f:
            f.write("\n" + "\n".join(missing))

