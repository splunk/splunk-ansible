# Welcome to the Splunk-Ansible documentation!

Welcome to the official Splunk documentation on [Ansible](https://docs.ansible.com/ansible/latest/index.html) playbooks for configuring and managing Splunk Enterprise and Universal Forwarder deployments. This repository contains plays that target all Splunk Enterprise roles and deployment topologies that work on any Linux-based platform.

Splunk-Ansible is currently being used by [Docker-Splunk](https://github.com/splunk/docker-splunk), the official Splunk Docker image project.

### What is Splunk Enterprise?
[Splunk Enterprise](https://www.splunk.com/en_us/software/splunk-enterprise.html) is a platform for operational intelligence. Our software lets you collect, analyze, and act upon the untapped value of big data that your technology infrastructure, security systems, and business applications generate. It gives you insights to drive operational performance and business results.

See [Splunk Products](https://www.splunk.com/en_us/software.html) for more information about the features and capabilities of Splunk products and how you can [bring them into your organization](https://www.splunk.com/en_us/enterprise-data-platform.html).

### What is Splunk-Ansible?
The [Splunk-Ansible project](https://github.com/splunk/splunk-ansible) is a collection of Splunk configuration best practices, written as Ansible scripts. These scripts, called playbooks, can be used for configuring Splunk Enterprise and Universal Forwarder instances based on a declarative configuration.

The playbooks in this codebase are internally-vetted procedures and operations that administer and manage Splunk as done within the company. Use Splunk-Ansible to manage Splunk Enterprise and Universal Forwarder instances in a manner consistent with industry standards, such as infrastructure automation and infrastructure-as-code.

### How to use Splunk-Ansible
Although this project can be used independently as ordinary Ansible scripts, there are necessary environment settings. For example, Splunk-Ansible assumes you need different users with specific permissions in your local environment.

For reference, see [Docker-Splunk](https://github.com/splunk/docker-splunk), the official Splunk Docker image project. Splunk-Ansible is tightly integrated into our Docker image, which offers a complete configuration package along with Splunk-Ansible.

See the [Ansible User Guide](https://docs.ansible.com/ansible/latest/user_guide/index.html) for more details on Ansible concepts and how it works.

----

## Table of Contents

* [Getting Started](SETUP.md)
    * [Install splunk-ansible](SETUP.md#install-splunk-ansible)
    * [Configure parameters](SETUP.md#configure-parameters)
    * [Execute playbooks](SETUP.md#execute-playbooks)
* [Examples](EXAMPLES.md)
* [Advanced Usage](ADVANCED.md)
* [Architecture](ARCHITECTURE.md)
* [Contributing](CONTRIBUTING.md)
* [Changelog](CHANGELOG.md)
* [License](LICENSE.md)
