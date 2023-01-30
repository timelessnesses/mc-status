POETRY_PYTHON_PATH = $(shell poetry env info --path) # wow copilot ur amazing
POETRY_PYTHON_PATH := $(subst  ,,$(POETRY_PYTHON_PATH)) # remove spaces
ifeq ($(OS),Windows_NT)
	# Windows
	PYTHON = $(addsuffix \Scripts\python.exe,$(POETRY_PYTHON_PATH))
else
	# Linux
	PYTHON = $(addsuffix /bin/python,$(POETRY_PYTHON_PATH))
endif

run:
	$(PYTHON) main.py
install_deps:
	pip install poetry
	poetry install
update:
	poetry update
beauty: # this is mostly used in CI so just use global python
	python -m isort .
	python -m black .
	python -m flake8 .  --exit-zero
	python -m autoflake --remove-all-unused-imports --remove-unused-variables --in-place -r .
install-beautifier:
	pip install isort black flake8 autoflake
