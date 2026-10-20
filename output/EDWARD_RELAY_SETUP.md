# Edward alerts through Do Not Disturb: setup (Oct 19, 2026)

**Goal:** only VIP #🚨|alerts and free #🚨|trade-ideas ring through Do Not Disturb. Nothing else from Discord does.

## Best way: iPhone only (no computer needed)
iOS 27's Shortcuts app can run an automation **when a notification arrives** from a chosen app, filtered by its text. The phone itself watches for Edward's Discord alerts. Each one fires a **Pushover Critical Alert**, which rings through Do Not Disturb and silent mode. It works with your Mac off.

**1. Quit Discord on your work Mac (and close any Discord browser tabs)**
- While you're active on a computer, Discord doesn't send alerts to your phone. That's the main reason you've been missing them.
- Read Discord on your phone instead.

**2. Discord on your phone**
- Free server → **#trade-ideas: unmute it** (the bell with a slash in your screenshot) and set it to All Messages.
- VIP #alerts: All Messages (already set). Everything else stays muted.

**3. Pushover (the alarm app)**
- Install **Pushover** and sign up in the app (free for 30 days, then $4.99 once).
- Pushover app → Settings → **Critical Alerts: on** → Allow.
- On pushover.net: copy **Your User Key**. Then **Create an Application/API Token** (name it "Edward") and copy the token.

**4. The automation (Shortcuts app → Automation → +)**
- **Trigger:** Notification → App: **Discord** → Add Filter: **Title contains `EdwardAlerts`** (this matches both servers).
- Set it to **Run Immediately**, and turn **Notify When Run** off.
- **One action: Get Contents of URL**
  - URL: `https://api.pushover.net/1/messages.json`
  - Method: **POST**; Request Body: **Form**
  - `token` = your app token
  - `user` = your user key
  - `title` = *Notification → Title*
  - `message` = *Notification → Body*
  - `priority` = `2`
  - `retry` = `60`
  - `expire` = `300`
- Priority 2 repeats every 60 s until you tap it, for up to 5 minutes. Use `1` to ring once.

**5. Test it**
- Copy the action into a normal shortcut with a typed test message. Turn on Do Not Disturb and run it: it must ring.
- Then check the real thing on Edward's next post. If nothing fires, open one of his notifications in Notification Center. If "EdwardAlerts" isn't in the bold top line, change the filter from **Title** to **Subtitle**.
- **Unconfirmed:** this trigger is new in iOS 27, and it isn't documented whether it fires while Do Not Disturb is silencing Discord. That's what the real-post test checks.
- Keep Discord **off** Do Not Disturb's allowed apps.
- **Free alternative to Pushover:** use a **Show Notification** action and add the Shortcuts app to Do Not Disturb's allowed apps. It won't ring when the phone is on silent.

## Order details + paper copy (cloud server, works with the Mac off)
**Live since Oct 19, 11:40 PM ET.** The service is `edward-relay` on your DigitalOcean server, always on and restarting itself.
1. **Add two more actions** to the same automation, after the Pushover action. They're on your **private Shortcut card** (sent separately; it holds your inbox name and key, so don't share it):
   - a **Text** action: a key line plus the notification's title, subtitle and body;
   - a second **Get Contents of URL** that posts that text to your private inbox.
2. **Send your Pushover keys to the server once:** on the Mac, run
   `PYTHONPATH=src:. .venv/bin/python -m research.edward_live_v1.relay setup` (paste the two keys; they stay hidden), then
   `.venv/bin/python cloud/edward_relay_v1/deploy.py --keys-only`. Or just tell me and I'll open both for you.

**What each alert does after that:**
- Your phone rings with Edward's post, straight from the Shortcut. This doesn't depend on the server.
- **Within a few seconds**, a quiet **📋** note arrives in Pushover:
  > 📋 VIP: QQQ 720 PUT 10/19 @ 0.73
  > Buy 4 if you can get ≤ $0.75, else 3 up to $0.87.
  > Then sell GTC at your fill × 1.5.
  > Paper copy: bought 3 QQQ 720P 10/19 at 0.78 (his 0.73); sell order at 1.17.
  > [Open QQQ in Robinhood]
- **Paper rules:** copied only while the market is open and the alert is under 10 minutes old; skipped if the ask is above his price + 20%.
- **Exits:** when he posts a full exit ("stopped out", "sell all"), the paper copy is sold. Trims are logged, not followed. Expiring copies are sold at 3:45 PM ET.
- **4:05 PM ET weekdays:** a quiet summary of today's paper copies and this week's P&L. It also tells you the server is alive.
- **If the server loses its inbox for 10+ minutes,** you get one warning. Your phone's own alert keeps working.
- **Tested Oct 19:** a fake alert went Mac → inbox → server in under 4 seconds and was read correctly (paper copy skipped: market closed).

## Placing the trades
- **I won't place or automate real-money orders, including through Robinhood's AI ("agentic") account.** That holds even with your OK.
- Robinhood's agentic account is a separate account that an AI agent can trade, options included, with optional tap-to-approve. Connecting one is your own decision and setup.
- **What I can do:** make your own tap fast. Each alert can carry the exact order: contracts, max price (his + 20%), the +50% sell, and a link that opens Robinhood. Plus an instant **paper** copy in …U036 to measure whether instant copying makes money.
- **The record so far:** across his 26 VIP alerts (Sept 9–Oct 9), every rule you could follow live lost money: −$981 to −$1,919 at $300 per alert. Followers paid about 15% over his posted price, and speed only fixes that part.

## Older option: the Mac relay (built, not running)
- `research/edward_live_v1/relay.py` reads the Mac's notification list, sends the alert with your ticket, and places the paper copy.
- It only works while the Mac is awake with Discord open. That conflicts with step 1, so the iPhone way replaces it.
- The cloud server reuses its parser, order math and paper copier. **Don't run both**, or each alert gets two paper copies.

Files: code `research/edward_live_v1/` (cloud: `cloud.py`); deploy `cloud/edward_relay_v1/deploy.py`; logs `outputs/edward_live/` and on the server `/opt/edward-relay/outputs/edward_live/` (both gitignored); keys `.env.edward` (gitignored, owner-only). Server status: `ssh` in, then `runuser -u edward-relay -- env PYTHONPATH=/opt/edward-relay python3 -m research.edward_live_v1.cloud status` (run from `/tmp`).
