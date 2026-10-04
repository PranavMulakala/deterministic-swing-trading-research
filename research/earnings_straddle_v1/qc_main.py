# Pre-declared test #7 (output/EARNINGS_STRADDLE_TEST_PLAN_20261003.md): buy an at-the-money straddle at the close
# 3 trading days before an earnings report, sell it at the last close before the report. Research only: this
# algorithm places NO orders. It reads option quotes (asks to buy, bids to sell) and computes each event's return.
# Paste this whole file into a new QuantConnect Python project as main.py, then press Backtest.
from AlgorithmImports import *
import math
import statistics

# Events packed to fit QuantConnect's 32,000-character file limit (built by build_qc.py from schedule.json).
# Per stock: 5-character tokens = L as base-36 days after 2012-01-01 (3 chars), calendar days from E to L (1 digit),
# timing (p = pre-market report, a = after the close). L = last close before the report; E = entry day.
SCHEDULE = {
    "AAPL": "00n5a 0365a 05p5a 08a3a 0as6a 0da5a 0ft5a 0ii5a 0l15a 0nf6a 0px5a 0sf5a 0v65a 0xo5a 1015a 12r5a 15a5a 17t5a 1ac5a 1cv5a 1fl5a 1i45a 1kn5a 1n83a 1pr3a 1s85a 1ur5a 1xc3a 1zt5a 22c5a 24v5a 27f5a 29x5a 2ci3a 2f13a 2hk3a 2k25a 2ml5a 2p35a 2ro3a 2u73a 2wq3a 2z93a 31s3a 34i3a 3713a 39k3a 3c33a 3em3a 3h53a 3jo3a 3m73a 3oq3a 3r93a 3ts3a 3wb3a 3yu3a 41d3a 43w3a",
    "ADBE": "0265a 04q5a 07a5a 09n3a 0cb5a 0eu5a 0hd5a 0jr3a 0mf5a 0oy5a 0rh5a 0tv3a 0wj5a 0z25a 11n3a 13z3a 16p3a 19d5a 1bw5a 1ea3a 1gt3a 1jh5a 1m05a 1oe3a 1qx3a 1tg3a 1vz3a 1yi3a 2113a 23p5a 2685a 28m3a 2b53a 2do3a 2gc5a 2ip5p 2ll5a 2nz3a 2qn5a 2t05p 2vp5a 2y33a 30l5p 3353a 35n5a 3873a 3aq3a 3d85a 3fs3a 3ib3a 3ku3a 3nc5a 3pv5a 3sf3a 3uy3a 3xg5a 4003a 42j3a 4526a",
    "AMD": "00n5a 0313a 05k3a 0833a 0ar6a 0d53a 0fo3a 0i73a 0kv6a 0n93a 0ps3a 0sb3a 0uz6a 0xd3a 0zw3a 12f3a 1536a 17o3a 1a73a 1cq3a 1fl5a 1i35a 1kg5a 1mz5a 1pp5a 1s25a 1ul5a 1x45a 1zt5a 22c5a 24v5a 27e5a 29x5a 2cg5a 2ez5a 2hh5p 2k15a 2mk5a 2p35a 2rm5a 2uc5a 2wv5a 2ze5a 31x5a 34g5a 36z5a 39i5a 3c15a 3ek5a 3h35a 3jm5a 3m55a 3ov5a 3re5a 3tx5a 3wg5a 3yz5a 41i5a 4415a",
    "AMZN": "00u5a 0383a 05r3a 08a3a 0ay5a 0dc3a 0fv3a 0ie3a 0l43a 0ng3a 0pz3a 0si3a 0v83a 0xk3a 1033a 12m3a 15c3a 17v3a 1ae3a 1cx3a 1fn3a 1hz3a 1ki3a 1n13a 1pr3a 1s33a 1um3a 1x53a 1zv3a 2273a 24q3a 2793a 29z3a 2ci3a 2f13a 2hk3a 2k85a 2mm3a 2p53a 2ro3a 2ue3a 2wq3a 2z93a 31s3a 34i3a 36u3a 39k3a 3bw3a 3em3a 3h35a 3jo3a 3m73a 3ow5p 3r93a 3ts3a 3wb3a 3z13a 41c5a 43w3a",
    "AVGO": "01f6p 03x5p 06b5p 0985p 0bp5p 0e96p 0gr5p 0ji6p 0lt5p 0oe6p 0qy3a 0tn5a 0vz5a 0yi6p 1115a 13r5a 16b3a 18u6a 1bd3a 1e33a 1ge5a 1iy6a 1la3a 1o65a 1qx3a 1t93a 1vs6a 1yb6a 2113a 23k3a 2633a 28m3a 2b53a 2dh3a 2g03a 2iq3a 2l23a 2nl6a 2q43a 2su3a 2v63a 2xh5p 3083a 32y3a 35a3a 37t6a 3ac3a 3d23a 3fl3a 3ia5a 3kn6a 3nd3a 3pp3a 3s83a 3ur6a 3xh3a 3zs5a 42b5a 44u5a",
    "BAC": "00h6p 0305p 05i5p 0815p 0al5p 0d35p 0fm5p 0i55p 0ko5p 0n75p 0pq5p 0s95p 0ut5p 0xb5p 0zu5p 12d5p 14z3p 17g5p 1a13p 1ck3p 1f23p 1hp6p 1k85p 1mn3p 1pb6p 1rq3p 1u93p 1ws3p 1zf5p 21x5p 24h5p 2705p 29j5p 2c26p 2em5p 2h45p 2jq3p 2m83a 2op5p 2r95p 2ty6p 2wc3p 2yw3p 31f3p 33x3p 36k5p 3935p 3bm5p 3e13p 3go5p 3j75p 3lq5p 3ob5p 3qs5p 3tc5p 3vv5p 3ye5p 40x5p 43f5p",
    "CRM": "01h6a 03t3a 06j3a 0905a 0bs3a 0e43a 0gu3a 0j35a 0lw3a 0o65a 0qr3a 0t95a 0vz5a 0yb5a 10v3a 13d5a 1635a 18f5a 1bc5a 1di3a 1gd5a 1ik3a 1l85a 1nr5a 1qi5a 1t06a 1vk5a 1y26a 20r5a 23b5a 25i3a 28d6a 2ap5a 2da6a 2fr5a 2ih6a 2kv3a 2ne3a 2pw5a 2sl6a 2v45a 2xn6a 3005a 32q5a 3595a 37s6a 3ab5a 3cu5a 3fd5a 3hw6a 3kf5a 3n46a 3ph5a 3s06a 3uq6a 3x95a 3zl5a 4246a 44n5a",
    "CSCO": "0125a 03l5a 06b5a 08t5a 0bd5a 0dw5a 0gf5a 0iy5a 0lh5a 0o05a 0qj5a 0t25a 0vl5a 0y45a 10n5a 1373a 15p5a 18f5a 1ay5a 1dh5a 1g05a 1ij5a 1l25a 1nl5a 1q45a 1sn5a 1v65a 1xp5a 2085a 22r5a 25a5a 27t5a 2ac5a 2cv5a 2fe5a 2hy3a 2kf5a 2n65a 2pp5a 2s85a 2ur5a 2xa5a 2zt5a 32c5a 34v5a 37e5a 39x5a 3cg5a 3ez5a 3hi5a 3k15a 3mk5a 3p35a 3rm5a 3u55a 3wo5a 3z75a 41q5a 4495a",
    "GOOGL": "00h6p 02t6p 05j5p 0825p 0an3p 0d45p 0fn5p 0i65p 0l35p 0n75p 0pr5p 0sb3a 0v83a 0xk3a 0zw3a 12m3a 15g5a 17o3a 1ae3a 1cx3a 1fg3a 1hz3a 1kf5a 1n13a 1pr3a 1s05a 1uj5a 1x53a 1zz5a 22b5a 24q3a 27d5a 2a35a 2cg5a 2f13a 2hk3a 2k85a 2mk5a 2p35a 2rm5a 2uc5a 2wo5a 2z75a 31q5a 34i3a 36s5a 39b5a 3bu5a 3ek5a 3gy3a 3jf5a 3m55a 3ov5a 3r23a 3tk5a 3wa5a 3z05a 41c5a 43o5a",
    "INTC": "00i6a 02z5a 05i5a 0815a 0am3a 0d35a 0fn5a 0i55a 0kq3a 0n75a 0pq5a 0s95a 0uu3a 0xb5a 0zv5a 12d5a 14y3a 17m5a 1a65a 1co5a 1fg3a 1hz3a 1ki3a 1n13a 1pk3a 1s33a 1um3a 1x53a 1zo6a 2273a 24q3a 2793a 29s6a 2cb3a 2eu3a 2hd3a 2jw6a 2mf3a 2oy3a 2rh3a 2u65a 2wq3a 2z93a 31s3a 34b3a 36u3a 39d3a 3bw3a 3ef3a 3gy3a 3jo3a 3m73a 3oq3a 3r23a 3tl3a 3w43a 3yn6a 4163a 43p3a",
    "JPM": "00b3p 02u3p 05d3p 07w3p 0ak5p 0cy3p 0fh3p 0i03p 0kn5p 0n23p 0pp5p 0s85p 0us5p 0xa5p 0zt5p 12d5a 14x5p 17f5p 19z5p 1cj3p 1f23p 1hk5p 1k43p 1mm5p 1p63p 1rp3p 1u83p 1wr3p 20k5p 21t3p 24g5p 26z5p 29i5p 2c16p 2ek5p 2h35p 2jp3p 2m65p 2oo5p 2r85p 2tt3p 2wa5p 2yu5p 31e3p 33x3p 36g3p 38z3p 3bi3p 3e13p 3gk3p 3j33p 3lm3p 3oa6p 3qo3p 3tb5p 3vu5p 3yd5p 40w5p 43f5p",
    "META": "0456p 05r3a 0885a 0az5a 0di5a 0fu5a 0ik5a 0l35a 0nf6a 0py5a 0sn5a 0v75a 0xj5a 1095a 12z5a 15b5a 17u5a 1ad5a 1d35a 1fm5a 1i55a 1kh5a 1n75a 1pq5a 1s25a 1ul5a 1xa5a 1zu5a 2266a 24p5a 27f5a 29y5a 2ch5a 2f13a 2hk3a 2k25a 2ml5a 2p45a 2rl5a 2ud5a 2wp5a 2z85a 31r5a 34h5a 36t5a 39c5a 3bv5a 3em3a 3gx5a 3jn5a 3m65a 3op5a 3r85a 3tr5a 3wa5a 3yt5a 41c5a 43v5a",
    "MSFT": "00i6a 0313a 05k3a 0833a 0at6a 0d53a 0fo3a 0ie3a 0kx6a 0ng3a 0px5a 0si3a 0v55a 0xk3a 1015a 12m3a 15c3a 17o3a 1a55a 1cq3a 1fg3a 1hz3a 1kb3a 1n13a 1pq5a 1s33a 1uf3a 1x45a 1zu5a 2266a 24j3a 2785a 29y5a 2ch5a 2et5a 2hi5a 2k15a 2mk5a 2p25p 2rm5a 2u55a 2wo5a 2z65p 31q5a 3495a 36s5a 39a5p 3bu5a 3ek5a 3gy3a 3jm5a 3m65a 3op5a 3r85a 3tr5a 3wa5a 3yt5a 41c5a 43v5a",
    "MU": "0293a 04r5a 07i3a 09u3a 0cd3a 0ev5a 0i03a 0kh5a 0mv3a 0p45a 0sm5a 0ul6a 0wy5a 0zb3a 1213a 14b5a 1726a 19m3a 1ca5a 1eg5a 1h03a 1jq3a 1m75a 1oj5a 1r43a 1tm5a 1w63a 1yn5a 2175a 23w5a 26h3a 28s5a 2bi5a 2e65a 2gq5a 2ji3a 2lt5a 2oc5a 2qu5a 2t55a 2vw5a 2yh3a 3103a 33b5a 3605a 38k5a 3b35a 3df5a 3fy5a 3io5a 3l75a 3nj5a 3q33a 3ss5a 3va5a 3xn5a 4065a 42w6a 45m5a",
    "NFLX": "00o5a 0355a 05p5a 0885a 0as6a 0d95a 0fs5a 0ib5a 0kw6a 0nd6a 0pw5a 0sa5a 0uz6a 0xc5a 0zv5a 12e5a 1536a 17l5a 1a45a 1cn5a 1f86a 1hp6a 1k85a 1mr5a 1ph5a 1rt5a 1uc5a 1ww5a 1zh3a 21y5a 24i5a 2715a 29q6a 2c95a 2en3a 2hb5a 2ju6a 2md5a 2ow5a 2rf5a 2u06a 2wh6a 2z05a 31j5a 3446a 36l5a 3955a 3bo5a 3ed5a 3gr3a 3ja3a 3lt3a 3oh6a 3qv3a 3te3a 3w25a 3yl6a 40z3a 43i3a",
    "NVDA": "0185p 03m3p 0645p 08n5p 0bc5p 0dp5p 0g85p 0ir5p 0lg5p 0nr5p 0qc5p 0sw3a 0vl5a 0xy3a 10h3a 1303a 15w6a 1893a 1as3a 1db3a 1fu3a 1ib5a 1kw3a 1nf3a 1py3a 1sh3a 1v73a 1xq3a 2093a 22s3a 25b3a 27u3a 2ad3a 2d33a 2fl5a 2i45a 2ku5a 2nd5a 2pp5a 2s85a 2ur5a 2xh5a 3005a 32c5a 3526a 37l5a 3a45a 3cm5a 3f66a 3hp5a 3kf5a 3mr5a 3ph5a 3s06a 3uj5a 3wv5a 3zl5a 41x5a 44n5a",
    "ORCL": "0275a 04p5a 07b3a 09s5a 0cc5a 0ew3a 0he5a 0jx5a 0mf5a 0p03a 0rj3a 0u15a 0wj5a 0z35a 11m5a 1455a 16n5a 1983a 1br3a 1ea3a 1gs5a 1ji5a 1lv3a 1oe3a 1r15a 1tl5a 1w35a 1ym5a 2113a 23q5a 2625a 28m3a 2b53a 2dt5a 2g76a 2iq3a 2l85a 2nx5a 2qf5a 2su3a 2vd3a 2y05a 30j5a 3325a 35h3a 3845a 3an5a 3d65a 3fp5a 3i95a 3kr5a 3na5a 3pt5a 3se5a 3uw5a 3xg5a 3zy5a 42i5a 4526a",
    "QCOM": "00v5a 0305a 05j5a 08n5a 0az5a 0db5a 0fu5a 0ir5a 0l35a 0nf6a 0py5a 0sv5a 0v75a 0xj5a 1025a 12z5a 15b5a 17n5a 1a65a 1d35a 1ff5a 1hr6a 1ka5a 1n75a 1pq5a 1s25a 1ul5a 1xi5a 1zu5a 22d5a 24w5a 27m5a 2a55a 2ch5a 2f05a 2hq5a 2k95a 2mk5p 2p45a 2ru5a 2ud5a 2wp5a 2z85a 31y5a 34i3a 3705a 39j5a 3c25a 3el5a 3h45a 3jn5a 3md5a 3ow5a 3r85a 3tr5a 3wh5a 3z05a 41c5a 43v5a",
    "TSLA": "0195a 03l5a 05q5a 08i7p 0bk6a 0dp5a 0g85a 0iq5a 0lo6a 0nt5a 0q63a 0sv5a 0vl5a 0xx5a 10g5a 12y5a 15p5a 1815a 1ak5a 1cw5a 1g76a 1i55a 1ko5a 1n75a 1px5a 1s95a 1us5a 1x45a 1zu5a 2266a 24p5a 2785a 29y5a 2ch5a 2et5a 2hc5a 2k25a 2mj5a 2p25a 2rg5a 2u65a 2wi6a 2z15a 31k5a 34a5a 36m5a 3955a 3bo5a 3ee5a 3gw5a 3jf5a 3lz5a 3op5a 3r06a 3tk5a 3w35a 3yt5a 4155a 43o5a",
    "XOM": "00u5a 0375p 05q5p 08g7p 0b03p 0db5p 0g15p 0ik5p 0l35p 0nm5p 0q55p 0sp3p 0v93p 0xq5p 10a3p 12t3p 15g5p 17v3p 1ae3p 1cx3p 1fk5p 1hz3p 1ki3p 1n13p 1pr3p 1s33p 1um3p 1xc3p 1zv3p 2273p 24x3p 27g3p 29z3p 2ci3p 2f13p 2hk3p 2k75p 2mm3p 2p53p 2ro3p 2ub5p 2wq3p 2z93p 31s3p 34f5p 36u3p 39d3p 3bw3p 3em3p 3gz3a 3jo3p 3m73p 3oq3p 3r93p 3ts3p 3wb3p 3yu3p 41d3p 43w3p",
}
SPREAD_MAX = 0.20      # skip if either leg's bid/ask gap is wider than 20% of its mid at entry
SLEEVE_SPEND = 0.02    # sleeve spends 2% of current equity on each straddle
SLEEVE_START = 100000.0


