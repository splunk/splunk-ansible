## Changelog

## Navigation

* [7.3.1](#731)
* [7.3.0](#730)
* [7.2.7](#727)
* [7.2.6](#726)
* [7.2.5.1](#7251)
* [7.2.5](#725)
* [7.2.4](#724)
* [7.2.3](#723)
* [7.2.2](#722)
* [7.2.1](#721)
* [7.2.0](#720)

--- 

## 7.3.1

#### What's New?
* Enterprise Security application fix
* Bugfixes and environment cleanup

#### Changes
* Refactored Systemd
* Fixed application installation issues
* Fixed Ansible formatting issue
* Cleaned up Python files before install

---

## 7.3.0

#### What's New?
* Reorganizing multi-site playbooks
* Initial support for Cygwin-based Windows environments
* Minor bugfixes

#### Changes
* Adding ability to dynamically change `SPLUNK_ROOT_ENDPOINT` at start-up time
* Adding ability to dynamically change SplunkWeb HTTP port at start-up time
* Modified manner in which deployment server installs + distributes app bundles
* More multi-site functionality
* Support for Cygwin-based Windows environments
* Minor documentation changes

---

## 7.2.7 

#### What's New?
* Reorganizing multi-site playbooks
* Initial support for Cygwin-based Windows environments
* Minor bugfixes

#### Changes
* Adding ability to dynamically change `SPLUNK_ROOT_ENDPOINT` at start-up time
* Adding ability to dynamically change SplunkWeb HTTP port at start-up time
* Modified manner in which deployment server installs + distributes app bundles
* More multi-site functionality
* Support for Cygwin-based Windows environments
* Minor documentation changes

---

## 7.2.6

#### What's New?
Nothing - releasing new images to support Splunk Enterprise maintenance patch.

#### Changes
* Nothing - releasing new images to support Splunk Enterprise maintenance patch

---

## 7.2.5.1

#### What's New?
Nothing - releasing new images to support Splunk Enterprise maintenance patch.

#### Changes
* Nothing - releasing new images to support Splunk Enterprise maintenance patch

---

## 7.2.5

#### What's New?
* Introducing multi-site to the party
* Added `splunk_deployment_server` role
* Minor bugfixes

#### Changes
* Adding support for `splunk_deployment_server` role
* Adding initial framework to support multi-site deployments
* Small refactor of upgrade logic
* Ansible syntactic sugar and playbook clean-up
* Documentation overhaul
* Adding CircleCI to support automated regression testing

---

## 7.2.4

#### What's New?
* Support for Java installation in standalones and search heads
* Hardening of asyncronous SHC bootstrapping procedures
* App installation across all topologies
* Adding CircleCI to support automated regression testing
* Minor bugfixes

#### Changes
* Changing replication port from 4001 to 9887 for PS and field best practices
* Adding support for multiple licenses via URL and filepath globs
* Adding support for java installation
* Hardening SHC-readiness during provisioning due to large-scale deployment syncronization issues
* Extracting out `admin` username to be dynamic and flexible and enabling it to be user-defined
* App installation support for distributed topologies (SHC, IDXC, etc.) and some primitive premium app support
* Supporting Splunk restart only when required (via Splunk internal restart_required check)
* Minor documentation changes

---

## 7.2.3

#### What's New?
Nothing - releasing new images to support Splunk Enterprise maintenance patch.

#### Changes
* Nothing - releasing new images to support Splunk Enterprise maintenance patch

---

## 7.2.2

#### What's New?
* Permission model refactor
* Minor bugfixes

#### Changes
* Writing ansible logs to container artifact directory
* Adding templates for various OS/distributions to define default `default.yml` settings
* Adding `no_log` to prevent password exposure
* Support new permission model with `become/become_user` elevation/de-elevation when interacting with `splunkd`
* Support for out-of-the-box SSL-enabled SplunkWeb
* Adding ability to generate any configuration file in `$SPLUNK_HOME/etc/system/local`
* Introducing user-defined pre- and post- playbook hooks that can run before and after (respectively) site.yml
* Minor documentation changes

---

## 7.2.1

#### What's New?
* Initial SmartStore support
* App installation for direct URL link, local tarball, and from SplunkBase for standalone and forwarder

#### Changes
* Minor documentation changes
* Introducing support for [SmartStore](https://docs.splunk.com/Documentation/Splunk/latest/Indexer/AboutSmartStore) and index creation via `defaults.yml`
* Checks for first-time run to drive idempotency
* Adding capability to enable boot-start of splunkd as a service
* Support for user-defined splunk.secret file
* Adding app installation features (direct link, local tarball, and SplunkBase)
* Fixing bug where HEC receiving was not enabled on various Splunk roles
* Ansible syntactic sugar and playbook clean-up
* Minor documentation changes

---

## 7.2.0

#### What's New?
Everything :)

#### Changes
* Initial release!
* Support for Splunk Enterprise and Splunk Universal Forwarder deployments on Docker
* Supporting standalone and distributed topologies
