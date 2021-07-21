## Navigation

* [Spec](#spec)
  * [Configuration files](#configuration-files)
* [Example](#example)

---

## Spec
The following is the full spec file for a `default.yml` that controls how Splunk gets provisioned.

```
ansible_post_tasks: <list>
* list of paths or URLs to custom Ansible playbooks to run AFTER Splunk has been setup using the provided site.yml
* Default: []

ansible_pre_tasks: <list>
* list of paths or URLs to custom Ansible playbooks to run BEFORE Splunk sets up using the provided site.yml
* Default: []

ansible_environment: <dict>
* Map of environment variables used only during the execution context of all the Ansible tasks. For more information, see https://docs.ansible.com/ansible/latest/user_guide/playbooks_environment.html
* Default: {}

hide_password: <bool>
* Boolean that determines whether or not to output Splunk admin passwords through Ansible
* Default: false

retry_num: <int>
* Number of retries to make for potentially flakey/error-prone tasks
* Default: 60

wait_for_splunk_retry_num: <int>
* Number of retries to make when waiting for a Splunk instance to be available
* Default: 60

shc_sync_retry_num: <int>
* Number of retries to make when waiting for sync up with a search head cluster
* Default: 60

retry_delay: <int>
* Duration of waits between each of the aforementioned retries (in seconds)
* Default: 6

splunk_home_ownership_enforcement: true
* Boolean that to control and enable UAC on $SPLUNK_HOME (recommended to be enabled)
* Default: true

config:
  baked: <str>
  * Configuration filename
  * Default: default.yml

  defaults_dir: <str - filepath>
  * Location on filesystem where the default.yml can be found
  * Default: /tmp/defaults

  env:
    headers: <str>
    * Define header information (in necessary) when pulling default.yml from a URL 
    * Default: null

    var: <str>
    * Control environment variable name that determines location of default.yml 
    * Default: SPLUNK_DEFAULTS_URL

    verify: <bool>
    * Enable/disable SSL validation
    * Default: true
  host:
    headers: <str>
    * Define header information (in necessary) when pulling default.yml from a URL 
    * Default: null

    url: <str>
    * Define URL to pull default.yml from 
    * Default: null

    verify: <bool>
    * Enable/disable SSL validation
    * Default: true

  max_delay: <int>
  * Maximum duration (in seconds) between attempts to pull the default.yml from a remote source
  * Default: 60

  max_retries: <int>
  * Maximum attempts to pull the default.yml from a remote source
  * Default: 3

  max_timeout: <int>
  * Maximum timeout for attempts to pull the default.yml from a remote source
  * Default: 1200

splunkbase_username: <str>
* Used for authentication when downloading apps from https://splunkbase.splunk.com/ (this is NOT required to even be specified, unless you have SplunkBase apps defined in your splunk.apps_location)
* NOTE: Use this in combination with splunkbase_password. You will also need to run Ansible using the dynamic inventory script (environ.py) for this to register and work properly.
* Default: null

splunkbase_password: <str>
* Used for authentication when downloading apps from https://splunkbase.splunk.com/ (this is NOT required to even be specified, unless you have SplunkBase apps defined in your splunk.apps_location)
* NOTE: Use this in combination with splunkbase_username. You will also need to run Ansible using the dynamic inventory script (environ.py) for this to register and work properly.
* Default: null

splunkbase_token: <str>
* Used for authentication when downloading apps from https://splunkbase.splunk.com/ (this is NOT required to even be specified, unless you have SplunkBase apps defined in your splunk.apps_location)
* NOTE: This is ordinarily generated using the dynamic inventory script (environ.py) using the aforementioned `splunkbase_username` and `splunkbase_password` variables above, and every token has an expiry.
* Default: null

cert_prefix: <str>
* Specify the scheme used for the SplunkD management endpoint (typically port 8089). If you plan on running SplunkD over HTTP, you should set this to "http" so the Ansible plays are aware of the intended scheme.
* Default: https

java_download_url: <str>
* Java JDK URL that is dynamically fetched and installed at container run-time. For example: "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz"
* Default: null

java_update_version: <str>
* Name of the Java JDK file used for installation. For example: "openjdk-11.0.2_linux-x64_bin.tar.gz"
* Default: null

java_version: <str>
* String notifying the Ansible plays which version of Java is being installed so variables can be parsed properly. For example: "openjdk:11"
* Default: null

dmc_forwarder_monitoring: <bool>
* Feature-flag to enable forwarder asset monitoring through the Distributed Management Console (DMC). This is disabled by default.
* Default: false

dmc_asset_interval: <str>
* Cron-formatted string of the frequency and recurrence of the query that builds the forwarding assets table
* Default: "3,18,33,48 * * * *"

docker: <bool>
* DEPRECATED - this was used to signal whether or not the instance being provisioned was running in Docker. This does not affect playbook execution at all, but the dynamic inventory script environ.py will set this to setup host::vars mapping as needed.

splunk:
  role: <str>
  * Role to assume when setting up Splunk. Accepted values include: splunk_standalone, splunk_search_head, splunk_search_head_captain, splunk_indexer, splunk_deployer, splunk_cluster_master, splunk_deployment_server, splunk_heavy_forwarder, splunk_license_master, splunk_universal_forwarder, and splunk_monitor.
  * Default: splunk_standalone

  allow_upgrade:
  * Determines whether or not to perform an upgrade (to the splunk.build_location)
  * Default: true

  build_location: <str>
  * Splunk build location, either on the filesystem or a remote URL
  * Default: null

  build_url_bearer_token: <str>
  * Bearer token used to provide authorization when fetching a Splunk build from a remote URL. 
  * Default: null

  license_master_url: <str>
  * Hostname of Splunk Enterprise license master instance. May be overridden using SPLUNK_LICENSE_MASTER_URL environment variable.
  * Default: null

  cluster_master_url: <str>
  * Hostname of Splunk Enterprise cluster master instance. May be overridden using SPLUNK_CLUSTER_MASTER_URL environment variable.
  * Default: null

  auxiliary_cluster_masters: <list>
  * Array of other cluster masters to support multi-cluster distributed search. The node must be a search head configured to peer an initial cluster master before the masters listed here are added. For more information, see https://docs.splunk.com/Documentation/Splunk/latest/Indexer/Configuremulti-clustersearch. 
  * Default: []
  * Example:
  *   auxiliary_cluster_masters:
  *   - url: https://master.us-west.corp.net:8089
  *     pass4SymmKey: thisisasecret
  *   - url: https://master.us-east.corp.net:8089
  *     pass4SymmKey: thisisanothersecret
  
  deployer_url: null
  * Hostname of Splunk Enterprise deployer instance. May be overridden using SPLUNK_DEPLOYER_URL environment variable.
  * Default: null

  deployment_client: <dict>
  * Deployment client object that configures `deployment-client` stanza of `deploymentclient.conf` file.
  * Default: null

    name: null
    * Client name for deployment client. May be overridden using SPLUNK_DEPLOYMENT_CLIENT_NAME environment variable.
    * Default: null

  search_head_captain_url: null
  * Hostname of Splunk Enterprise search head cluster captain instance. May be overridden using SPLUNK_SEARCH_HEAD_CAPTAIN_URL environment variable.
  * Default: null

  search_head_cluster_url: null
  * URL of the Splunk search head cluster
  * NOTE: This is being deprecated in favor of `splunk.search_head_captain_url`.
  * Default: null

  disable_popups: <bool>
  * When set to true, pop-ups/modals will be disabled from login on the homescreen and search app.
  * Default: false

  preferred_captaincy: <bool>
  * Boolean to determine whether splunk should set a preferred captain.  This can have an effect on day 2 operations if the search heads need to be restarted 
  * Default: true

  apps_location: <list>
  * List of apps to install - elements can be in the form of a URL or a location in the filessytem
  * Default: null

  license_uri: <str>
  * Path or remote URL to a valid Splunk license
  * Default: null

  ignore_license: <bool>
  * Allow proceeding with a bad/invalid Splunk license
  * Default: false

  license_download_dest: <str - filepath>
  * Path in filesystem where licenses will be downloaded as
  * Default: /tmp/splunk.lic

  wildcard_license: <bool>
  * Enable licenses to be interpreted as fileglobs, to support provisioning with multiple Splunk licenses
  * Default: false

  admin_user: <str>
  * Default admin-level user to run provisioning commands under. It is only possible to change the admin user name at the first-time execution of Splunk Enterprise.
  * Default: admin

  password: <str>
  * Default Splunk admin user password. This is REQUIRED when starting Splunk, and can only be set during the first-time run of the playbooks. If changes are required to the admin password, they should be done through SplunkWeb/CLI and the new value should be re-entered here.
  * Default: null

  declarative_admin_password: <bool>
  * When set to true, the playbooks will always enforce that the admin password is set to the value of `password` above. Any changes to the admin password outside of splunk-ansible will be reverted.
  * Default: false

  user: <str>
  * Host user under which Splunk will run
  * Default: splunk

  group: <str>
  * Host group under which Splunk will run
  * Default: splunk

  enable_service: <bool>
  * Determine whether or not to enable Splunk for boot-start (start via sysinitv or systemd, etc.)
  * Default: false

  service_name: <str>
  * Specify the service name of splunkd when running through sysinitv, systemd, etc.
  * Default: null

  opt: <str - filepath>
  * Path in filesystem where Splunk will be installed
  * Default: /opt

  home: <str - filepath>
  * Path in filesystem where SPLUNK_HOME is located
  * Default: /opt/splunk

  exec: <str - filepath>
  * Path in filesystem where splunk binary exists (this will depend on splunk.home)
  * Default: /opt/splunk/bin/splunk

  pid: <str - filepath>
  * Path in filesystem of splunk PID file (this will depend on splunk.home)
  * Default: /opt/splunk/var/run/splunk/splunkd.pid

  app_paths:
    default: <str - filepath>
    * Path in filesystem of default apps (this will depend on splunk.home)
    * Default: /opt/splunk/etc/apps

    deployment: <str - filepath>
    * Path in filesystem of deployment apps (this will depend on splunk.home)
    * Default: /opt/splunk/etc/deployment-apps

    httpinput: <str - filepath>
    * Path in filesystem of the HTTP input apps (this will depend on splunk.home)
    * Default: /opt/splunk/etc/apps/splunk_httpinput

    idxc: <str - filepath>
    * Path in filesystem of indexer cluster master apps (this will depend on splunk.home)
    * Default: /opt/splunk/etc/master-apps

    shc: <str - filepath>
    * Path in filesystem of search head cluster apps (this will depend on splunk.home)
    * Default: /opt/splunk/etc/shcluster/apps

  app_paths_install:
    default: <list>
    * List of apps to install into app_paths.default - elements can be in the form of a URL or a location in the filessytem
    * Default: null

    deployment: <list>
    * List of apps to install into app_paths.deployment - elements can be in the form of a URL or a location in the filessytem
    * Default: null

    idxc: <list>
    * List of apps to install into app_paths.idxc on the CM to be pushed to the Indexer Cluster - elements can be in the form of a URL or a location in the filessytem
    * Default: null

    shc: <list>
    * List of apps to install into app_paths.shc on the deployer to be pushed to the Search Head Cluster- elements can be in the form of a URL or a location in the filessytem
    * Default: null

  hec:
    enable: <bool>
    * Determine whether or not to disable setting up the HTTP event collector (HEC)
    * Default: True

    ssl: <bool>
    * Determine whether or not to enable SSL on the HTTP event collector (HEC) endpoint
    * Default: True

    port <int>
    * Determine the port used for the HTTP event collector (HEC) endpoint
    * Default: 8088

    token: <str>
    * Determine a token to use for the HTTP event collector (HEC) endpoint
    * Default: null

    cert: <str>
    * Filepath to a custom SSL certificate for HEC
    * Default: null

    password: <str>
    * SSL password used to create the SSL certificate for HEC
    * Default: null

  http_enableSSL: <int|bool>
  * Determine whether or not to enable SSL on SplunkWeb
  * Default: 0

  http_enableSSL_cert: <str>
  * Path in filesystem to SplunkWeb SSL certificate
  * Default: null

  http_enableSSL_privKey: <str>
  * Path in filesystem to SplunkWeb SSL private key
  * Default: null

  http_enableSSL_privKey_password: <str>
  * Password used to setup SplunkWeb SSL private key
  * Default: null

  http_port: <int>
  * Determine the port used for SplunkWeb
  * Default: 8000

  root_endpoint: <str>
  * Root endpoint used when serving SplunkWeb over a different path
  * Default: null

  s2s:
    enable: <bool>
    * Determine whether or not to enable Splunk-to-Splunk communication. This is REQUIRED for any distributed topologies.
    * Default: true

    port: <int>
    * Determine the port used for the Splunk-to-Splunk networking
    * Default: 9997

    ssl: <bool>
    * When true, enables splunktcp input to use SSL
    * Default: false

    cert: <str>
    * Coupled with the ssl parameter above, specify the path to the SSL certificate used for splunktcp-ssl
    * Default: null

    password: <str>
    * Coupled with the ssl parameter above, specify the SSL password used for splunktcp-ssl
    * Default: null

    ca: <str>
    * Coupled with the ssl parameter above, specify the path to the CA certificate used for splunktcp-ssl
    * Default: null

  svc_port: <int>
  * Determine the port used for Splunk management/remote API calls
  * Default: 8089

  appserver:
    port: <int>
    * Determine the port used for Splunk Application Server
    * Default: 8065

  kvstore:
    port: <int>
    * Determine the port used for Splunk Key-Value store
    * Default: 8191

  launch: null
  * key::value pairs for environment variables that get written to ${SPLUNK_HOME}/etc/splunk-launch.conf
  * Default: null

  asan: <bool>
  * Feature-flag to enable special configurations when using debug, address-sanitized builds. This is not used externally and not recommended to change.
  * Default: false

  connection_timeout: <int>
  * Change timeout value (in seconds) for the setting `splunkdConnectionTimeout` in web.conf. This triggers a change only when the value is non-zero.
  * Default: 0

  secret: <str>
  * Secret passcode used to encrypt all of Splunk's sensitive information on disk. When not set, Splunk will autogenerate a unique secret local to each installation. This is NOT required for any standalone or distributed Splunk topology
  * NOTE: This may be set once at the start of provisioning any deployment. Any changes made to this splunk.secret after the deployment has been created must be resolved manually, otherwise there is a severe risk of bricking the capabilities of your Splunk environment.
  * Default: null

  pass4SymmKey: <str>
  * Password for Symmetric Key used to encrypt Splunk's sensitive information on disk. When not set, Splunk will encrypt a default value (`changeme`) with `splunk.secret` and set it as `pass4SymmKey` in the `[general]` stanza of `/opt/splunk/etc/system/local/server.conf`.
  * Default: null

  ssl:
  * Configure the default certificates used by Splunk Enterprise
  
    enable: <bool>
    * Enable SSL on the Splunkd management API (typically port 8089)
    * Default: True

    cert: <str>
    * Specify the path to the SSL certificate used for the Splunkd management API
    * Default: null

    password <str>
    * Specify the path to the SSL password used by the certificate above
    * Default: null

    ca: <str>
    * Specify the path to the CA certificate used for the Splunkd management API
    * Default: null

  idxc:
    label: <str>
    * Provide a label for indexer clustering configuration
    * Default: idxc_label

    replication_factor: <int>
    * Determine knowledge object replication factor
    * Default: 3

    replication_port: <int>
    * Determine the port used for replication of artifacts
    * Default: 9887

    search_factor: <int>
    * Determine the search factor used by indexer clustering
    * Default: 3

    secret: <str>
    * Determine the secret used to configure indexer clustering. This is pass4SymmKey in the `[clustering]` stanza of server.conf.
    * NOTE: This is being deprecated in favor of `splunk.idxc.pass4SymmKey`.
    * Default: null

    pass4SymmKey: <str>
    * Determine the secret used to configure indexer clustering. This is REQUIRED when setting up indexer clustering. This is pass4SymmKey in the `[clustering]` stanza of server.conf.
    * Default: null

    discoveryPass4SymmKey: <str>
    * Determine the secret used to enable indexer discovery (for any forwarding clients connecting to the cluster master). This is pass4SymmKey in the `[indexer_discovery]` stanza of server.conf.
    * Default: null

  multisite_master:
  * Specify the location of the multisite cluster
  * Default: null

  multisite_master_port:
  * Specify the management port of the multisite cluster master
  * Default: 8089

  multisite_replication_factor_origin:
  * Determine origin-level knowledge object replication factor when in a multisite environment
  * Default: 2

  multisite_replication_factor_total:
  * Determine site-level knowledge object replication factor when in a multisite environment
  * Default: 3

  multisite_search_factor_origin:
  * Determine origin-level search replication factor when in a multisite environment
  * Default: 1

  multisite_search_factor_total:
  * Determine site-level search replication factor when in a multisite environment
  * Default: 3

  site:
  * Define the site of this particular Splunk Enterprise instance when in a multisite environment
  * Default: null

  all_sites:
  * Define all sites of the topology when in a multisite environment
  * Default: null

  set_search_peers: <bool>
  * Feature-flag to disable the automatic peering from the search tier to the indexer tier (cluster master or indexers directly). It is discouraged to change this to false, but it is exposed for the purposes of testing and isolating the groups.
  * Default: true

  shc:
    label: <str>
    * Provide a label for search head clustering configuration
    * Default: shc_label

    replication_factor: <int>
    * Determine knowledge object replication factor
    * Default: 3

    replication_port: <int>
    * Determine the port used for replication of artifacts
    * Default: 9887

    secret: <str>
    * Determine the secret used to configure search head clustering. This is pass4SymmKey in server.conf.
    * NOTE: This is being deprecated in favor of `splunk.shc.pass4SymmKey`
    * Default: null

    pass4SymmKey: <str>
    * Determine the secret used to configure search head clustering. This is REQUIRED when setting up search head clustering. This is pass4SymmKey in the `[shclustering]` stanza of server.conf.
    * Default: null

    deployer_push_mode: <str>
    * Change the strategy used by the deployer when bundling apps and distributing them across the search head cluster. The acceptable modes are: full, local_only, default_only, and merge_to_default (merge_to_default is the default unless otherwise specified).
    * For more information, please see: https://docs.splunk.com/Documentation/Splunk/latest/DistSearch/PropagateSHCconfigurationchanges#Set_the_deployer_push_mode
    * Default: null

  dfs:
    enable: <bool>
    * Enable Data Fabric Search (DFS)
    * Default: false

    port: <int>
    * Identifies the port on which the DFSMaster Java process runs.
    * Default: 9000

    dfc_num_slots: <int>
    * Maximum number of concurrent DFS searches that run on each search head
    * Default: 4
    
    dfw_num_slots: <int>
    * Maximum number of concurrent DFS searches that run on a search head cluster
    * Default: 10
    
    dfw_num_slots_enabled: <bool>
    * Enables you to set the value of the field dfw_num_slots.
    * Default: false

    spark_master_host: <str>
    * This setting identifies the Spark master.
    * Default: 127.0.0.1

    spark_master_webui_port: <int>
    * Identifies the port for the Spark master web UI.
    * Default: 8080

  dsp:
    enable: <bool>
    * Enable Data Stream Procesor forwarding (DSP)
    * Default: false

    server: <str>
    * DSP forwarding service endpoint
    * Default: forwarders.scp.splunk.com:9997

    cert: <str>
    * Filepath to DSP forwarding client certificate - if set to 'auto', a new cert will be generated
    * Default: null

    verify: <bool>
    * Enable server verification when forwarding
    * Default: false

    pipeline_name: <str>
    * When configuring a new/existing DSP pipeline, the name of the pipeline
    * Default: null

    pipeline_desc: <str>
    * When configuring a new/existing DSP pipeline, the description of the pipeline
    * Default: null

    pipeline_spec: <str>
    * When configuring a new/existing DSP pipeline, the specification of the pipeline in SPL2 syntax
    * Default: null

  smartstore: <dict>
  * Nested dict obj to enable automatic SmartStore provisioning
  * Default: null

    cachemanager: <dict>
    * cachemanager server.conf settings related to SmartStore
    * Default: null
    * Example:
      max_cache_size: 500
      max_concurrent_uploads: 7

    index: <list>
    * Per-index SmartStore configuration
    * Default: null
    * Example:
      - indexName: custom_index
        remoteName: my_storage
        scheme: http
        remoteLocation: my_storage.net
        s3:
          access_key: <access_key>
          secret_key: <secret_key>
          endpoint: http://s3-us-west-1.amazonaws.com
        maxGlobalDataSizeMB: 500
        maxGlobalRawDataSizeMB: 200
        hotlist_recency_secs: 30
        hotlist_bloom_filter_recency_hours: 1

  tar_dir: <str>
  * Name of directory for the Splunk tar
  * Default: splunk
  
  # NOTE: This is the updated schema for this entry - please refer to "Configuration files" section for more info
  conf: <list>
    - key: <sttr - filename without .conf suffix)
      value:
        directory: <str - filepath>
        * Path in filesystem to create `.conf` file
        * Default: /opt/splunk/etc/system/local

        content: <dict>
          (section name): <dict>
            (name) : (value)
              * Key-value pairs in configuration file
```

### Configuration files

**Using this method of configuration file generation may not create a configuration file the way Splunk expects. Verify the generated configuration file to avoid errors. Use at your own discretion**

The `default.yml` file can be used to specify multiple named configuration files.

`conf` accepts an array of objects where each entry's key corresponds to the name of the `.conf` file and each entry's value contains a mapping of `directory` and `contents`. Files will be created in the directory specified in `directory` or the default directory (`/opt/splunk/etc/system/local`) if not provided. `content` accepts a dictionary where keys are section names and values are key-value pairs to be listed in the configuration file.
  
The following example generates `user-prefs.conf` in `/opt/splunk/etc/users/admin/user-prefs/local`
```
splunk:
  conf:
    - key: user-prefs
      value: 
        directory: /opt/splunk/etc/users/admin/user-prefs/local
        content:
          general:
            default_namespace : appboilerplate
            search_use_advanced_editor : true
            search_line_numbers : false
            search_auto_format : false
            search_syntax_highlighting : dark
```

```
[general]
default_namespace = appboilerplate
search_use_advanced_editor = true
search_line_numbers = false
search_auto_format = false
search_syntax_highlighting = dark
```

**NOTE:** The above `splunk.conf` was changed to accept an array data-type. This array input is only applicable for recent versions of `splunk-ansible`. If you are using any of the git-tagged versions `<= 8.0.2, <= 7.3.5, <= 7.2.9` (which directly map to any of the Docker-based `splunk/splunk` images), you must use the former dictionary data-type. An example of this is shown below:
```
splunk:
  conf:
    user-prefs:
      directory: /opt/splunk/etc/users/admin/user-prefs/local
      content:
        general:
          default_namespace : appboilerplate
          search_use_advanced_editor : true
          search_line_numbers : false
          search_auto_format : false
          search_syntax_highlighting : dark
```

Any recent versions of `splunk-ansible` should still support this map type, however it is strongly recommended you move to the array type for future support.

---

## Example

The following is used in the quickstart section to start Splunk in a standalone mode, using the Splunk installation provided in /tmp/splunk.tgz

```
---
ansible_post_tasks: null
ansible_pre_tasks: null
hide_password: false
retry_delay: 3
retry_num: 60
wait_for_splunk_retry_num: 60
shc_sync_retry_num: 60
splunk_home_ownership_enforcement: true

config:
  baked: default.yml
  defaults_dir: /tmp/defaults
  env:
    headers: null
    var: SPLUNK_DEFAULTS_URL
    verify: true
  host:
    headers: null
    url: null
    verify: true
  max_delay: 60
  max_retries: 3
  max_timeout: 1200

splunk:
  role: splunk_standalone
  upgrade: false
  build_location: /tmp/splunk.tgz
  apps_location: null
  license_uri: null
  admin_user: admin
  app_paths:
    default: /opt/splunk/etc/apps
    deployment: /opt/splunk/etc/deployment-apps
    httpinput: /opt/splunk/etc/apps/splunk_httpinput
    idxc: /opt/splunk/etc/master-apps
    shc: /opt/splunk/etc/shcluster/apps
  enable_service: false
  exec: /opt/splunk/bin/splunk
  group: splunk
  hec:
    enable: True
    ssl: True
    port: 8088
    token: 4a8a737d-5452-426c-a6f7-106dca4e813f
  home: /opt/splunk
  http_enableSSL: 0
  http_enableSSL_cert: null
  http_enableSSL_privKey: null
  http_enableSSL_privKey_password: null
  http_port: 8000
  idxc:
    enable: false
    label: idxc_label
    replication_factor: 3
    replication_port: 9887
    search_factor: 3
    secret: dmwHG97SpM+GzeGPUELwr7xXowSAVmLW
  ignore_license: false
  license_download_dest: /tmp/splunk.lic
  opt: /opt
  password: helloworld
  pid: /opt/splunk/var/run/splunk/splunkd.pid
  s2s_enable: true
  s2s_port: 9997
  search_head_captain_url: null
  secret: null
  shc:
    enable: false
    label: shc_label
    replication_factor: 3
    replication_port: 9887
    secret: EpcUlTUHMSOhdjRZb3QqPYf9Lf7L991c
  smartstore: null
  svc_port: 8089
  tar_dir: splunk
  user: splunk
  wildcard_license: false
```
