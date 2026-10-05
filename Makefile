.PHONY: check test lint ci-docker assess report
PYTHON ?= python
SOFTVERSE_ROOT ?= ../softverse
PYTHON_IMAGE ?= python:3.14-slim

check: lint test
lint:
	$(PYTHON) -m black --check src tests
	$(PYTHON) -m isort --check-only src tests
	$(PYTHON) -m flake8 src tests
test:
	$(PYTHON) -m pytest
ci-docker:
	docker run --rm -v "$(CURDIR):/work:ro" -v "$(abspath $(SOFTVERSE_ROOT)):/softverse:ro" -e SOFTVERSE_ROOT=/softverse -w /work $(PYTHON_IMAGE) sh -c 'pip install --upgrade pip && pip install . --group dev && python -m black --check src tests && python -m isort --check-only src tests && python -m flake8 src tests && python -m pytest -p no:cacheprovider'
assess:
	not-to-code assess --softverse-root ../softverse --output build/assessment
report:
	not-to-code report --input build/assessment
