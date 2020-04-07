## Navigation

* [Spec](#spec)
  * [Configuration files](#configuration-files)
* [Example](#example)

---

## Spec
The following is the full spec file for a `default.yml` that controls how Splunk gets provisioned.

```
ansible_post_tasks: <str>
* Comma-separated list of paths or URLs to custom Ansible playbooks to run AFTER Splunk has been setup using the provided site.yml
* Default: null

ansible_pre_tasks: <str>
* Comma-separated list of paths or URLs to custom Ansible playbooks to run BEFORE Splunk sets up using the provided site.yml
* Default: null

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

splunk:
  role: <str>
  * Role to assume when setting up Splunk
  * Default: splunk_standalone

  upgrade: <bool>
  * Determines whether or not to perform an upgrade (to the splunk.build_location)
  * Default: false

  build_location: <str>
  * Splunk build location, either on the filesystem or a remote URL
  * Default: /tmp/splunk.tgz

  license_master_url: <str>
  * Hostname of Splunk Enterprise license master instance. May be overridden using SPLUNK_LICENSE_MASTER_URL environment variable.
  * Default: null

  cluster_master_url: <str>
  * Hostname of Splunk Enterprise cluster master instance. May be overridden using SPLUNK_CLUSTER_MASTER_URL environment variable.
  * Default: null
  
  deployer_url: null
  * Hostname of Splunk Enterprise deployer instance. May be overridden using SPLUNK_DEPLOYER_URL environment variable.
  * Default: null

  search_head_captain_url: null
  * Hostname of Splunk Enterprise search head cluster captain instance. May be overridden using SPLUNK_SEARCH_HEAD_CAPTAIN_URL environment variable.
  * Default: null

  search_head_cluster_url: null
  * URL of the Splunk search head cluster
  * NOTE: This is being deprecated in favor of `splunk.search_head_captain_url`.
  * Default: null

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
  * Default admin-level user to run provisioning commands under
  * Default: admin

  password: <str>
  * Default Splunk admin user password. This is REQUIRED when starting Splunk
  * Default: null

  user: <str>
  * Host user under which Splunk will run
  * Default: splunk

  group: <str>
  * Host group under which Splunk will run
  * Default: splunk

  enable_service: <bool>
  * Determine whether or not to enable Splunk for boot-start (start via sysinitv or systemd, etc.)
  * Default: false

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

  launch: null
  * key::value pairs for environment variables that get written to ${SPLUNK_HOME}/etc/splunk-launch.conf
  * Default: null

  secret: <str>
  * Secret passcode used to encrypt all of Splunk's sensitive information on disk. When not set, Splunk will autogenerate a unique secret local to each installation. This is NOT required for any standalone or distributed Splunk topology
  * NOTE: This may be set once at the start of provisioning any deployment. Any changes made to this splunk.secret after the deployment has been created must be resolved manually, otherwise there is a severe risk of bricking the capabilities of your Splunk environment.
  * Default: null

  pass4SymmKey: <str>
  * Password for Symmetric Key used to encrypt Splunk's sensitive information on disk. When not set, Splunk will encrypt a default value (`changeme`) with `splunk.secret` and set it as `pass4SymmKey` in the `[general]` stanza of `/opt/splunk/etc/system/local/server.conf`.
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
  
  conf: <dict>
    (filename):
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

`conf` accepts a dictionary where keys are names of `.conf` files and values contain the `directory` and `contents`. Files will be created in the directory specified in `directory` or the default directory (`/opt/splunk/etc/system/local`) if none are provided. `content` accepts a dictionary where keys are section names and values are key-value pairs to be listed in the configuration file.
  
  
The following example generates `user-prefs.conf` in `/opt/splunk/etc/users/admin/user-prefs/local`
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

```
[general]
default_namespace = appboilerplate
search_use_advanced_editor = true
search_line_numbers = false
search_auto_format = false
search_syntax_highlighting = dark
```

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
