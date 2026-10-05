"""Read Reddit threads (post + top comments), read-only. No PRAW install needed.

Two modes, picked automatically:
- No .env.reddit (default today): Reddit's public RSS feed per thread (post + ~50 comments, flat), one thread every
  10 s. RSS is what Reddit offers feed readers; no key, no login, no browser impersonation.
- With .env.reddit (only after Reddit approves an API request): the official OAuth API, with nested replies.

  PYTHONPATH=src:. .venv/bin/python -m research.reddit_reader_v1.fetch                 # every link in inbox/reddit_links.txt
  PYTHONPATH=src:. .venv/bin/python -m research.reddit_reader_v1.fetch <link> [<link>]  # specific links

Setup (owner, once): create a "script" app at https://www.reddit.com/prefs/apps and save its ID and secret in the
owner-only file .env.reddit (REDDIT_CLIENT_ID=..., REDDIT_CLIENT_SECRET=..., optional REDDIT_USERNAME=...).
The key is never printed. App-only ("client credentials") access: public threads only, no posting, no account data.
Output: one markdown file per thread in outputs/reddit/ (gitignored). Reddit's free tier allows 100 requests a minute;
this makes 1-2 per thread.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
KEY_FILE = ROOT / ".env.reddit"
LINKS = ROOT / "inbox/reddit_links.txt"
OUT = ROOT / "outputs/reddit"
TOP_COMMENTS = 40      # top-level comments kept, by Reddit's "top" order
REPLY_DEPTH = 2        # replies kept under each


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def keys(path=KEY_FILE):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise SystemExit("Owner-only .env.reddit required (see the setup note at the top of this file)")
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        values[name.strip()] = value.strip().strip("\"'")
    if not values.get("REDDIT_CLIENT_ID") or not values.get("REDDIT_CLIENT_SECRET"):
        raise SystemExit(".env.reddit needs REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
    return values


def user_agent(values):
    return f"macos:personal-trading-research:v0.1 (by /u/{values.get('REDDIT_USERNAME') or 'unknown'})"


def token(values):
    auth = base64.b64encode(f"{values['REDDIT_CLIENT_ID']}:{values['REDDIT_CLIENT_SECRET']}".encode()).decode()
    request = Request("https://www.reddit.com/api/v1/access_token", data=b"grant_type=client_credentials",
                      headers={"Authorization": "Basic " + auth, "User-Agent": user_agent(values)})
    with build_opener(ProxyHandler({})).open(request, timeout=30) as reply:
        return json.load(reply)["access_token"]


def thread_id(link, values=None):
    """Post id from a full link, an old/new/mobile link, a redd.it link, or a /s/ share link (resolved once)."""
    match = re.search(r"/comments/([a-z0-9]+)", link) or re.search(r"redd\.it/([a-z0-9]+)", link)
    if match:
        return match[1]
    if "/s/" in link and values is not None:  # share links redirect to the real thread
        request = Request(link, method="HEAD", headers={"User-Agent": user_agent(values)})
        try:
            build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=20)
        except Exception as error:  # a 301/302 surfaces here with the Location header
            location = getattr(error, "headers", {}).get("Location", "") if hasattr(error, "headers") else ""
            return thread_id(location) if location else None
    return None


def walk(comment, depth, lines):
    data = comment.get("data", {})
    if comment.get("kind") != "t1" or not data.get("body"):
        return
    body = data["body"].replace("\n", "\n" + "  " * depth + "  ")
    lines.append(f"{'  ' * depth}- **{data.get('author')}** ({data.get('score')} pts): {body}")
    if depth < REPLY_DEPTH and isinstance(data.get("replies"), dict):
        for child in data["replies"]["data"]["children"][:5]:
            walk(child, depth + 1, lines)


def fetch(post_id, bearer, values):
    query = urllib.parse.urlencode({"sort": "top", "limit": TOP_COMMENTS, "depth": REPLY_DEPTH + 1, "raw_json": 1})
    request = Request(f"https://oauth.reddit.com/comments/{post_id}?{query}",
                      headers={"Authorization": "bearer " + bearer, "User-Agent": user_agent(values)})
    with build_opener(ProxyHandler({})).open(request, timeout=30) as reply:
        post_listing, comment_listing = json.load(reply)
    post = post_listing["data"]["children"][0]["data"]
    lines = [f"# {post['title']}", "",
             f"r/{post['subreddit']} · u/{post.get('author')} · {post.get('score')} pts · "
             f"{post.get('num_comments')} comments · https://www.reddit.com{post['permalink']}", ""]
    if post.get("selftext"):
        lines += [post["selftext"], ""]
    elif post.get("url") and "reddit.com" not in post["url"]:
        lines += [f"Link post: {post['url']}", ""]
    lines += ["## Top comments", ""]
    for child in comment_listing["data"]["children"][:TOP_COMMENTS]:
        walk(child, 0, lines)
    return post, "\n".join(lines) + "\n"


RSS_AGENT = "personal-feed-reader/0.1 (read-only, low volume)"
RSS_PAUSE = 10  # seconds between threads; Reddit's public feeds rate-limit fast clients (HTTP 429)
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def fetch_rss(post_id):
    """Reddit's public RSS/Atom feed for a thread: the post plus about 50 comments in Reddit's default order.
    This is the feed Reddit offers to feed readers; no key needed. Comments come flat (no reply nesting)."""
    import html
    import xml.etree.ElementTree as ET
    import urllib.error
    request = Request(f"https://www.reddit.com/comments/{post_id}/.rss?limit=100", headers={"User-Agent": RSS_AGENT})
    for attempt in range(4):  # back off politely when Reddit says "too many requests"
        try:
            with build_opener(ProxyHandler({})).open(request, timeout=30) as reply:
                root = ET.fromstring(reply.read())
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            time.sleep(30 * (attempt + 1))

    def text(entry):
        content = entry.find("a:content", ATOM)
        raw = html.unescape(content.text or "") if content is not None else ""
        raw = re.sub(r"<br\s*/?>|</p>", "\n", raw)
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"<[^>]+>", "", raw)).strip()

    entries = root.findall("a:entry", ATOM)
    if not entries:
        raise ValueError("empty feed")
    post, comments = entries[0], entries[1:]
    author = lambda e: (e.findtext("a:author/a:name", "?", ATOM) or "?").replace("/u/", "")
    link = post.find("a:link", ATOM).get("href", "")
    match = re.search(r"/r/([^/]+)/", link)
    subreddit = f"r/{match[1]}" if match else ""
    lines = [f"# {post.findtext('a:title', '', ATOM)}", "", f"{subreddit} · u/{author(post)} · {link}", "",
             text(post), "", f"## Comments ({len(comments)}, Reddit's default order, replies not nested)", ""]
    lines += [f"- **{author(c)}**: {text(c)}".replace("\n", "\n  ") for c in comments]
    return {"subreddit": subreddit, "title": post.findtext("a:title", "", ATOM)}, "\n".join(lines) + "\n"


FEED_FILE = ROOT / ".env.reddit_feed"


def feed_links(url):
    """Thread links from any Reddit RSS listing (your private Saved feed, or a subreddit's hot/top/new feed)."""
    import urllib.error
    import xml.etree.ElementTree as ET
    request = Request(url, headers={"User-Agent": RSS_AGENT})
    for attempt in range(4):
        try:
            with build_opener(ProxyHandler({})).open(request, timeout=30) as reply:
                root = ET.fromstring(reply.read())
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            time.sleep(30 * (attempt + 1))
    links = []
    for entry in root.findall("a:entry", ATOM):
        link = entry.find("a:link", ATOM)
        href = link.get("href", "") if link is not None else ""
        if "/comments/" in href and href not in links:  # saved comments point inside a thread; keep the thread
            links.append(href)
    return links


def saved_feed_url(path=FEED_FILE):
    """The owner's private Saved-posts RSS link (contains a private feed key; never printed)."""
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise SystemExit("Owner-only .env.reddit_feed required (see the save command Claude gave you)")
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        if name.strip() == "REDDIT_SAVED_FEED" and re.match(r"https://(www\.|old\.)?reddit\.com/", value.strip()):
            return value.strip()
    raise SystemExit(".env.reddit_feed needs REDDIT_SAVED_FEED=https://www.reddit.com/saved.rss?...")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Read Reddit threads read-only (RSS by default).")
    parser.add_argument("links", nargs="*", help="thread links; default: inbox/reddit_links.txt")
    parser.add_argument("--saved", type=int, metavar="N", help="read my newest N saved posts (private feed)")
    parser.add_argument("--sub", metavar="NAME", help="read top posts of a community, e.g. --sub stocks")
    parser.add_argument("--sort", default="top", choices=["top", "hot", "new"])
    parser.add_argument("--t", default="week", choices=["day", "week", "month", "year", "all"])
    parser.add_argument("--n", type=int, default=10, help="how many posts for --sub (default 10)")
    args = parser.parse_args()
    if args.saved:
        url = saved_feed_url()
        links = feed_links(url + ("&" if "?" in url else "?") + "limit=100")[:args.saved]
    elif args.sub:
        name = re.sub(r"[^A-Za-z0-9_]", "", args.sub.removeprefix("r/"))
        links = feed_links(f"https://www.reddit.com/r/{name}/{args.sort}/.rss?t={args.t}&limit={args.n}")[:args.n]
    else:
        links = args.links or [l.strip() for l in LINKS.read_text().splitlines() if l.strip() and not l.startswith("#")]
    print(f"{len(links)} thread(s) to read")
    use_api = KEY_FILE.exists()
    values = keys() if use_api else {}
    bearer = token(values) if use_api else None
    OUT.mkdir(parents=True, exist_ok=True)
    for n, link in enumerate(links):
        post_id = thread_id(link, values if use_api else {"REDDIT_USERNAME": ""})
        if not post_id:
            print("SKIP (no thread id):", link)
            continue
        if not use_api:
            time.sleep(RSS_PAUSE)
        try:
            post, text = fetch(post_id, bearer, values) if use_api else fetch_rss(post_id)
        except Exception as error:
            print(f"FAIL {post_id}: {type(error).__name__} {error}")
            continue
        path = OUT / f"{post_id}.md"
        path.write_text(text, encoding="utf-8")
        print(f"OK {post_id} ({'api' if use_api else 'rss'}): {post['subreddit']} | {post['title'][:80]} -> {path.relative_to(ROOT)}")
        if use_api:
            time.sleep(1)


if __name__ == "__main__":
    main()
