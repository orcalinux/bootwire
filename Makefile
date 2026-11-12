# BootWire: run the tools from the source tree, test them, and build the package.
# `make` or `make help` lists every target.

DESKTOP := desktop
VENV    := $(DESKTOP)/.venv
PY      := $(VENV)/bin/python
STAMP   := $(VENV)/.installed
VERSION := $(shell sed -n 's/^version = "\(.*\)"$$/\1/p' $(DESKTOP)/pyproject.toml)
DEB     := dist/bootwire_$(VERSION)_all.deb

# Arguments for `make cli`, e.g. make cli ARGS="-p sim info"
ARGS ?= --help
# Simulated-target arguments for `make sim`, e.g. make sim ARGS="--dump flash.bin"

.DEFAULT_GOAL := help
.PHONY: help setup cli gui sim test man man-gui deb deb-info install-deb uninstall-deb screenshots diagrams clean distclean

help: ## Show this help
	@echo "BootWire $(VERSION)"
	@echo
	@echo "Usage: make <target> [ARGS=\"...\"]"
	@echo
	@awk 'BEGIN { FS = ":.*## " } /^[a-zA-Z_-]+:.*## / { printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo
	@echo "Examples:"
	@echo "  make cli ARGS=\"-p sim info\"            talk to the built-in simulator"
	@echo "  make cli ARGS=\"-p sim flash app.bin\"   erase, write, verify, run"
	@echo "  make cli ARGS=\"-p /dev/ttyACM0 info\"   talk to a board"
	@echo "  make gui                               open the desktop application"
	@echo "  make deb && make install-deb           build and install the package"

# The environment is rebuilt whenever pyproject.toml changes.
$(STAMP): $(DESKTOP)/pyproject.toml
	test -x $(PY) || python3 -m venv $(VENV)
	$(PY) -m pip install --quiet -e '$(DESKTOP)[gui,dev]'
	@touch $@

setup: $(STAMP) ## Create desktop/.venv and install BootWire with the GUI and test extras

cli: $(STAMP) ## Run the command-line tool: make cli ARGS="-p sim info"
	@$(VENV)/bin/bootwire $(ARGS)

gui: $(STAMP) ## Open the desktop application
	@$(VENV)/bin/bootwire-gui

sim: $(STAMP) ## Run the simulated target on a pseudo-terminal (prints the port to use)
	@$(PY) -m bootwire.sim $(filter-out --help,$(ARGS))

test: $(STAMP) ## Run the test suite
	cd $(DESKTOP) && .venv/bin/python -m pytest -q

man: ## Read the bootwire(1) manual page
	@man -l $(DESKTOP)/man/bootwire.1

man-gui: ## Read the bootwire-gui(1) manual page
	@man -l $(DESKTOP)/man/bootwire-gui.1

deb: ## Build the Debian package into dist/
	@sh packaging/build-deb.sh

deb-info: ## Show the control data and contents of the built package
	@test -f $(DEB) || { echo "No package yet. Run: make deb"; exit 1; }
	@dpkg-deb --info $(DEB)
	@dpkg-deb --contents $(DEB)

install-deb: ## Install the built package with apt (asks for sudo)
	@test -f $(DEB) || { echo "No package yet. Run: make deb"; exit 1; }
	sudo apt install ./$(DEB)

uninstall-deb: ## Remove the installed package (asks for sudo)
	sudo apt remove bootwire

screenshots: $(STAMP) ## Capture every workspace in both themes into .impeccable/review/
	cd $(DESKTOP) && QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python ../scripts/preview_gui.py

diagrams: ## Regenerate the protocol diagrams (needs Graphviz and PlantUML)
	sh docs/protocol/render.sh

clean: ## Remove build output, caches and the built package
	rm -rf dist $(DESKTOP)/dist $(DESKTOP)/build $(DESKTOP)/src/*.egg-info .pytest_cache $(DESKTOP)/.pytest_cache
	find $(DESKTOP) -name __pycache__ -type d -not -path '$(VENV)/*' -prune -exec rm -rf {} +

distclean: clean ## Also remove desktop/.venv
	rm -rf $(VENV)
