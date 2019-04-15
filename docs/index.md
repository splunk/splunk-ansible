# Welcome to the splunk-ansible documentation!

Welcome to Splunk's official documentation regarding Ansible playbooks for configuring and managing Splunk Enterprise and Universal Forwarder deployments. This repository contains plays that target all Splunk roles and deployment topologies, and currently work on any Linux-based platform. It is currently being used by the [Splunk's official Docker image](https://github.com/splunk/docker-splunk) project. 

Please refer to [Ansible documentation](http://docs.ansible.com/) for more details about Ansible concepts and how it works. 

##### What is Splunk Enterprise?
Splunk Enterprise is a platform for operational intelligence. Our software lets you collect, analyze, and act upon the untapped value of big data that your technology infrastructure, security systems, and business applications generate. It gives you insights to drive operational performance and business results.

Please refer to [Splunk products](https://www.splunk.com/en_us/software.html) for more knowledge about the features and capabilities of Splunk, and how you can bring it into your organization.

##### What is splunk-ansible?
This code in this repository is used for configuring Splunk Enterprise and Splunk Universal Forwarder instances based on a declarative configuration. The role of Ansible here enables managing Splunk in a manner consistent with industry standards such as infrastructure automation and infrastructure-as-code.

This repository should be used by people interested in configuring Splunk according to recommended best practices. The playbooks in this codebase are internally-vetted procedures and operations that administer and manage Splunk as done within the company.

##### How to use splunk-ansible?
Splunk-Ansible project is a collection of Splunk configuration best practices written as Ansible scripts. The playbooks in this codebase are internally-vetted procedures and operations that administer and manage Splunk as done within the company. 

Although this project can be used independently as ordinary Ansible scripts, there are necessary environmental settings to have. For example, Splunk-Ansible assumes that you need different users with specific permission in your local environment. If you need a reference point, please refer to [Splunk's official Docker image](https://github.com/splunk/docker-splunk) project since Splunk-Ansible is tightly integrated into our docker image as the docker image offers a complete configuration package along with Splunk-Ansible.

----

## Table of Contents

* [Getting Started](SETUP.md)
    * [Install](SETUP.md#install)
    * [Configure](SETUP.md#configure)
    * [Run](SETUP.md#run)
* [Examples](EXAMPLES.md)
* [Advanced Usage](ADVANCED.md)
* [Architecture](ARCHITECTURE.md)
* [Contributing](CONTRIBUTING.md)
* [License](LICENSE.md)
