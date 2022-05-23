## Navigation

* [Inventory Script](#inventory-script)
    * [Supported environment variables](#supported-environment-variables)
    * [Additional Splunk Universal Forwarder variables](#additional-splunk-universal-forwarder-variables)
* [Defaults](#defaults)
    * [Loading defaults through file](#loading-defaults-through-file)
    * [Loading defaults through URL](#loading-defaults-through-url)
    * [Schema](#schema)
* [Apps](#apps)
* [SmartStore](#smartstore)
* [Custom splunk-launch.conf](#custom-splunk-launchconf)
* [Multi-cluster Search](#multi-cluster-search)

---

## Inventory Script
Splunk-Ansible ships with an inventory script in `inventory/environ.py`. The script gathers user configurations from a local YAML file and/or OS environment variables and converts them into Ansible variables accessible in Ansible tasks.

### Supported environment variables

| Environment Variable Name | Description | Required for Standalone | Required for Search Head Clustering | Required for Index Clustering |
| --- | --- | --- | --- | --- |
| SPLUNK_BUILD_URL | URL of Splunk build to be installed | no | no | no |
| SPLUNK_DEFAULTS_URL | URL of `default.yml` | no | no | no |
| SPLUNK_ALLOW_UPGRADE | Perform upgrade if target build version doesn't match installed version | no | no | no |
| SPLUNK_ROLE | The container’s current Splunk Enterprise role. Supported Roles: `splunk_standalone`, `splunk_indexer`, `splunk_deployer`, `splunk_search_head`, etc. See [Roles](https://github.com/splunk/splunk-ansible/tree/develop/roles). | no | yes | yes |
| SPLUNK_HOSTNAME | Specify the instance's hostname. | no | no | no |
| DEBUG | Print Ansible vars to stdout (supports Docker logging) | no | no | no |
| SPLUNK_START_ARGS | Accept the license with `—accept-license` in this variable. The container will not start without it. | yes | yes | yes |
| SPLUNK_LICENSE_URI | URI we can fetch a Splunk Enterprise license. This can be a local path, a remote URL, or ["Free"](https://docs.splunk.com/Documentation/Splunk/latest/Admin/MoreaboutSplunkFree). | no | no | no |
| SPLUNK_IGNORE_LICENSE | Flag to disable any plays that would add a license. Set this env var to "true" if you do not want to license your installation. | no | no | no |
| SPLUNK_LICENSE_INSTALL_PATH | Path on filesystem where Splunk license will be moved/downloaded to | no | no | no |
| SPLUNK_STANDALONE_URL | Comma-separated list of all Splunk Enterprise standalone hosts (network alias) | no | no | no |
| SPLUNK_SEARCH_HEAD_URL | Comma-separated list of all Splunk Enterprise search head hosts (network alias) | no | yes | yes |
| SPLUNK_INDEXER_URL| Comma-separated list of all Splunk Enterprise indexer hosts (network alias) | no | yes | yes |
| SPLUNK_HEAVY_FORWARDER_URL | Comma-separated list of all Splunk Enterprise heavy forwarder hosts (network alias) | no | no | no |
| SPLUNK_DEPLOYER_URL | One Splunk Enterprise deployer host (network alias) | no | yes | no |
| SPLUNK_CLUSTER_MASTER_URL | One Splunk Enterprise cluster master host (network alias) | no | no | yes |
| SPLUNK_SEARCH_HEAD_CAPTAIN_URL | One Splunk Enterprise search head host (network alias). Passing this ENV variable will enable search head clustering. | no | yes | no |
| SPLUNK_LICENSE_MASTER_URL | One Splunk Enterprise license master host (network alias). Passing this ENV variable will enable license master setup. | no | no | no |
| SPLUNK_DEPLOYMENT_SERVER | One Splunk host (network alias) that we use as a [deployment server](http://docs.splunk.com/Documentation/Splunk/latest/Updating/Configuredeploymentclients). | no | no | no |
| SPLUNK_ADD | Comma-separated list of items to add to monitoring. Example: `SPLUNK_ADD=udp 1514,monitor /var/log/\*`. This will monitor the UDP port 1514 and `/var/log/\*` files. | no | no | no |
| SPLUNK_BEFORE_START_CMD | Comma-separated list of commands to run before Splunk starts. Ansible will run <!-- {% raw %} -->`{{splunk.exec}} {{item}}`<!-- {% endraw %} -->. | no | no | no |
| SPLUNK_S2S_PORT | Splunk forwarding/receiving port. Default: `9997` | no | no | no |
| SPLUNK_SVC_PORT | Splunk management/administration port. Default: `8089` | no | no | no |
| SPLUNK_CERT_PREFIX | HTTP scheme used when making API requests to Splunk management endpoint. Default: `https` | no | no | no |
| SPLUNK_ROOT_ENDPOINT | Allow SplunkWeb to be accessed behind a given route (ex. reverse proxy usage) | no | no | no |
| SPLUNK_PASSWORD* | Default password of the admin user | yes | yes | yes |
| SPLUNK_DECLARATVE_ADMIN_PASSWORD | When `true`, admin password will be fixed to the value defined through Ansible | no | no | no |
| SPLUNK_PASS4SYMMKEY | Used to overwrite default `pass4SymmKey` for Splunk secrets | no | no | no |
| SPLUNK_HEC_TOKEN | HEC (HTTP Event Collector) token when enabled | no | no | no |
| SPLUNK_SHC_SECRET | Search Head Clustering shared secret (deprecated in favor of `SPLUNK_SHC_PASS4SYMMKEY`) | no | no | no |
| SPLUNK_SHC_PASS4SYMMKEY | Password for the Search Head Clustering shared secret | no | yes | no |
| SPLUNK_SHC_LABEL | Search head clustering label | no | yes | no |
| SPLUNK_SHC_REPLICATION_FACTOR | Configure search head clustering replication factor | no | no | no |
| SPLUNK_PREFERRED_CAPTAINCY | Set up search head clustering with preferred captaincy, typically pinned to the instance designated as `splunk_search_head_captain` | no | no | no |
| SPLUNK_IDXC_SECRET | Indexer Clustering shared Secret (deprecated in favor of `SPLUNK_SHC_PASS4SYMMKEY`) | no | no | no |
| SPLUNK_IDXC_PASS4SYMMKEY | Password for the Indexer Clustering shared Secret | no | no | yes |
| SPLUNK_IDXC_DISCOVERYPASS4SYMMKEY | Password for the indexer discovery shared secret | no | no | yes |
| SPLUNK_IDXC_LABEL | Indexer clustering label | no | no | yes |
| SPLUNK_IDXC_REPLICATION_FACTOR | Configure indexer clustering data replication factor | no | no | no |
| SPLUNK_IDXC_SEARCH_FACTOR | Configure indexer clustering search factor | no | no | no |
| SPLUNK_OPT | Location where Splunk Enterprise will be installed (not recommended to change). Default: `/opt` | no | no | no |
| SPLUNK_HOME | Location of Splunk Enterprise home directory (not recommended to change). Default: `/opt/splunk` | no | no | no |
| SPLUNK_EXEC | Location of Splunk Enterprise executable (not recommended to change). Default: `/opt/splunk/bin/splunk` | no | no | no |
| SPLUNK_PID | Location of Splunk Enterprise process ID file (not recommended to change). Default: `/opt/splunk/var/run/splunk/splunkd.pid` | no | no | no |
| SPLUNK_USER | User which owns the Splunk home directory and runs the splunkd process (not recommended to change). Default: `splunk` | no | no | no |
| SPLUNK_GROUP | Group which owns the Splunk home directory and runs the splunkd process (not recommended to change). Default: `splunk` | no | no | no |
| SPLUNK_PASS4SYMMKEY | Set user-defined `pass4SymmKey` in the general stanza of server.conf instead of using the Splunk default | no | no | no |
| SPLUNK_SECRET | Set user-defined `${SPLUNK_HOME}/etc/splunk.secret` instead of using the Splunk default | no | no | no |
| SPLUNK_ENABLE_SERVICE | Enable Splunk to start as a system service (`enable boot-start`) | no | no | no |
| SPLUNK_SERVICE_NAME | Define Splunk service name when set to start as a system service | no | no | no |
| SPLUNK_LAUNCH_CONF | Pass in a comma-separated list of "key=value" pairs that will get written to `${SPLUNK_HOME}/etc/splunk-launch.conf` | no | no | no |
| SPLUNK_APPS_URL | Pass in a comma-separated list of local paths or remote URLs to Splunk apps that will get installed | no | no | no |
| SPLUNKBASE_USERNAME | Splunkbase username used for authentication when installing an app from [Splunkbase](https://splunkbase.splunk.com/) | no | no | no |
| SPLUNKBASE_PASSWORD | Splunkbase password used for authentication when installing an app from [Splunkbase](https://splunkbase.splunk.com/) | no | no | no |
| SPLUNK_HTTP_PORT | Port to run SplunkWeb on. To disable SplunkWeb, set to `0`. Default: `8000` | no | no | no |
| SPLUNK_HTTP_ENABLESSL | Enable HTTPS on SplunkWeb | no | no | no |
| SPLUNK_HTTP_ENABLESSL_CERT | Path to SSL certificate used for SplunkWeb, if HTTPS is enabled | no | no | no |
| SPLUNK_HTTP_ENABLESSL_PRIVKEY | Path to SSL private key used for SplunkWeb, if HTTPS is enabled | no | no | no |
| SPLUNK_HTTP_ENABLESSL_PRIVKEY_PASSWORD | SSL certificate private key password used with SplunkWeb, if HTTPS is enabled | no | no | no |
| SPLUNKD_SSL_ENABLE | Enable HTTPS on Splunkd. By default, this is enabled out-of-the-box. To disable, set this to "false" | no | no | no |
| SPLUNKD_SSL_CERT | Path to custom SSL certificate used for Splunkd when HTTPS is enabled | no | no | no |
| SPLUNKD_SSL_CA | Path to custom CA certificate used for Splunkd when HTTPS is enabled | no | no | no |
| SPLUNKD_SSL_PASSWORD | Custom SSL password used with Splunkd when HTTPS is enabled | no | no | no |
| SPLUNK_KVSTORE_PORT | Port to run Splunk KVStore. Default: `8191` | no | no | no |
| SPLUNK_APPSERVER_PORT | Port to run Splunk appserver. Default: `8065` | no | no | no |
| SPLUNK_SET_SEARCH_PEERS | Boolean to configure whether search heads should connect to search peers. Default: `True`. Not recommended to change | no | no | no |
| SPLUNK_SITE | For multisite topologies, define the site of this particular Splunk Enterprise instance | no | no | no |
| SPLUNK_ALL_SITES | For multisite topologies, define all sites of the topology | no | no | no |
| SPLUNK_MULTISITE_MASTER | For multisite topologies, define location of the multisite cluster master | no | no | no |
| SPLUNK_MULTISITE_MASTER_PORT | For multisite topologies, define the Splunk management port of the multisite cluster master | no | no | no |
| SPLUNK_MULTISITE_REPLICATION_FACTOR_ORIGIN | For multisite topologies, define the origin replication factor | no | no | no |
| SPLUNK_MULTISITE_REPLICATION_FACTOR_TOTAL | For multisite topologies, define the total replication factor | no | no | no |
| SPLUNK_MULTISITE_SEARCH_FACTOR_ORIGIN | For multisite topologies, define the origin search factor | no | no | no |
| SPLUNK_MULTISITE_SEARCH_FACTOR_TOTAL | For multisite topologies, define the total search factor | no | no | no |
| NO_HEALTHCHECK | Disable the Splunk health check script | no | no | yes |
| STEPDOWN_ANSIBLE_USER | Removes Ansible user from the sudo group when set to true. This means that no other users than root will have root access. | no | no | no |
| SPLUNK_HOME_OWNERSHIP_ENFORCEMENT | Recursively enforces `${SPLUNK_HOME}` to be owned by the user "splunk". Default: `True` | no | no | no |
| SPLUNK_DISABLE_POPUPS | Disable pop-ups from login on home page and search app. Default: `False` | no | no | no |
| HIDE_PASSWORD | Hide all Ansible task logs containing Splunk password to secure output to `stdout`. | no | no | no |
| JAVA_VERSION | Supply `"oracle:8"`, `"openjdk:8"`, or `"openjdk:11"` to install a respective Java distribution. | no | no | no |
| JAVA_DOWNLOAD_URL | Provide a custom URL where the Java installation will be fetched| no | no | no |
| SPLUNK_TAIL_FILE | Determine which file gets written to the container's stdout (default: `splunkd_stderr.log`) | no | no | no |
| SPLUNK_ES_SSL_ENABLEMENT | When running Enterprise Security version >= 6.3.0, define ssl_enablement installation option | no | no | no |
| SPLUNK_DSP_ENABLE | Enable DSP forwarding. Default: `false` | no | no | no |
| SPLUNK_DSP_SERVER | DSP S2S forwarding endpoint | no | no | no |
| SPLUNK_DSP_CERT | DSP certificate used when forwarding | no | no | no |
| SPLUNK_DSP_VERIFY | Enable cert verification when forwarding to DSP. Default: `false` | no | no | no |
| SPLUNK_DSP_PIPELINE_NAME | Name of DSP pipeline to create/update | no | no | no |
| SPLUNK_DSP_PIPELINE_DESC | Description of DSP pipeline to create/update | no | no | no |
| SPLUNK_DSP_PIPELINE_SPEC | SPL2 specification of DSP pipeline to create/update | no | no | no |
| SPLUNK_ENABLE_DFS | Enable [Data Fabric Search (DFS)](https://docs.splunk.com/Documentation/DFS/latest/DFS/Overview) | no | no | no |
| SPLUNK_DFW_NUM_SLOTS | Maximum number of concurrent DFS searches that run on a search head cluster | no | no | no |
| SPLUNK_DFC_NUM_SLOTS | Maximum number of concurrent DFS searches that run on each search head | no | no | no |
| SPLUNK_DFW_NUM_SLOTS_ENABLED | Enables you to set the value of the field `dfw_num_slots`. | no | no | no |
| SPARK_MASTER_HOST | This setting identifies the Spark master. | no | no | no |
| SPARK_MASTER_WEBUI_PORT | Identifies the port for the Spark master web UI. | no | no | no |
| DMC_FORWARDER_MONITORING | Enables forwarder monitoring on all standalone and search head instances. Default: `False` | no | no | no |
| DMC_ASSET_INTERVAL | Cron schedule that determines how often forwarder assets are re-built. Default: `"3,18,33,48 * * * *"` = every 15 minutes) | no | no | no |
| SPLUNK_ENABLE_ASAN | Internally used trigger to handle special provisioning of debug builds of Splunk Enterprise | no | no | no |
| SPLUNK_DEFAULTS_URL | URL to a remote `default.yml` file - when fetched, this will get merged into a consolidated mapping of variables | no | no | no |
| SPLUNK_DEFAULTS_HTTP_MAX_TIMEOUT | When fetching a remote `default.yml`, specify the timeout of the request | no | no | no |
| SPLUNK_DEFAULTS_HTTP_MAX_RETRIES | When fetching a remote `default.yml`, the number of retries to make. For unlimited retries, use `-1` | no | no | no |
| SPLUNK_DEFAULTS_HTTP_MAX_DELAY | When fetching a remote `default.yml`, specify the delay between each retry | no | no | no |
| SPLUNK_DEFAULTS_HTTP_AUTH_HEADER | When fetching a remote `default.yml`, set the `Authorization` header | no | no | no |
| SPLUNK_ANSIBLE_PRE_TASKS | Pass in a comma-separated list of local paths or remote URLs to Ansible playbooks that will be executed before `site.yml`. Must include the protocol, i.e. it must match the regex `^(http\|https\|file)://.*` | no | no | no |
| SPLUNK_ANSIBLE_POST_TASKS | Pass in a comma-separated list of local paths or remote URLs to Ansible playbooks that will be executed after `site.yml`. Must include the protocol, i.e. it must match the regex `^(http\|https\|file)://.*` | no | no | no |
| SPLUNK_ANSIBLE_ENV | Pass in a comma-separated list of "key=value" pairs that will be mapped to environment variables used during `site.yml` execution. These variables are also available in ansible pre/post playbooks and can be referenced as `hostvars['localhost'].ansible_environment['key']` | no | no | no |
| SPLUNK_CONNECTION_TIMEOUT | Configures splunkdConnectionTimeout in `web.conf` with passed integer value (in seconds) | no | no | no |
| SPLUNK_ES_SSL_ENABLEMENT | Set the ssl-enablement flag in ES.  Valid values are 'auto', 'strict', and 'ignore'. Defaults to auto when present. | no | no | no |

\* Password must be set either in `default.yml` or as the environment variable `SPLUNK_PASSWORD`

#### Additional Splunk Universal Forwarder variables

The `splunk/universalforwarder` image accepts the majority* environment variables as the `splunk/splunk` image above. However, there are some additional ones that are specific to the Universal Forwarder.

\* **Note:** Specifically for the `splunk/universalforwarder` image, the environment variable `SPLUNK_ROLE` will by default be set to `splunk_universal_forwarder`. This image cannot accept any other role, and should not be changed (unlike its `splunk/splunk` image counterpart).

| Environment Variable Name | Description | Required for Standalone | Required for Search Head Clustering | Required for Index Clustering |
| --- | --- | --- | --- | --- |
| SPLUNK_CMD | Comma-separated list of commands to run after Splunk starts. Ansible will run <!-- {% raw %} -->`{{splunk.exec}} {{item}}`<!-- {% endraw %} -->. | no | no | no |

#### Suggestions for environment variables for Splunk search head cluster

For Splunk search cluster configuration, we suggest passing in the environment variables `SPLUNK_HOSTNAME` and `SPLUNK_SEARCH_HEAD_URL` with fully qualified domain names.

The dynamic inventory script will assign the value of `SPLUNK_HOSTNAME` if defined or `socket.getfqdn()` to the <!-- {% raw %} -->`{{ splunk.hostname }}`<!-- {% endraw %} --> Ansible variable, which will be used to init search head cluster member. `SPLUNK_SEARCH_HEAD_URL` will be used as the `--server_list` argument of search cluster captain bootstrap command, and it requires that each member in `--server_list` must be exactly the same as the <!-- {% raw %} -->`{{ splunk.hostname }}`<!-- {% endraw %} --> specified earlier.

To be consistent, we suggest passing in the environment variables `SPLUNK_SEARCH_HEAD_CAPTAIN_URL`, `SPLUNK_INDEXER_URL` and `SPLUNK_DEPLOYER_URL` with fully qualified domain names as well.

## Defaults
For security purposes, we do not ship with a standard `default.yml`. However, it is a required component when running these Ansible playbooks in this codebase. This file can be created manually, but for a quick shortcut you can run:
```
$ docker run -it --rm -e SPLUNK_PASSWORD=helloworld splunk/splunk create-defaults > default.yml
```
NOTE: The `default.yml` generated above may require additional, manual modifications.

For distributed Splunk topologies, there are certain configuration settings that are required to be consistent across all members of the deployment. These are settings such as administrator password, clustering labels, keys, etc. To achieve this, it is possible to source all the settings from a single `default.yml` and distribute it universally in the following manners.

#### Loading defaults through file
A static `default.yml` can be dropped on to each instance utilizing the playbooks in this repository. If you're bundling this code in a Docker image or AWS AMI, note that this will be a static configuration, such that Splunk should always spin up in the same way.

This `default.yml` file must be placed at `/tmp/defaults/default.yml`, and it must be readable to the user executing the `ansible-playbook` command. Additionally, it is also possible for certain environment variables to dynamically override settings in this `default.yml` - for more information on those environment variables, please see the [Splunk Docker image](https://github.com/splunk/docker-splunk) project.

In order for the file in `/tmp/defaults/default.yml` to be read and interpreted, it is required that the Ansible command is executed using the dynamic inventory script (`environ.py`) as so:
```
$ ansible-playbook -i inventory/environ.py ...
```

#### Loading defaults through URL
If the `default.yml` file is hosted as a static asset on some webserver, it can be retrieved using an HTTP GET request. The URL must point to a file in a proper YAML format in order for it to be used correctly. Currently, no parameters can be passed through the request. However, redirects are permitted.

To specify a URL to pull a given `default.yml`, a dummy `default.yml` can be baked into each instance ([as instructed above](#loading-defaults-through-file)) to force Ansible to dynamically pull a new one. This placeholder will simply modify the url parameter shown below:
```
config:
  baked: default.yml
  defaults_dir: /tmp/defaults
  env:
    headers: null
    var: https://webserver/path/to/default.yml
    verify: false
  host:
    headers: null
    url: null
    verify: true
  max_delay: 60
  max_retries: 3
  max_timeout: 1200
```
This will try to download the `default.yml` located at `https://webserver/path/to/default.yml` using the given `headers` and `verify` key-word arguments for each request. The download request will timeout after `max_timeout` seconds, but it will retry a maximum of `max_retries` attempts with a delay of `max_delay` in between each attempt.

To use the URL-based loading of a `default.yml`, it is required that the Ansible command is executed using the dynamic inventory script (`environ.py`) as so:
```
$ ansible-playbook -i inventory/environ.py ...
```

#### Schema
For more information on the format and options exposed in a `default.yml`, please see the [full spec](advanced/default.yml.spec.md).

---

## Apps
One of the more versatile features of the Splunk platform is the ability to extend its functionality through the use of apps and add-ons. Apps and add-ons are used heavily by customers by providing out-of-the-box solutions for targeted needs. Many of these products are internally developed and supported by Splunk itself - but an even larger offering is developed by members of the community, partners, and even open-source contributors. Many of these apps can be found on [SplunkBase](https://splunkbase.splunk.com/).

For more information on apps and add-ons, please see [Splunk's featured apps](https://www.splunk.com/en_us/products/apps-and-add-ons.html).

The Ansible playbooks provided in this repository offer the ability to perform fully-vetted app installation. To enable this, modify this section of your `default.yml` to include a list of URLs or files local to the host:
```
splunkbase_username: ...
splunkbase_password: ...
splunk:
  ...
  apps_location:
    - /tmp/app.tgz
    - http://webserver.com/path/to/splunkApp.spl
    - https://splunkbase.splunk.com/app/978/release/1.1/download
  ...
```

Note that in the above, a direct SplunkBase download link was provided. To install an app or add-on directly from SplunkBase, values for `splunkbase_username` and `splunkbase_password` must be specified in order to process licensing agreements and authentication. Additionally, the Ansible provisioning must be done using the dynamic inventory script (`environ.py`) in order to perform the authentication as so:
```
$ ansible-playbook -i inventory/environ.py ...
```

If SplunkBase apps are not specified or needed, the `splunkbase_username` and `splunkbase_password` variables should be omitted entirely.

When deploying distributed Splunk Enterprise environments, apps should be installed on the deployer, cluster master, and deployment server instances. Each of these roles will take care of bundling and pushing the apps to their respective downstream peers. Note that any configuration files in any custom app's `local` directory will *not* be sent to peers - this is in alignment with Splunk best practices around configuration management.

To install an app from elsewhere, provide a path to a compressed `splunkApp.spl` file (either through a filesystem or URL) as seen above. For proper installation, apps should be compressed using `tar` in a GNU/Linux environment, as apps compressed on OSX or other BSD-variant operating systems have been known to cause issues.

For roles that manage clusters, such as Cluster Master and SH Deployer, the apps specified in `apps_location` will be pushed to the cluster and disabled on the local CM or Deployer instance.  For apps that need to be installed locally on these instances, use the `apps_location_local` variable.  Apps specified here will not be pushed to the cluster but installed locally in the same way that apps are installed on a standalone instance.  Both `apps_location` and `apps_location_local` can be used concurrently to allow for different sets of apps to be installed locally vs. pushed to the cluster for CM and Deployer instance.  The syntax is the same as `apps_location`:
```
splunk:
  ...
  apps_location:
    - /tmp/cluster_app.tgz
  apps_location_local:
    - /tmp/local_app.tgz
    - http://webserver.com/path/to/local_auth_app.spl
  ...
```

Splunk Apps and Add-on archive files can also be extracted and installed using the `app_paths_install:` option.  This configuration will install a list of apps directly to the configure `app_paths` directory, bypassing any local install then copy to bundle directory that `apps_location` uses for cluster managing roles such as CM or Deployer.  The suported `app_paths` are default (local apps), shc, idxc, and deployment.  An example of a CM config with one local app and two cluster apps is:
```
splunk:
  ...
  app_paths_install:
    default:
      - /tmp/local_app.tgz
    idxc:
      - /tmp/cluster_app1.tgz
      - /tmp/cluster_app2.spl
  ...
```

The `shc` and `idxc` apps specified in `app_paths_install` are not installed locally so Apps that require a local installation prior to a cluster-wide implementation (such as Enterprise Security Suite) would not be support.  Those apps would still need to use the `apps_location` field for proper installation.

---

## SmartStore
SmartStore utilizes S3-compliant object storage in order to store indexed data. This is a capability only available if you're using an indexer cluster (cluster_master + indexers). For more information, please see the [blog post](https://www.splunk.com/blog/2018/10/11/splunk-smartstore-cut-the-cord-by-decoupling-compute-and-storage.html) as well as [technical overview](https://docs.splunk.com/Documentation/Splunk/latest/Indexer/AboutSmartStore).

Here's an overview of what this looks like if you want to persist *all* your indexes (default) with a SmartStore backend using the `default.yml`:
```
---
splunk:
  smartstore:
    index:
      - indexName: default
        remoteName: remote_store
        scheme: s3
        remoteLocation: <bucket-name>
        s3:
          access_key: <access_key>
          secret_key: <secret_key>
          endpoint: http://s3-us-west-2.amazonaws.com
```

---

## Custom splunk-launch.conf
`splunk-launch.conf` is a configuration file that exists in `${SPLUNK_HOME}/etc/` that has some global environment variables that are using by the `splunkd` process. You can add new variables to this file using either the `default.yml` or via environment variables.

For instance, if you want to add `OPTIMISTIC_ABOUT_FILE_LOCKING=1` to the `splunk-launch.conf`, you can use this `default.yml` as reference:
```
---
splunk:
  launch:
    OPTIMISTIC_ABOUT_FILE_LOCKING: 1
  ...
```

---

## Multi-cluster Search

See the [documentation on how multi-cluster search](advanced/MULTICLUSTERSEARCH.md) can be configured.
