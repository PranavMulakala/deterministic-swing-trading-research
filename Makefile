PYTHON ?= python3

.PHONY: test fetch-data reproduce paper-constraint paper-autopilot

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

fetch-data:
	PYTHONPATH=src $(PYTHON) -m swingbot.cli fetch-data --root .

reproduce: test
	PYTHONPATH=src $(PYTHON) -m swingbot.cli reproduce --root .

paper-constraint:
	PYTHONPATH=src $(PYTHON) -m swingbot.cli analyze-paper-constraint --root .

paper-autopilot:
	./scripts/run_paper_autopilot.sh
