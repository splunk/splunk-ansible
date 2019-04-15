## Navigation

* [Inventory Script](#inventory-script)
    * [Environment variables for Splunk instance](#environment-variables-for-splunk-instance)
    * [Additional environment variables for Splunk universal forwarder](#additional-environment-variables-for-splunk-universal-forwarder)
* [Defaults](#defaults)
    * [Loading defaults through file](#loading-defaults-through-file)
    * [Loading defaults through URL](#loading-defaults-through-url)
    * [Schema](#schema)
* [Apps](#app)
* [SmartStore](@smartstore)
* [Defaults](#defaults)

---

## Inventory Script
Splunk-Ansible ships with an inventory script under `inventory/environ.py'. Environ.py is responsible for gathering user configurations from a local yaml file and/or os environment variables. Then, environ.py converts gathered configurations into Ansible variables that are accessible in Ansible tasks.

Below is the list of all environment variables that the inventory script can work with.

#### Environment variables for Splunk instance

| Environment Variable Name | Description | Required for Standalone | Required for Search Head Clustering | Required for Index Clustering |
| --- | --- | --- | --- | --- |
| SPLUNK_BUILD_URL | URL to Splunk build where we can fetch a Splunk build to install | no | no | no |
| SPLUNK_DEFAULTS_URL | default.yml URL | no | no | no |
| SPLUNK_ALLOW_UPGRADE | If this is True (default), we compare the target build version against the current installed one, and perform an upgrade if they're different. | no | no | no |
| SPLUNK_ROLE | Specify the container’s current Splunk Enterprise role. Supported Roles: splunk_standalone, splunk_indexer, splunk_deployer, splunk_search_head, etc. | no | yes | yes |
| DEBUG | Print Ansible vars to stdout (supports Docker logging) | no | no | no |
| SPLUNK_START_ARGS | Accept the license with “—accept-license”. Please note, we will not start a container without the existence of --accept-license in this variable. | yes | yes | yes |
| SPLUNK_LICENSE_URI | URI we can fetch a Splunk Enterprise license. This can be a local path or a remote URL. | no | no | no |
| SPLUNK_STANDALONE_URL | List of all Splunk Enterprise standalone hosts (network alias) separated by comma | no | no | no |
| SPLUNK_SEARCH_HEAD_URL | List of all Splunk Enterprise search head hosts (network alias) separated by comma | no | yes | yes |
| SPLUNK_INDEXER_URL| List of all Splunk Enterprise indexer hosts (network alias) separated by comma | no | yes | yes |
| SPLUNK_HEAVY_FORWARDER_URL | List of all Splunk Enterprise heavy forwarder hosts (network alias) separated by comma | no | no | no |
| SPLUNK_DEPLOYER_URL | One Splunk Enterprise deployer host (network alias) | no | yes | no |
| SPLUNK_CLUSTER_MASTER_URL | One Splunk Enterprise cluster master host (network alias) | no | no | yes |
| SPLUNK_SEARCH_HEAD_CAPTAIN_URL | One Splunk Enterprise search head host (network alias). Passing this ENV variable will enable search head clustering. | no | yes | no |
| SPLUNK_DEPLOYMENT_SERVER | One Splunk host (network alias) that we use as a [deployment server](http://docs.splunk.com/Documentation/Splunk/latest/Updating/Configuredeploymentclients) | no | no | no |
| SPLUNK_ADD | List of items to add to monitoring separated by comma. Example, SPLUNK_ADD=udp 1514,monitor /var/log/\*. This will monitor udp 1514 port and /var/log/\* files. | no | no | no |
| SPLUNK_BEFORE_START_CMD | List of commands to run before Splunk starts separated by comma. Ansible will run “{{splunk.exec}} {{item}}”. | no | no | no |
| SPLUNK_S2S_PORT | Default Forwarding Port | no | no | no |
| SPLUNK_SVC_PORT | Default Admin Port | no | no | no |
| SPLUNK_PASSWORD* | Default password of the admin user| yes | yes | yes |
| SPLUNK_HEC_TOKEN | HEC (HTTP Event Collector) Token when enabled | no | no | no |
| SPLUNK_SHC_SECRET | Search Head Clustering Shared secret | no | yes | no |
| SPLUNK_IDXC_SECRET | Indexer Clustering Shared Secret | no | no | yes |
| NO_HEALTHCHECK | Disable the Splunk healthcheck script | no | no | yes |
| STEPDOWN_ANSIBLE_USER | Removes Ansible user from the sudo group when set to true. This means that no other users than root will have root access. | no | no | no |
| SPLUNK_HOME_OWNERSHIP_ENFORCEMENT | Recursively enforces ${SPLUNK_HOME} to be owned by the user "splunk". Default value is true. | no | no | no |
| HIDE_PASSWORD | Set to true to hide all Ansible task logs with Splunk password in them in order to secure our output to stdout. | no | no | no |
| JAVA_VERSION | Supply "oracle:8", "openjdk:8", or "openjdk:11" to install a respective Java distribution. | no | no | no |
| SPLUNK_TAIL_FILE | Determine which file gets written to the container's stdout (default: splunkd_stderr.log) | no | no | no |

* Password must be set either in default.yml or as the environment variable `SPLUNK_PASSWORD`

#### Additional environment variables for Splunk universal forwarder

The `splunk/universalforwarder` image accepts the majority* environment variables as the `splunk/splunk` image above. However, there are some additional ones that are specific to the Universal Forwarder.

* **Note:** Specifically for the `splunk/universalforwarder` image, the environment variable `SPLUNK_ROLE` will by default be set to `splunk_universal_forwarder`. This image cannot accept any other role, and should not be changed (unlike its `splunk/splunk` image counterpart).

| Environment Variable Name | Description | Required for Standalone | Required for Search Head Clustering | Required for Index Clustering |
| --- | --- | --- | --- | --- |
| SPLUNK_CMD | List of commands to run after Splunk starts separated by comma. Ansible will run “{{splunk.exec}} {{item}}”. | no | no | no |

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

##### Loading defaults through URL
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

##### Schema
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

---

## SmartStore
TODO