def unpack(packed):
    base = datetime(2012, 1, 1).date()
    for ticker, tokens in packed.items():
        for token in tokens.split():
            last = base + timedelta(days=int(token[:3], 36))
            yield ticker, last - timedelta(days=int(token[3])), last, token[4]


class EarningsStraddleTest(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2012, 1, 3)
        self.set_end_date(2026, 10, 1)
        self.set_cash(SLEEVE_START)
        self.events = []
        for symbol, entry, last, timing in unpack(SCHEDULE):
            self.events.append({"ticker": symbol, "E": entry, "L": last, "timing": timing, "status": "waiting"})
        self.stocks = {}
        for ticker in sorted({e["ticker"] for e in self.events}):
            equity = self.add_equity(ticker, Resolution.HOUR, data_normalization_mode=DataNormalizationMode.RAW)
            self.stocks[ticker] = equity.symbol
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        self.spy_closes = []
        self.schedule.on(self.date_rules.every_day(self.spy), self.time_rules.at(10, 5), self.pick_contracts)

    def pick_contracts(self):
        today = self.time.date()
        for e in self.events:
            if e["status"] != "waiting" or e["E"] != today:
                continue
            stock = self.stocks[e["ticker"]]
            price = self.securities[stock].price
            if price <= 0:
                e["status"] = "skip_no_stock_price"
                continue
            contracts = [c for c in self.option_chain_provider.get_option_contract_list(stock, self.time)
                         if c.id.date.date() > e["L"]]
            if not contracts:
                e["status"] = "skip_no_contracts"
                continue
            expiry = min(c.id.date for c in contracts)
            same = [c for c in contracts if c.id.date == expiry]
            strikes = sorted({c.id.strike_price for c in same})
            strike = min(strikes, key=lambda k: (abs(float(k) - float(price)), float(k)))
            call = next((c for c in same if c.id.strike_price == strike and c.id.option_right == OptionRight.CALL), None)
            put = next((c for c in same if c.id.strike_price == strike and c.id.option_right == OptionRight.PUT), None)
            if call is None or put is None:
                e["status"] = "skip_missing_leg"
                continue
            e["call"] = self.add_option_contract(call, Resolution.HOUR).symbol
            e["put"] = self.add_option_contract(put, Resolution.HOUR).symbol
            e.update({"strike": float(strike), "expiry": expiry.date(), "status": "picked"})

    def quotes(self, e):
        legs = [self.securities[e["call"]], self.securities[e["put"]]]
        return [(float(s.bid_price), float(s.ask_price)) for s in legs]

    def on_data(self, data):
        if self.spy in data.bars:
            self.spy_closes.append((self.time.date(), float(data.bars[self.spy].close)))
        if self.time.hour != 16:
            return
        today = self.time.date()
        for e in self.events:
            if e["status"] == "picked" and e["E"] == today:
                q = self.quotes(e)
                if any(b <= 0 or a <= 0 or a < b for b, a in q):
                    e["status"] = "skip_no_entry_quote"
                elif any((a - b) / ((a + b) / 2) > SPREAD_MAX for b, a in q):
                    e["status"] = "skip_wide_spread"
                else:
                    e["entry_ask"] = sum(a for _, a in q)
                    e["entry_mid"] = sum((a + b) / 2 for b, a in q)
                    e["status"] = "open"
                if e["status"] != "open":
                    self.drop(e)
            elif e["status"] == "open" and e["L"] == today:
                q = self.quotes(e)
                if any(b <= 0 or a <= 0 for b, a in q):
                    e["status"] = "skip_no_exit_quote"
                else:
                    e["ret"] = sum(b for b, _ in q) / e["entry_ask"] - 1
                    e["ret_mid"] = sum((a + b) / 2 for b, a in q) / e["entry_mid"] - 1
                    e["status"] = "done"
                self.drop(e)

    def drop(self, e):
        for leg in ("call", "put"):
            if leg in e:
                self.remove_option_contract(e[leg])

    def on_end_of_algorithm(self):
        done = [e for e in self.events if e["status"] == "done"]
        counts = {}
        for e in self.events:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
        self.log("STATUS " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        if len(done) < 2:
            self.log("RESULT not enough valid events")
            return
        rets = [e["ret"] for e in done]
        mean, sd = statistics.mean(rets), statistics.stdev(rets)
        t_stat = mean / (sd / math.sqrt(len(rets)))
        first = [e["ret"] for e in done if e["E"].year <= 2018]
        second = [e["ret"] for e in done if e["E"].year >= 2019]
        trimmed = sorted(rets)[:len(rets) - max(1, len(rets) // 20)]
        sleeve_cagr, sleeve_dd = self.sleeve(done)
        spy_cagr, spy_dd = self.spy_stats()
        checks = {
            "1_events_300_plus": len(done) >= 300,
            "2_mean_positive_t2": mean > 0 and t_stat >= 2.0,
            "3_both_halves_positive": bool(first) and bool(second) and statistics.mean(first) > 0
                                      and statistics.mean(second) > 0,
            "4_positive_without_best_5pct": statistics.mean(trimmed) > 0,
            "5_bar_b_vs_spy": (spy_dd - sleeve_dd >= 0.05) and (sleeve_dd > 0 and spy_dd > 0
                              and sleeve_cagr / sleeve_dd > spy_cagr / spy_dd),
        }
        self.log(f"RESULT events={len(done)} mean_bidask={mean:.4f} t={t_stat:.2f} median={statistics.median(rets):.4f} "
                 f"win_rate={sum(r > 0 for r in rets) / len(rets):.3f} mean_mid={statistics.mean(e['ret_mid'] for e in done):.4f}")
        self.log(f"RESULT halves 2012-18 mean={statistics.mean(first) if first else float('nan'):.4f} n={len(first)} | "
                 f"2019-26 mean={statistics.mean(second) if second else float('nan'):.4f} n={len(second)} | "
                 f"trimmed mean={statistics.mean(trimmed):.4f}")
        self.log(f"RESULT sleeve CAGR={sleeve_cagr:.4f} maxDD={sleeve_dd:.4f} | SPY CAGR={spy_cagr:.4f} maxDD={spy_dd:.4f}")
        for timing in ("p", "a"):
            sub = [e["ret"] for e in done if e["timing"] == timing]
            if sub:
                self.log(f"INFO timing={timing} n={len(sub)} mean={statistics.mean(sub):.4f}")
        for ticker in sorted({e["ticker"] for e in done}):
            sub = [e["ret"] for e in done if e["ticker"] == ticker]
            self.log(f"INFO {ticker} n={len(sub)} mean={statistics.mean(sub):.4f}")
        self.log("CHECKS " + ", ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in checks.items()))
        self.log("VERDICT " + ("PASS (all five)" if all(checks.values()) else "FAIL"))
        self.set_summary_statistic("Test7 verdict", "PASS" if all(checks.values()) else "FAIL")
        self.set_summary_statistic("Test7 events", str(len(done)))
        self.set_summary_statistic("Test7 mean bid/ask return", f"{mean:.4f}")
        self.set_summary_statistic("Test7 t-stat", f"{t_stat:.2f}")
        rows = [f"{e['ticker']},{e['E']},{e['L']},{e['timing']},{e['strike']},{e['expiry']},{e['ret']:.4f},{e['ret_mid']:.4f}"
                for e in done]
        try:
            self.object_store.save("test7_events.csv", "ticker,E,L,timing,strike,expiry,ret_bidask,ret_mid\n" + "\n".join(rows))
            self.log("SAVED test7_events.csv to the Object Store")
        except Exception as error:
            self.log(f"Object Store save failed: {error}")
        for row in rows:  # last, so a log cap can only cut these
            self.log("EV," + row)

    def sleeve(self, done):
        """Spend 2% of equity (marked at cost) on each straddle at entry; add the bid proceeds at exit."""
        cash, open_cost, curve = SLEEVE_START, {}, []
        timeline = sorted([(e["E"], 0, i) for i, e in enumerate(done)] + [(e["L"], 1, i) for i, e in enumerate(done)])
        for when, kind, i in timeline:
            if kind == 0:
                spend = SLEEVE_SPEND * (cash + sum(open_cost.values()))
                cash -= spend
                open_cost[i] = spend
            else:
                cash += open_cost.pop(i) * (1 + done[i]["ret"])
            curve.append(cash + sum(open_cost.values()))
        peak, worst = SLEEVE_START, 0.0
        for value in curve:
            peak = max(peak, value)
            worst = max(worst, 1 - value / peak)
        years = (done[-1]["L"] - done[0]["E"]).days / 365.25
        return (curve[-1] / SLEEVE_START) ** (1 / years) - 1, worst

    def spy_stats(self):
        closes = self.spy_closes
        peak, worst = closes[0][1], 0.0
        for _, value in closes:
            peak = max(peak, value)
            worst = max(worst, 1 - value / peak)
        years = (closes[-1][0] - closes[0][0]).days / 365.25
        return (closes[-1][1] / closes[0][1]) ** (1 / years) - 1, worst
