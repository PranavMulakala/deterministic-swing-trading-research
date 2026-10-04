"""Read Reddit threads (post + top comments) through the official Reddit API, read-only. No PRAW install needed.

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


def main():
    values = keys()
    links = sys.argv[1:] or [l.strip() for l in LINKS.read_text().splitlines() if l.strip() and not l.startswith("#")]
    bearer = token(values)
    OUT.mkdir(parents=True, exist_ok=True)
    for link in links:
        post_id = thread_id(link, values)
        if not post_id:
            print("SKIP (no thread id):", link)
            continue
        post, text = fetch(post_id, bearer, values)
        path = OUT / f"{post_id}.md"
        path.write_text(text, encoding="utf-8")
        print(f"OK {post_id}: r/{post['subreddit']} | {post['title'][:80]} -> {path.relative_to(ROOT)}")
        time.sleep(1)


if __name__ == "__main__":
    main()
