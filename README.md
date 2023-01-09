# Splunk-Ansible: Provisioning Splunk Enterprise the Easy Way

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)&nbsp;
[![GitHub release](https://img.shields.io/github/v/tag/splunk/splunk-ansible?sort=semver&label=Version)](https://github.com/splunk/splunk-ansible/releases)

Welcome to the official Splunk repository containing Ansible playbooks for configuring and managing Splunk Enterprise and Universal Forwarder deployments. This repository contains plays that target all Splunk Enterprise roles and deployment topologies that work on any Linux-based platform.

Splunk-Ansible is currently being used by [Docker-Splunk](https://github.com/splunk/docker-splunk), the official Splunk Docker image project.

----

## Table of Contents

1. [Purpose](#purpose)
1. [Documentation](#documentation)
1. [Support](#support)
1. [Contributing](#contributing)
1. [License](#license)

----

## Purpose

#### What is Splunk Enterprise?
[Splunk Enterprise](https://www.splunk.com/en_us/software/splunk-enterprise.html) is a platform for operational intelligence. Our software lets you collect, analyze, and act upon the untapped value of big data that your technology infrastructure, security systems, and business applications generate. It gives you insights to drive operational performance and business results.

See [Splunk Products](https://www.splunk.com/en_us/software.html) for more information about the features and capabilities of Splunk products and how you can [bring them into your organization](https://www.splunk.com/en_us/enterprise-data-platform.html).

#### What is Splunk-Ansible?
The Splunk-Ansible project is a collection of Splunk configuration best practices, written as Ansible scripts. These scripts, called playbooks, can be used for configuring Splunk Enterprise and Universal Forwarder instances based on a declarative configuration.

The playbooks in this codebase are internally-vetted procedures and operations that administer and manage Splunk as done within the company. Use Splunk-Ansible to manage Splunk Enterprise and Splunk Universal Forwarder instances in a manner consistent with industry standards, such as infrastructure automation and infrastructure-as-code.

---

## Documentation

Visit the [Splunk-Ansible documentation](https://splunk.github.io/splunk-ansible/) page for full usage instructions, including installation, tutorials, and examples.

See the [Ansible User Guide](https://docs.ansible.com/ansible/latest/user_guide/index.html) for more details on Ansible concepts and how it works.

---

## Support
Use the [GitHub issue tracker](https://github.com/splunk/splunk-ansible/issues) to submit bugs or request features.

If you have questions or need support, you can:
* Post a question to [Splunk Answers](http://answers.splunk.com)
* Join the [#docker](https://splunk-usergroups.slack.com/messages/C1RH09ERM/) room in the [Splunk Slack channel](http://splunk-usergroups.slack.com)
* If you are a Splunk Enterprise customer with a support entitlement contract and have a question related to a Splunk product, you can open a support case on the [Splunk support portal](https://www.splunk.com/en_us/support-and-services.html).

---

## Contributing
We welcome feedback and contributions from the community! See the [contribution guidelines](docs/CONTRIBUTING.md) for more information on how to get involved.

---

## License
Copyright 2018-2020 Splunk.

Distributed under the terms of our [license](docs/LICENSE.md), Splunk-Ansible is a free and open-source software.
