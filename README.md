# Welcome to the Splunk Ansible GitHub repository

[![Build Status](https://circleci.com/gh/splunk/splunk-ansible/tree/develop.svg?style=svg)](https://circleci.com/gh/splunk/splunk-ansible/tree/develop)

Welcome to Splunk's official repository containing Ansible playbooks for configuring and managing Splunk Enterprise and Universal Forwarder deployments. This repository contains plays that target all Splunk roles and deployment topologies, and currently work on any Linux-based platform. It is currently being used by the [Splunk Official Docker Image](https://github.com/splunk/docker-splunk) project. 

Please refer to [Ansible documentation](http://docs.ansible.com/) for more details about Ansible concepts and how it works. 

Please see the documentation for more details, including contributing and licensing information.

## What is Splunk Enterprise?

Splunk Enterprise is a platform for operational intelligence. Our software lets you collect, analyze, and act upon the untapped value of big data that your technology infrastructure, security systems, and business applications generate. It gives you insights to drive operational performance and business results.

Please refer to [Splunk products](https://www.splunk.com/en_us/software.html) for more knowledge about the features and capabilities of Splunk, and how you can bring it into your organization.

## What does this codebase do?

This code in this repository is used for configuring Splunk Enterprise and Splunk Universal Forwarder instances based on a declarative configuration. The role of Ansible here enables managing Splunk in a manner consistent with industry standards such as infrastructure automation and infrastructure-as-code.

## When should I use this repo?

This repository should be used by people interested in configuring Splunk according to recommended best practices. The playbooks in this codebase are internally-vetted procedures and operations that administer and manage Splunk as done within the company.

# Support and Help

Please use the [GitHub issue tracker](https://github.com/splunk/splunk-ansible/issues) to submit bugs or request features.

If you have questions or need support, you can:
* Post a question to [Splunk Answers](http://answers.splunk.com)
* Join the [#docker](https://splunk-usergroups.slack.com/messages/C1RH09ERM/) room in the [Splunk Slack channel](http://splunk-usergroups.slack.com)
* If you are a Splunk Enterprise customer with a valid support entitlement contract and have a Splunk-related question, you can also open a support case on the https://www.splunk.com/ support portal
* For details on the supported architectures, please refer to the documentation http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements#Containerized_computing_platforms

# Documentation

For full documentation, including isntallation, tutorials, and examples, please visit the [splunk-ansible documentation](https://splunk.github.io/splunk-ansible/) page.

# Contributing

See [CONTRIBUTING](docs/CONTRIBUTING.md)

# Changelog

See [CHANGELOG](docs/CHANGELOG.md)

# License

See [LICENSING](docs/LICENSING.md)

# Authors

Splunk Inc. and the Splunk Community
