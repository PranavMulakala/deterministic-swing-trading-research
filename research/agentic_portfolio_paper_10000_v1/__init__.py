"""Separate $10,000-per-account paper trial profile."""

from typing import Final, Literal


VERSION: Final[str] = "1.0.0"
MODE: Final[str] = "PAPER_ONLY_NO_ORDER"
ORDERS_ENABLED: Final[Literal[False]] = False
MODEL_CALLS_ENABLED: Final[Literal[False]] = False
NETWORK_ENABLED: Final[Literal[False]] = False
BROKER_ENABLED: Final[Literal[False]] = False
DEPLOY_ENABLED: Final[Literal[False]] = False

