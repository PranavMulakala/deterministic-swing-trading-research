import unittest

from swingbot.indicators import sma, wilder_atr, wilder_rsi


class IndicatorTests(unittest.TestCase):
    def test_sma_alignment(self) -> None:
        self.assertEqual(sma([1, 2, 3, 4], 3), [None, None, 2.0, 3.0])

    def test_rsi_and_atr_are_deterministic(self) -> None:
        closes = [10, 9, 8, 9, 10, 9]
        first = wilder_rsi(closes, 2)
        self.assertEqual(first, wilder_rsi(closes, 2))
        self.assertEqual(len(first), len(closes))
        atr = wilder_atr([11, 10, 9, 10, 11, 10], [9, 8, 7, 8, 9, 8], closes, 2)
        self.assertEqual(len(atr), len(closes))
        self.assertTrue(all(value is None or value >= 0 for value in atr))


if __name__ == "__main__":
    unittest.main()
