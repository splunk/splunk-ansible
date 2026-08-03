SHELL := /bin/bash
SHC_LINT_VENV ?= .venv-shc-lint
SHC_LINT_PYTHON_BIN ?= python3
SHC_ANSIBLE_LINT := $(SHC_LINT_VENV)/bin/ansible-lint
SHC_ANSIBLE_PLAYBOOK := $(SHC_LINT_VENV)/bin/ansible-playbook
SHC_LINT_PYTHON := $(SHC_LINT_VENV)/bin/python
SHC_LINT_FILES := \
	roles/splunk_common/tasks/configure_indexer_search_address_prestart.yml \
	roles/splunk_common/tasks/configure_shc_prestart.yml \
	roles/splunk_common/tasks/peer_cluster_master.yml \
	roles/splunk_common/tasks/start_splunk.yml \
	roles/splunk_search_head/tasks/search_head_clustering.yml

.PHONY: tests shc-check shc-lint shc-unit-test shc-lint-setup shc-lint-clean

test-setup:
	@echo 'Install test requirements'
	pip install --upgrade pip
	pip install -r $(shell pwd)/tests/requirements.txt --upgrade

py3k-test-setup:
	pip3 install --upgrade pip
	pip3 install -r $(shell pwd)/tests/requirements.txt --upgrade

$(SHC_ANSIBLE_LINT): tests/requirements-shc-lint.txt
	"$(SHC_LINT_PYTHON_BIN)" -m venv "$(SHC_LINT_VENV)"
	"$(SHC_LINT_PYTHON)" -m pip install -r tests/requirements-shc-lint.txt

shc-lint-setup: $(SHC_ANSIBLE_LINT)

shc-lint: shc-lint-setup
	"$(SHC_ANSIBLE_LINT)" -v -c ./tests/ansible-lint-shc.cfg $(SHC_LINT_FILES)
	"$(SHC_ANSIBLE_PLAYBOOK)" --syntax-check -i 'localhost,' site.yml

shc-unit-test: shc-lint-setup
	"$(SHC_LINT_PYTHON)" -m pytest -q tests/small/test_environ.py -k 'SearchHeadClustering or IndexerClustering'
	"$(SHC_LINT_PYTHON)" -m pytest -q tests/small/test_indexer_search_address_tasks.py
	SHC_ANSIBLE_PLAYBOOK="$(SHC_ANSIBLE_PLAYBOOK)" "$(SHC_LINT_PYTHON)" -m pytest -q tests/small/test_indexer_search_address_behavior.py
	"$(SHC_LINT_PYTHON)" -m pytest -q tests/small/test_start_splunk_tasks.py

shc-check: shc-lint shc-unit-test

shc-lint-clean:
	rm -rf "$(SHC_LINT_VENV)"

lint: test-setup
	ansible-lint -v -c ./tests/ansible-lint.cfg site.yml roles/**/**/*.yml roles/**/**/**/*.yml

py3k-lint: test-setup 
	# We're treating each file separately here, because of their scarcity
	# This will need to be re-evaluated if a full blown module gets in here
	pylint --py3k $(shell find . -name "*.py")
	caniusepython3 -r tests/requirements.txt

test: lint py3k-lint small-tests large-tests

py3k-test: py3k-test-setup py3k-small-tests py3k-large-tests

small-tests: test-setup
	@echo 'Running the super awesome python2 small tests'
	pytest -sv tests/small/ --junitxml tests/results/small-tests.xml
	
py3k-small-tests: py3k-test-setup
	@echo 'Running the super awesome python3 small tests'
	python3 -m pytest -sv tests/small/ --junitxml tests/results/small-tests.xml
	
large-tests: test-setup
	@echo 'Running the super awesome large tests'
	cd roles/splunk_standalone && molecule test --all
	cd roles/splunk_universal_forwarder && molecule test --all
	cd roles/splunk_heavy_forwarder && molecule test --all
	cd roles/splunk_indexer && molecule test --all
	cd roles/splunk_monitor && molecule test --all

py3k-large-tests: py3k-test-setup
	@echo 'Running the super awesome large tests'
	cd roles/splunk_standalone && python3 -m molecule test --all
	cd roles/splunk_universal_forwarder && python3 -m molecule test --all
	cd roles/splunk_heavy_forwarder && molecule test --all
	cd roles/splunk_indexer && molecule test --all
	cd roles/splunk_monitor && python3 -m molecule test --all
