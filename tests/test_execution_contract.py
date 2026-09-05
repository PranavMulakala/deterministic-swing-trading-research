import unittest

from swingbot.execution_contract import ExecutionDisabled, submit_paper_order


class ExecutionContractTests(unittest.TestCase):
    def test_broker_execution_is_unconditionally_disabled(self) -> None:
        with self.assertRaises(ExecutionDisabled):
            submit_paper_order()


if __name__ == "__main__":
    unittest.main()
