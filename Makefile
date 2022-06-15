SHELL := /bin/bash

.PHONY: tests 

test-setup:
	@echo 'Install test requirements'
	pip install --upgrade pip
	pip install -r $(shell pwd)/tests/requirements.txt --upgrade

py3k-test-setup:
	pip3 install --upgrade pip
	pip3 install -r $(shell pwd)/tests/requirements.txt --upgrade

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
