PYTHON ?= python3

.PHONY: test fetch-data reproduce

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

fetch-data:
	PYTHONPATH=src $(PYTHON) -m swingbot.cli fetch-data --root .

reproduce: test
	PYTHONPATH=src $(PYTHON) -m swingbot.cli reproduce --root .
