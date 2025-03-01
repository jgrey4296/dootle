#/usr/bin/env python3
"""
A Direct Firefox sqlite databse -> bookmarks file merger
uses pony
Database is found at ~/Library/ApplicationSupport/Firefox/Profiles/?/places.sqlite
tables of interest: moz_bookmarks and moz_places
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import tempfile
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from re import Pattern
from shutil import copy
from sys import stderr, stdout
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
import pony.orm as pony
from jgdv.files.bookmarks.bookmark import Bookmark
from jgdv.files.bookmarks.collection import BookmarkCollection

# ##-- end 3rd party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    import pathlib as pl
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def init_db() -> tuple[pony.Database, *type]:
    db = pony.Database()

    ##-- ORM

    class DBBookmark(db.Entity):
        """
        Schema of moz_bookmarks
        type   = 1 if bookmark, 2 if metadata
        parent = 4 if a tag
        fk     = foreign key to moz_place for url

        So a bookmark uses fk to point to the url.
        If the bookmark has tags, each tag is a bookmark entry,
        with no title, same fk as the bookmark,
        parent points to the tag name entry.
        The tag name entry has a title, but no fk
        and it's parent points to entry 4: 'tags'
        """
        _table_                 = "moz_bookmarks"
        type              : int = pony.Required(int)
        fk                : int = pony.Optional(int)
        parent            : int = pony.Required(int)
        position          : int = pony.Required(int)
        title             : str = pony.Optional(str)
        keyword_id        : int = pony.Optional(int)
        folder_type       : str = pony.Optional(str)
        dateAdded         : int = pony.Required(int)  # noqa: N815
        lastModified      : int = pony.Required(int)  # noqa: N815
        guid              : str = pony.Required(str)
        syncStatus        : int = pony.Required(int)  # noqa: N815
        syncChangeCounter : int = pony.Required(int)  # noqa: N815

    class DBURL(db.Entity):
        """
        a url entry in moz_places.
        url field is the important bit.
        the DBURL's id is used for the fk of a bookmark
        """
        _table_                 = "moz_places"
        url               : str = pony.Required(str)
        title             : str = pony.Optional(str)
        rev_host          : str = pony.Required(str)
        visit_count       : int = pony.Required(int)
        hidden            : int = pony.Required(int)
        typed             : int = pony.Required(int)
        frecency          : int = pony.Required(int)
        last_visit_date   : int = pony.Optional(int)
        guid              : str = pony.Required(str)
        foreign_count     : int = pony.Required(int)
        url_hash          : int = pony.Required(int)
        description       : str = pony.Optional(str)
        preview_image_url : str = pony.Optional(str)
        origin_id         : int = pony.Required(int)
        site_name         : str = pony.Optional(str)

    ##-- end ORM
    return db, DBBookmark, DBURL

def extract(fpath:pl.Path, debug:bool=False) -> BookmarkCollection:  # noqa: FBT001, FBT002
    db, DBBookmark, DBURL = init_db()  # noqa: N806

    pony.set_sql_debug(debug)

    tag_names                          = {}
    bookmark_tags                      = defaultdict(lambda: set())
    collection : BookmarkCollection    = BookmarkCollection()

    ##-- bind database and mappings
    db.bind(provider='sqlite', filename=str(fpath), create_db=False)
    db.generate_mapping(create_tables=False)
    ##-- end bind database and mappings

    ##-- session use
    logging.info("Extracting bookmarks")
    parent_type : int = 4
    with pony.db_session:
        tag_names = {b.id : b.title
                     for b in pony.select(b for b in DBBookmark
                                          if b.title is not None
                                          and b.fk is None and b.parent == parent_type)}
        for b in pony.select(b for b in DBBookmark if b.title is None and b.fk is not None):
            if b.parent not in tag_names:
                continue
            bookmark_tags[b.fk].add(tag_names[b.parent])

        query  = pony.select(b for b in DBBookmark if b.title is not None and b.fk is not None)
        result = query[:]
        for x in result:
            bkmk : Bookmark = Bookmark(url=DBURL[x.fk].url, tags=bookmark_tags[x.fk], name=x.title)
            collection += bkmk
    ##-- end session use

    return collection
