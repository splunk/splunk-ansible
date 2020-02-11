# splunk-ansible: Provisioning Splunk Enterprise the Easy Way

[![Build Status](https://circleci.com/gh/splunk/splunk-ansible/tree/develop.svg?style=svg)](https://circleci.com/gh/splunk/splunk-ansible/tree/develop)

Welcome to Splunk's official repository containing Ansible playbooks for configuring and managing Splunk Enterprise and Universal Forwarder deployments. This repository contains plays that target all Splunk Enterprise roles and deployment topologies that work on any Linux-based platform. It is currently being used by [Splunk's official Docker image](https://github.com/splunk/docker-splunk) project.

**Visit the [splunk-ansible documentation](https://splunk.github.io/splunk-ansible/) page for full usage instructions, including installation, tutorials, and examples.**

See the [Ansible documentation](http://docs.ansible.com/) for more details about Ansible concepts and how it works.

----

## Table of Contents

1. [Purpose](#purpose)
1. [Support](#support)
1. [Contributing](#contributing)
1. [License](#license)

----

## Purpose

#### What is Splunk Enterprise?
Splunk Enterprise is a platform for operational intelligence. Splunk software lets you collect, analyze, and act upon the untapped value of big data that your technology infrastructure, security systems, and business applications generate. It gives you insights to drive operational performance and business results.

See [Splunk products](https://www.splunk.com/en_us/software.html) for more information about the features and capabilities of Splunk products and how you can bring it into your organization.

#### What is splunk-ansible?
Use the code in this repository to configure Splunk Enterprise and Splunk Universal Forwarder instances based on a declarative configuration. You can use Ansible to manage Splunk Enterprise and Splunk Universal Forwarder in a manner consistent with industry standards such as infrastructure automation and infrastructure-as-code.

The playbooks in this codebase are Splunk-vetted procedures and operations that administer and manage Splunk products as done within the company.

## Support
Please use the [GitHub issue tracker](https://github.com/splunk/splunk-ansible/issues) to submit bugs or request features.

If you have questions or need support, you can:
* Post a question to [Splunk Answers](http://answers.splunk.com)
* Join the [#docker](https://splunk-usergroups.slack.com/messages/C1RH09ERM/) room in the [Splunk Slack channel](http://splunk-usergroups.slack.com)
* If you are a Splunk Enterprise customer with a support entitlement contract and have a question related to a Splunk product, you can open a support case on the [Splunk support portal](https://www.splunk.com/en_us/support-and-services.html).

## Contributing
We welcome feedback and contributions from the community! See the [contribution guidelines](docs/CONTRIBUTING.md) for more information on how to get involved. 

## License
Copyright 2018-2020 Splunk.

Distributed under the terms of our [license](docs/LICENSE.md), splunk-ansible is a free and open-source software.
