SHELL := /bin/bash

.PHONY: tests 

test_setup:
	@echo 'Install test requirements'
	pip install -r $(shell pwd)/tests/requirements.txt --upgrade

lint: test_setup
	ansible-lint -c ./tests/lint.cfg site.yml roles/* --exclude roles/splunk_universal_forwarder/tasks/setup_docker_monitoring.yml

test: test_setup small-tests

small-tests: 
	@echo 'Running the super awesome tests; Debian 9'
	pytest -sv tests/small/ --junitxml test-results/small-tests.xml
