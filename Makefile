SHELL := /bin/bash

.PHONY: tests 

test_setup:
	@echo 'Install test requirements'
	pip install -r $(shell pwd)/tests/requirements.txt --upgrade

lint: test_setup
	ansible-lint -c ./tests/lint.cfg site.yml roles/*
