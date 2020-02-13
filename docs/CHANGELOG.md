## Changelog

## Navigation

* [8.0.2](#802)
* [8.0.1](#801)
* [8.0.0](#800)
* [7.3.4](#734)
* [7.3.3](#733)
* [7.3.2](#732)
* [7.3.1](#731)
* [7.3.0](#730)
* [7.2.9](#729)
* [7.2.8](#728)
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

## 8.0.2

#### What's New?
* Revised Splunk forwarding/receiving plays to optionally support SSL (see documentation on [securing data from forwarders](https://docs.splunk.com/Documentation/Splunk/latest/Security/Aboutsecuringdatafromforwarders))
* Initial support for forwarder management using [Splunk Monitoring Console](https://docs.splunk.com/Documentation/Splunk/latest/DMC/DMCoverview)
* New environment variables exposed to control replication/search factor for clusters, key/value pairs written to `splunk-launch.conf`, and replacing default security key (pass4SymmKey)

#### Changes
* Created new environment variables to control indexer + search head clustering replication and search factor at run-time; error handling of these values are now moved into dynamic inventory script
* Created new environment variable `SPLUNK_PASS4SYMMKEY` to allow users to change the default shipped with Splunk Enterprise. Additionally, consolidated naming so `SPLUNK_SHC_SECRET` and `SPLUNK_IDXC_SECRET` will now be replaced by `SPLUNK_SHC_PASS4SYMMKEY` and `SPLUNK_IDXC_PASS4SYMMKEY` respectively in the future (see documentation on [securing clusters](https://docs.splunk.com/Documentation/Splunk/latest/Security/Aboutsecuringclusters))
* Added `SPLUNK_LAUNCH_CONF` that accepts key=value comma-separated pairs (ex: `SPLUNK_LAUNCH_CONF=OPTIMISTIC_ABOUT_FILE_LOCKING=1,HELLO=WORLLD`) that will get written to the Splunk Enterprise instance's `splunk-launch.conf`
* Splunk-to-Splunk forwarding and receiving is now rewritten to support an optional SSL. To utilize encryption, you must bring your own certificates and make them available to both forwarders and receivers. For more information, see the documentation on [securing forwarder to indexer communication](https://docs.splunk.com/Documentation/Splunk/8.0.1/Security/ConfigureSplunkforwardingtousesignedcertificates)
* Added `ansible_environment` variable to `default.yml` to set environment variables for task action contexts (see Ansible documentation on [setting environment](https://docs.ansible.com/ansible/latest/user_guide/playbooks_environment.html))
* Added and renamed variables in `default.yml` to control retry/backoff logic at a more granular level
* Refactored dynamic inventory script to remove duplicate code and improve code coverage
* Bugfixes around how clustering secrets were set - if you experience breakages, you can manually update the `pass4SymmKey` value in either `[shclustering]/[clustering]` stanzas of `server.conf` and restart Splunk to re-encrypt the tokens

**NOTE** Changes made to support new features may break backwards-compatibility with former versions of the `default.yml` schema. This was deemed necessary for maintainability and extensibility for these additional features requested by the community. While we do test and make an effort to support previous schemas, it is strongly advised to regenerate the `default.yml` if you plan on upgrading to this version.

**DEPRECATION WARNING** As mentioned in the changelog, the environment variables `SPLUNK_SHC_SECRET` and `SPLUNK_IDXC_SECRET` will now be replaced by `SPLUNK_SHC_PASS4SYMMKEY` and `SPLUNK_IDXC_PASS4SYMMKEY` respectively. Both are currently supported and will be mapped to the same setting now, but in the future we will likely remove both `SPLUNK_SHC_SECRET` and `SPLUNK_IDXC_SECRET`

---

## 8.0.1

#### What's New?
* Additional options to control SmartStore configuration
* Service name fixes for AWS
* Bugfixes around forwarding and SHC-readiness

#### Changes
* Small adjustment in forwarding settings to send data to specific tiers
* Bugfix in SHC readiness probe to properly handle membership list updates
* Adding more advanced options for SmartStore, including cachemanager, per-index retention sizes, and hotlist recency settings
**NOTE** If you are currently using SmartStore, this change does break backwards-compatibility with former versions of the `default.yml` schema. This was necessary to expose the additional features asked for by the community. Please regenerate the `default.yml` if you plan on upgrading to this version.

---

## 8.0.0

#### What's New?
* Python 2 and Python 3 compatibility
* Bugfixes

#### Changes
* Increasing delay intervals to better handle different platforms
* Adding vars needed for Ansible Galaxy
* Bugfix for pre-playbook tasks not supporting URLs

--- 

## 7.3.4

#### What's New?
* Syncing with latest codebase - currently up to sync with 8.0.1.

#### Changes
* See [8.0.1](#801) changes

--- 

## 7.3.3

#### What's New?
* Support for variety of Splunk package types
* Better management of deployment server apps
* Bugfixes around app installation

#### Changes
* Removing unnecessary apps in distributed ITSI installations
* Partioning apps in serverclass.conf when using the deployment server
* Adding support for activating Splunk Free license on boot
* Support for cluster labels via environment variables
* Bugfixes around app installation (through default.yml and pathing)

--- 

## 7.3.2

#### What's New?
* Python 2 and Python 3 compatibility
* Bugfixes

#### Changes
* Support and compatibility across Python 2 and Python 3
* Various bugfixes

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

## 7.2.9

#### What's New?
* Syncing with latest codebase - currently up to sync with 8.0.0.

#### Changes
* See [8.0.0](#800) changes

---

## 7.2.8

#### What's New?
* Syncing with latest codebase - currently up to sync with 7.3.0.

#### Changes
* See [7.3.0](#730) changes

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
