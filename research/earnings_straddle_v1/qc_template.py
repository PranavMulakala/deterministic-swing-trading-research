# Pre-declared test #7 (output/EARNINGS_STRADDLE_TEST_PLAN_20261003.md): buy an at-the-money straddle at the close
# 3 trading days before an earnings report, sell it at the last close before the report. Research only: this
# algorithm places NO orders. It reads option quotes (asks to buy, bids to sell) and computes each event's return.
# Paste this whole file into a new QuantConnect Python project as main.py, then press Backtest.
from AlgorithmImports import *
import math
import statistics

# symbol,entry_day(E),last_close_before_report(L),timing (p = pre-market, a = after close)
SCHEDULE = """__SCHEDULE__"""
SPREAD_MAX = 0.20      # skip if either leg's bid/ask gap is wider than 20% of its mid at entry
SLEEVE_SPEND = 0.02    # sleeve spends 2% of current equity on each straddle
SLEEVE_START = 100000.0


def day(text):
    return datetime(int(text[:4]), int(text[4:6]), int(text[6:8])).date()


class EarningsStraddleTest(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2012, 1, 3)
        self.set_end_date(2026, 10, 1)
        self.set_cash(SLEEVE_START)
        self.events = []
        for line in SCHEDULE.strip().splitlines():
            symbol, entry, last, timing = line.split(",")
            self.events.append({"ticker": symbol, "E": day(entry), "L": day(last), "timing": timing,
                                "status": "waiting"})
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
