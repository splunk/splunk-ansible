SHELL := /bin/bash

.PHONY: tests 

test_setup:
	@echo 'Install test requirements'
	pip install --upgrade pip
	pip install -r $(shell pwd)/tests/requirements.txt --upgrade

lint: test_setup
	ansible-lint -v -c ./tests/lint.cfg site.yml roles/**/**/*.yml roles/**/**/**/*.yml

test: lint small-tests large-tests

small-tests: test_setup
	@echo 'Running the super awesome small tests'
	pytest -sv tests/small/ --junitxml tests/results/small-tests.xml

large-tests: test_setup
	@echo 'Running the super awesome large tests'
	cd roles/splunk_standalone && molecule test
	cd roles/splunk_universal_forwarder && molecule test
