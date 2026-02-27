PYTHON ?= python3

.PHONY: lint-html lint-html-fix
lint-html:
	$(PYTHON) scripts/check_readme_html.py README.md

lint-html-fix:
	$(PYTHON) scripts/check_readme_html.py --fix README.md
