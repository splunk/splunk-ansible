## Changelog

## Navigation

* [9.0.4](#904)
* [9.0.0](#900)
* [8.2.10](#8210)
* [8.2.6](#826)
* [8.2.5](#825)
* [8.2.4](#824)
* [8.2.3.2](#8232)
* [8.2.3](#823)
* [8.2.2](#822)
* [8.2.1](#821)
* [8.2.0](#820)
* [8.1.13](#8113)
* [8.1.10](#8110)
* [8.1.9](#819)
* [8.1.8](#818)
* [8.1.7.1](#8171)
* [8.1.7](#817)
* [8.1.6](#816)
* [8.1.5](#815)
* [8.1.4](#814)
* [8.1.3](#813)
* [8.1.2](#812)
* [8.1.1](#811)
* [8.1.0.1](#8101)
* [8.1.0](#810)
* [8.0.10](#8010)
* [8.0.9](#809)
* [8.0.8](#808)
* [8.0.7](#807)
* [8.0.6.1](#8061)
* [8.0.6](#806)
* [8.0.5.1](#8051)
* [8.0.5](#805)
* [8.0.4.1](#8041)
* [8.0.4](#804)
* [8.0.3](#803)
* [8.0.2.1](#8021)
* [8.0.2](#802)
* [8.0.1](#801)
* [8.0.0](#800)
* [7.3.9](#739)
* [7.3.8](#738)
* [7.3.7](#737)
* [7.3.6](#736)
* [7.3.5](#735)
* [7.3.4.2](#7342)
* [7.3.4](#734)
* [7.3.3](#733)
* [7.3.2](#732)
* [7.3.1](#731)
* [7.3.0](#730)
* [7.2.10.1](#72101)
* [7.2.10](#7210)
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

## 9.0.4

#### Changes
* Support for latest major Splunk release
* Documentation updates + bugfixes

---

## 9.0.0

#### Changes
* Support for latest major Splunk release
* Documentation updates + bugfixes
---

## 8.2.10

#### Changes
* Bugfixes

---

---

## 8.2.6

#### Changes
* Bugfixes

---

## 8.2.5

#### Changes
* Bugfixes

---

## 8.2.4

#### Changes
* Bugfixes

---

## 8.2.3.2

#### Changes
* Patch release for CVE-2021-44228

---

## 8.2.3

#### Changes
* Bugfixes

---

## 8.2.2

#### What's New?
* Support for installing apps directly to a given path using `app_paths_install`. See our [documentation](https://splunk.github.io/splunk-ansible/ADVANCED.html#apps) for details.

#### Changes
* Bugfixes

---

## 8.2.1

#### What's New?
* Support for installing apps locally on a Cluster Manager or Deployer instance using `apps_location_local`. Both `apps_location` and `apps_location_local` can be used concurrently and follow the same syntax. See our [documentation](https://splunk.github.io/splunk-ansible/ADVANCED.html#apps) for details.

#### Changes
* Enabled `force_basic_auth` to reduce requests to splunkd
* Bugfixes

---

## 8.2.0

#### What's New?
* Added support for setting `clientName` in `deploymentclient.conf`
    * `splunk.deployment_client.name` in `default.yml`
    * `SPLUNK_DEPLOYMENT_CLIENT_NAME` environment variable

#### Changes
* Bugfixes

---

## 8.1.13

#### Changes
* Bugfixes

---

## 8.1.10

#### Changes
* Bugfixes

---

## 8.1.9

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.5.

#### Changes
* See [8.2.5](#825) changes above.

---

## 8.1.8

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.4.

#### Changes
* See [8.2.4](#824) changes above.

---

## 8.1.7.1

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.3.2.

#### Changes
* See [8.2.3.2](#8232) changes above.

---

## 8.1.7

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.3.

#### Changes
* See [8.2.3](#823) changes above.

---

## 8.1.6

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.2.

#### Changes
* See [8.2.2](#822) changes above.

---

## 8.1.5

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.1.

#### Changes
* See [8.2.1](#821) changes above.

---

## 8.1.4

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.0.

#### Changes
* See [8.2.0](#820) changes above.

---

## 8.1.3

#### Changes
* Bugfixes
* Documentation and CI updates

---

## 8.1.2

#### Changes
* Bugfixes and documentation updates

---

## 8.1.1

#### Changes
* Fetches peer node data for DMC
* Bugfixes and documentation updates

---

## 8.1.0.1

#### Changes
* Bugfixes and cleanup

---

## 8.1.0

#### What's New?
* Added environment variables to configure HTTPS on Splunkd. See [Supported environment variables](ADVANCED.md#supported-environment-variables) for details.
    * `SPLUNKD_SSL_` prefixed environment variables
    * `splunk.ssl` section in `default.yml`

#### Changes
* Enabled multisite for the `splunk_monitor` role
* Enabled local indexing on the license master
* Bugfixes and cleanup

---

## 8.0.10

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.1.

#### Changes
* See [8.2.1](#821) changes above.

---

## 8.0.9

#### What's New?
Syncing with latest codebase - currently up to sync with 8.2.0.

#### Changes
* See [8.2.0](#820) changes above.

---

## 8.0.8

#### What's New?
Syncing with latest codebase - currently up to sync with 8.1.1.

#### Changes
* See [8.1.1](#811) changes above.

---

## 8.0.7

#### What's New?
Syncing with latest codebase - currently up to sync with 8.1.0.

#### Changes
* See [8.1.0](#810) changes above.

---

## 8.0.6.1

#### What's New?
Syncing with latest codebase - currently up to sync with 8.1.1.

#### Changes
* See [8.1.1](#811) changes above.

---

## 8.0.6

#### What's New?
* Support for declarative admin password, enabling password updates and rotations. `splunk.password` will always be the password for the admin user and changes to `splunk.password` will drive password reconciliation.
    * `splunk.declarative_admin_password` in `default.yml`
    * `SPLUNK_DECLARATIVE_ADMIN_PASSWORD` environment variable
* Added flag to disable pop-ups and new user tour
    * `splunk.disable_popups` in `default.yml`
    * `SPLUNK_DISABLE_POPUPS` environment variable

#### Changes
* Fixed default variable propagation order 
* ASan v5 is dynamically linked to builds
* Bugfixes and security updates

---

## 8.0.5.1

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.6.

#### Changes
* See [8.0.6](#806) changes above.

---

## 8.0.5

#### What's New?
* Support for Splunk Enterprise Security (ES)
* Added a role for the Distributed Monitoring Console (DMC)
* Support for forwarding from the Splunk Data Stream Processor (DSP)

#### Changes
* `splunk.license_master_url` now allows scheme and port to be set along with the protocol
* Updates to tests and documentation

---

## 8.0.4.1

#### What's New?
* Support for setting the [deployer push mode](https://docs.splunk.com/Documentation/Splunk/latest/DistSearch/PropagateSHCconfigurationchanges#Choose_a_deployer_push_mode) to control how apps are bundled and distributed to cluster members:
    * `shc.deployer_push_mode` in `default.yml`
* Added the config variable `auxiliary_cluster_masters` to support enabling a search head to search across multiple indexer clusters. See [Multi-Cluster Search](advanced/MULTICLUSTERSEARCH.md) for details on configuration.
* Documentation on executing `splunk-ansible` remotely, through a controller node such as Ansible Tower/AWX


#### Changes
* Apps copied from `etc/apps` now include the `local` directory, ignoring `local/app.conf`
* Set custom Splunkd connection timeout using either:
    * `splunk.connection_timeout` in `default.yml`
    * `SPLUNK_CONNECTION_TIMEOUT` environment variable

---

## 8.0.4

#### What's New?
* Support for custom SSL certificates for the Splunkd management endpoint
* Support for custom ports for [Splunk Application Server](https://docs.splunk.com/Documentation/ITSI/latest/IModules/AboutApplicationServerModule) and [App KV Store](https://docs.splunk.com/Documentation/Splunk/8.0.0/Admin/AboutKVstore) using either:
    * `splunk.appserver.port`, `splunk.kvstore.port` in `default.yml`
    * `SPLUNK_APPSERVER_PORT`, `SPLUNK_KVSTORE_PORT` environment variables
* Java installation through `default.yml` with `java_download_url`, `java_update_version`, and `java_version`
* Support for Windows+AWS deployments for Splunk v7.2 and v7.3


#### Changes
* Set pass4SymmKey for indexer discovery separately from pass4SymmKey for indexer clustering with either:
    * `splunk.idxc.discoveryPass4SymmKey` in `default.yml`
    * `SPLUNK_IDXC_DISCOVERYPASS4SYMMKEY` environment variable
* `outputs.conf` is configured without REST calls to ensure forwarding is enabled before Splunk starts
* Splunk Deployer can be used as a deployment client
* Refactored molecule test structure

---

## 8.0.3

#### What's New?
* Support for custom SSL certificates for the HEC endpoint
* Support for Java installations on Red Hat and CentOS
* Updated defaults for `service_name`

#### Changes
* Switched `splunk.conf` in `default.yml` from a dictionary mapping to an array-based scheme. The change is backwards compatible but moving to the new array-based type is highly recommended as the new standard.
* In S2S configuration, revised Splunk restart trigger to occur only when `splunktcp` has changed and Splunk is running
* Refactored how apps are copied and disabled
* Bugfix for supporting empty stanzas in config files

---

## 8.0.2.1

#### What's New?
* Added support for reading `SPLUNK_PASSWORD` from a file
* License master and cluster master URLs are now also configurable in the `default.yml` config, as well as with the `LICENSE_MASTER_URL` and `CLUSTER_MASTER_URL` environment variables
* Added support for auto-detecting the `service_name` for SplunkForwarder and allowing manual configuration with `splunk.service_name`

#### Changes
* All HEC related variables were revised to follow a nested dict format in `default.yml`, i.e. `splunk.hec_enableSSL` is now `splunk.hec.ssl`. See the [Provision HEC](EXAMPLES.md#provision-hec) example in the docs.
* Fixed HEC-related API calls to be idempotent. This supports changing anything in `splunk.hec.*` and having the change be reflected upon next container restart.

---

## 8.0.2

#### What's New?
* Revised Splunk forwarding/receiving plays to optionally support SSL. See [About securing data from forwarders](https://docs.splunk.com/Documentation/Splunk/latest/Security/Aboutsecuringdatafromforwarders).
* Initial support for forwarder management using [Splunk Monitoring Console](https://docs.splunk.com/Documentation/Splunk/latest/DMC/DMCoverview)
* New environment variables exposed to control replication/search factor for clusters, key/value pairs written to `splunk-launch.conf`, and replacing default security key (pass4SymmKey)

#### Changes
* Created new environment variables to control indexer + search head clustering replication and search factor at run-time; error handling of these values are now moved into dynamic inventory script
* Created new environment variable `SPLUNK_PASS4SYMMKEY` to allow users to change the default shipped with Splunk Enterprise. Additionally, consolidated naming, so `SPLUNK_SHC_SECRET` and `SPLUNK_IDXC_SECRET` will now be replaced by `SPLUNK_SHC_PASS4SYMMKEY` and `SPLUNK_IDXC_PASS4SYMMKEY` respectively in the future (see documentation on [securing clusters](https://docs.splunk.com/Documentation/Splunk/latest/Security/Aboutsecuringclusters))
* Added `SPLUNK_LAUNCH_CONF` that accepts key=value comma-separated pairs (ex: `SPLUNK_LAUNCH_CONF=OPTIMISTIC_ABOUT_FILE_LOCKING=1,HELLO=WORLD`) that will get written to the Splunk Enterprise instance's `splunk-launch.conf`
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
* Adding more advanced options for SmartStore, including cache manager, per-index retention sizes, and hotlist recency settings
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

## 7.3.9

#### What's New?
Syncing with latest codebase - currently up to sync with 8.1.2.

#### Changes
* See [8.1.2](#812) changes.

---

## 7.3.8

#### What's New?
Syncing with latest codebase - currently up to sync with 8.1.0.1.

#### Changes
* See [8.1.0.1](#8101) changes.

---

## 7.3.7

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.5.

#### Changes
* See [8.0.5](#805) changes.


---

## 7.3.6

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.4.1.

#### Changes
* See [8.0.4.1](#8041) changes.

---

## 7.3.5

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.2.1.

#### Changes
* See [8.0.2.1](#8021) changes.

---

## 7.3.4.2

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.2.1.

#### Changes
* See [8.0.2.1](#8021) changes.

---

## 7.3.4

#### What's New?
* Syncing with latest codebase - currently up to sync with 8.0.1.

#### Changes
* See [8.0.1](#801) changes.

---

## 7.3.3

#### What's New?
* Support for variety of Splunk package types
* Better management of deployment server apps
* Bugfixes around app installation

#### Changes
* Removing unnecessary apps in distributed ITSI installations
* Partitioning apps in `serverclass.conf` when using the deployment server
* Adding support for activating Splunk Free license on boot
* Support for cluster labels via environment variables
* Bugfixes around app installation (through `default.yml` and pathing)

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

## 7.2.10.1

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.3.

#### Changes
* See [8.0.3](#803) changes.

---

## 7.2.10

#### What's New?
Syncing with latest codebase - currently up to sync with 8.0.2.1.

#### Changes
* See [8.0.2.1](#8021) changes.

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
* Hardening of asynchronous SHC bootstrapping procedures
* App installation across all topologies
* Adding CircleCI to support automated regression testing
* Minor bugfixes

#### Changes
* Changing replication port from 4001 to 9887 for PS and field best practices
* Adding support for multiple licenses via URL and file path globs
* Adding support for java installation
* Hardening SHC-readiness during provisioning due to large-scale deployment synchronization issues
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
* Introducing user-defined pre- and post- playbook hooks that can run before and after `site.yml`, respectively
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
