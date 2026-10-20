import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from types import SimpleNamespace

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TwitterClient:
    def __init__(self):
        # Session for public X profile pages. No Twitter login required.
        self.http = requests.Session()

        self.http.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

    # ================================================================
    # X HTML parsing helpers
    # ================================================================

    @staticmethod
    def _decode_x_string(value):
        # X currently double-escapes some sequences (e.g. newlines as
        # \\\\n), so decode twice when the first pass still leaves
        # backslash escapes behind.
        decoded = value

        try:
            decoded = json.loads(f'"{decoded}"')
        except Exception:
            decoded = (
                value
                .replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )

        if isinstance(decoded, str):
            try:
                decoded = json.loads(f'"{decoded}"')
            except Exception:
                pass

        return decoded

    @classmethod
    def _extract_x_string(cls, chunk, field):
        """
        Extract a string value for a field, tolerating both:

            full_text:"Hello\\nWorld"    (plain JS serialization)
            "full_text":"Hello\\nWorld"  (quoted-key JSON)
        """

        match = re.search(
            rf'{re.escape(field)}[\\"\s:]*"((?:\\.|[^"])*)"',
            chunk,
        )

        if not match:
            return None

        return cls._decode_x_string(match.group(1))

    # ================================================================
    # Embedded profile timeline JSON
    # ================================================================

    # Subtrees that belong to quoted tweets, reply threads, or user
    # objects rather than the tweet being displayed on the timeline.
    _SKIP_LAYERS = ("quoted", "quotet", "ancestor", "core", "user")

    @classmethod
    def _parse_embedded_timeline(cls, html):
        """
        Decode the timeline JSON embedded in an X profile page and
        return [(tweet_id, payload_dict), ...] in timeline order.

        The JSON can sit inside one or more escaped string layers, so
        we try the raw HTML plus progressively-unescaped copies and
        attempt json parsing around each known marker.
        """

        sources = [html]
        one = html.replace('\\"', '"')
        if one != html:
            sources.append(one)
            two = one.replace('\\\\', '\\')
            if two != one:
                sources.append(two)

        decoder = json.JSONDecoder()

        marker_pattern = re.compile(
            'TimelineAddEntries|tweet_results|entry_id'
        )

        for source in sources:
            marker_positions = [
                match.start()
                for match in marker_pattern.finditer(source)
            ]

            for marker_pos in marker_positions:
                brace_pos = source.rfind(
                    '{',
                    max(0, marker_pos - 3000),
                    marker_pos,
                )

                for _ in range(30):
                    if brace_pos == -1:
                        break

                    try:
                        data, _rest = decoder.raw_decode(source, brace_pos)
                    except Exception:
                        brace_pos = source.rfind('{', 0, brace_pos)
                        continue

                    if not isinstance(data, (dict, list)):
                        brace_pos = source.rfind('{', 0, brace_pos)
                        continue

                    browse = json.dumps(data, default=str)[:5_000_000]

                    if 'TimelineAddEntries' not in browse:
                        brace_pos = source.rfind('{', 0, brace_pos)
                        continue

                    payloads = []

                    cls._collect_tweet_payloads(data, set(), payloads)

                    if payloads:
                        return payloads

                    brace_pos = source.rfind('{', 0, brace_pos)

        return []

    @classmethod
    def _collect_tweet_payloads(
        cls,
        node,
        seen_ids,
        payloads,
        depth=0,
    ):
        """
        Depth-first, insertion-order walk that collects every
        tweet_results.{rest_id, result} payload in the timeline JSON.
        """

        if depth > 64:
            return

        if isinstance(node, dict):
            for key, value in node.items():
                if any(
                    hint in key.lower()
                    for hint in ("quoted", "quotet", "ancestor", "core", "user")
                ):
                    continue

                if (
                    key == "tweet_results"
                    and isinstance(value, dict)
                ):
                    tweet_id = str(value.get("rest_id") or "")

                    if re.fullmatch(r'\d{18,20}', tweet_id):
                        payload = value.get("result")

                        if isinstance(payload, dict):
                            if tweet_id not in seen_ids:
                                seen_ids.add(tweet_id)
                                payloads.append((tweet_id, payload))
                            continue

                cls._collect_tweet_payloads(
                    value,
                    seen_ids,
                    payloads,
                    depth + 1,
                )

        elif isinstance(node, list):
            for item in node:
                cls._collect_tweet_payloads(
                    item,
                    seen_ids,
                    payloads,
                    depth + 1,
                )

    @classmethod
    def _find_first_string(cls, node, wanted_keys, depth=0):
        if depth > 64:
            return None

        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                if any(
                    hint in lowered
                    for hint in ("quoted", "quotet", "ancestor")
                ):
                    continue

                if key in wanted_keys:
                    if isinstance(value, str):
                        return value
                    if isinstance(value, (dict, list)):
                        nested = cls._find_first_string(
                            value,
                            wanted_keys,
                            depth + 1,
                        )
                        if nested is not None:
                            return nested
                elif isinstance(value, (dict, list)):
                    nested = cls._find_first_string(
                        value,
                        wanted_keys,
                        depth + 1,
                    )
                    if nested is not None:
                        return nested

        elif isinstance(node, list):
            for item in node:
                found = cls._find_first_string(
                    item,
                    wanted_keys,
                    depth + 1,
                )
                if found is not None:
                    return found

        return None

    @classmethod
    def _find_tweet_is_reply(cls, node, depth=0):
        """
        True when the tweet payload contains its own in_reply_to
        metadata (meaning it replying to anyone, including the
        author replying to themselves).
        """

        if depth > 64:
            return False

        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                if any(
                    hint in lowered
                    for hint in cls._SKIP_LAYERS
                ):
                    continue

                if (
                    ("in_reply_to" in lowered or "in-reply-to" in lowered)
                    and value
                ):
                    if isinstance(value, (str, int)):
                        return True
                    if isinstance(value, (dict, list)):
                        return True

                if isinstance(value, (dict, list)):
                    if cls._find_tweet_is_reply(value, depth + 1):
                        return True

        elif isinstance(node, list):
            for item in node:
                if cls._find_tweet_is_reply(item, depth + 1):
                    return True

        return False

    @classmethod
    def _find_tweet_created_at(cls, node, depth=0):
        if depth > 64:
            return None

        if isinstance(node, dict):
            raw = node.get("created_at_ms")

            try:
                timestamp_ms = int(str(raw))
            except (TypeError, ValueError):
                timestamp_ms = None

            if timestamp_ms is not None:
                return timestamp_ms

            for key, value in node.items():
                lowered = key.lower()
                if any(
                    hint in lowered
                    for hint in cls._SKIP_LAYERS
                ):
                    continue

                found = cls._find_tweet_created_at(value, depth + 1)
                if found is not None:
                    return found

        elif isinstance(node, list):
            for item in node:
                found = cls._find_tweet_created_at(item, depth + 1)
                if found is not None:
                    return found

        return None

    def _fetch_profile_tweets_sync(self, username, limit=5):
        username = (
            str(username)
            .strip()
            .lstrip("@")
        )

        if not username:
            return []

        url = f"https://x.com/{username}"

        try:
            response = self.http.get(
                url,
                timeout=20,
            )
            response.raise_for_status()

        except requests.RequestException as e:
            logger.error(
                "Could not fetch X profile @%s: %s",
                username,
                e,
            )
            return []

        html = response.text

        logger.info(
            "Fetched X profile @%s (%s bytes)",
            username,
            len(html),
        )

        # ------------------------------------------------------------
        # Preferred path: decode the embedded timeline JSON and collect
        # tweets by their GraphQL shape. X keeps re-serializing the
        # page HTML, so exact-text matching kept breaking; walking real
        # decoded objects is far more resilient.
        # ------------------------------------------------------------

        results = []

        payloads = self._parse_embedded_timeline(html)

        if payloads:
            logger.info(
                "X profile @%s timeline JSON decoded (%s tweets)",
                username,
                len(payloads),
            )

            for tweet_id, payload in payloads:

                if len(results) >= limit:
                    break

                text = self._find_first_string(
                    payload,
                    ("full_text", "text"),
                )

                if text is None:
                    text = ""

                timestamp_ms = self._find_tweet_created_at(payload)

                created_on = None

                if timestamp_ms is not None:
                    created_on = datetime.fromtimestamp(
                        timestamp_ms / 1000,
                        tz=timezone.utc,
                    )

                is_reply = self._find_tweet_is_reply(payload)

                author = SimpleNamespace(username=username)

                tweet = SimpleNamespace(
                    id=tweet_id,
                    text=text,
                    full_text=text,
                    created_on=created_on,
                    created_at=created_on,

                    author=author,

                    is_reply=is_reply,
                    in_reply_to_status_id=None,

                    url=(
                        f"https://x.com/"
                        f"{username}/status/{tweet_id}"
                    ),
                )

                results.append(tweet)

                logger.info(
                    "X TWEET: %s | %s | reply=%s | %s",
                    tweet_id,
                    created_on,
                    is_reply,
                    text[:120].replace("\n", " "),
                )

        if results:
            return results

        # ------------------------------------------------------------
        # Fallback: legacy regex scraping for pages that do not contain
        # a parseable timeline JSON blob.
        #
        # X may embed the timeline as an escaped string, so undo one
        # layer of backslash-quote escaping first; this is a no-op for
        # pages served as plain JS/JSON.
        # ------------------------------------------------------------

        if 'entry_id:"' not in html and '\\"entry_id\\":\\"' in html:
            html = html.replace('\\"', '"')

        timeline_ids = []

        for tweet_id in re.findall(
            r"TimelineTimelineEntry:tweet-(\d+)",
            html,
        ):
            if tweet_id not in timeline_ids:
                timeline_ids.append(tweet_id)

        for tweet_id in re.findall(
            r'entry_id[\\"\s:]*tweet-(\d{18,20})',
            html,
        ):
            if tweet_id not in timeline_ids:
                timeline_ids.append(tweet_id)

        logger.info(
            "X profile @%s has %s timeline entries",
            username,
            len(timeline_ids),
        )

        results = []

        for tweet_id in timeline_ids:

            if len(results) >= limit:
                break

            # --------------------------------------------------------
            # Locate this tweet's timeline entry.
            # --------------------------------------------------------

            entry_match = re.search(
                rf'entry_id[\\"\s:]*tweet-{tweet_id}',
                html,
            )

            if entry_match is None:
                logger.warning(
                    "Could not locate timeline entry %s",
                    tweet_id,
                )
                continue

            # --------------------------------------------------------
            # Locate the tweet object. Its rest_id appears inside the
            # tweet_results object shortly before the entry_id.
            # --------------------------------------------------------

            rest_match = re.compile(
                rf'rest_id[\\"\s:]*"{tweet_id}"'
            ).search(
                html,
                max(0, entry_match.start() - 200000),
                entry_match.start(),
            )

            if rest_match is None:
                logger.warning(
                    "Could not locate tweet object %s",
                    tweet_id,
                )
                continue

            tweet_object_pos = html.rfind(
                "tweet_results",
                max(0, rest_match.start() - 500),
                rest_match.start() + 1,
            )

            if tweet_object_pos == -1:
                logger.warning(
                    "Could not anchor tweet_results for %s",
                    tweet_id,
                )
                continue

            # --------------------------------------------------------
            # Everything between the tweet object's start and this
            # entry's end holds the tweet text, timestamp, and counts.
            # --------------------------------------------------------

            details_chunk = html[
                rest_match.start() : min(
                    len(html),
                    entry_match.end() + 2000,
                )
            ]

            # --------------------------------------------------------
            # Extract tweet text.
            # --------------------------------------------------------

            text = self._extract_x_string(
                details_chunk,
                "full_text",
            )

            if not text:
                text = self._extract_x_string(
                    details_chunk,
                    "text",
                )

            if text is None:
                text = ""

            # --------------------------------------------------------
            # Extract timestamp.
            # --------------------------------------------------------

            created_on = None

            created_match = re.search(
                r'created_at_ms[\\"\s:]*(\d+)',
                details_chunk,
            )

            if created_match:
                timestamp_ms = int(
                    created_match.group(1)
                )

                created_on = datetime.fromtimestamp(
                    timestamp_ms / 1000,
                    tz=timezone.utc,
                )

            # --------------------------------------------------------
            # A reply to anyone (even to self) shows up as
            # in_reply_to_* fields inside the tweet payload.
            # --------------------------------------------------------

            is_reply = bool(
                re.search(
                    r'in_reply_to_status_id[\\"\s:]*\d{18,20}',
                    details_chunk,
                )
                or re.search(
                    r'in_reply_to_status_id_str[\\"\s:]*"(\d{18,20})"',
                    details_chunk,
                )
            )

            # --------------------------------------------------------
            # Create an object compatible with the rest of your bot.
            # --------------------------------------------------------

            author = SimpleNamespace(
                username=username,
            )

            tweet = SimpleNamespace(
                id=tweet_id,
                text=text,
                full_text=text,
                created_on=created_on,
                created_at=created_on,

                author=author,

                is_reply=is_reply,
                in_reply_to_status_id=None,

                url=(
                    f"https://x.com/"
                    f"{username}/status/{tweet_id}"
                ),
            )

            results.append(tweet)

            logger.info(
                "X TWEET: %s | %s | reply=%s | %s",
                tweet_id,
                created_on,
                is_reply,
                text[:120].replace("\n", " "),
            )

        return results

    async def get_user_tweets(self, username, limit=5):
        """
        Fetch the newest tweets shown on an X profile.

        This intentionally does NOT use Tweety's get_tweets().
        """

        try:
            return await asyncio.to_thread(
                self._fetch_profile_tweets_sync,
                username,
                limit,
            )

        except Exception as e:
            logger.exception(
                "Error fetching @%s: %s",
                username,
                e,
            )
            return []
