## Examples

The purpose of this section is to showcase a wide variety of examples on how `splunk-ansible` can be used. Please use the files and content here as simple references designs for implementing and getting immediate value out of the playbooks in this repository.

From a design perspective, the plays within `splunk-ansible` are meant to be run locally on each instance of your intended Splunk deployment. The execution flow of the provisioning process is meant to gracefully handle interoperability in this manner, while also maintaining idempotency and configuration management. It is also possible to use these plays against a remote instance, although that is not the intended use case so it might not work in all cases.

----

## I want to...

* [Provision localhost as a standalone Splunk](#provision-local-standalone)
* [Enable a user-defined HEC token](#provision-hec)
* [Use a dynamic inventory](#provision-with-dynamic-inventory)
* [Provision Docker containers with splunk-ansible](#provision-docker-containers)

---

## Provision local standalone
<details><summary>"hosts" file inventory</summary><p>
```
localhost ansible_connection=local
```
</p></details>

<details><summary>"default.yml" contents</summary><p>
```
---
ansible_post_tasks: null
ansible_pre_tasks: null
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
hide_password: false
retry_num: 50
shc_bootstrap_delay: 30
splunk:
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
hec_disabled: 1
hec_enableSSL: 1
hec_port: 8088
hec_token: null
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
    secret: null
ignore_license: false
license_download_dest: /tmp/splunk.lic
nfr_license: /tmp/nfr_enterprise.lic
opt: /opt
password: helloworld
pid: /opt/splunk/var/run/splunk/splunkd.pid
s2s_enable: true
s2s_port: 9997
search_head_cluster_url: null
secret: null
shc:
    enable: false
    label: shc_label
    replication_factor: 3
    replication_port: 9887
    secret: null
smartstore: null
svc_port: 8089
tar_dir: splunk
user: splunk
wildcard_license: false
splunk_home_ownership_enforcement: true
```
</p></details>

Execution command:
```
ansible-playbook --inventory hosts --connection local site.yml --extra-vars "@default.yml" 
```

---

## Provision HEC
The HTTP Event Collector (HEC) enables sending data directly to Splunk via a HTTP endpoint and a token. Here's how you can enable it with a user-defined token (`abcd-1234-efgh-5678`).
<details><summary>"hosts" file inventory</summary><p>
```
localhost ansible_connection=local
```
</p></details>

<details><summary>"default.yml" contents</summary><p>
```
---
ansible_post_tasks: null
ansible_pre_tasks: null
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
hide_password: false
retry_num: 50
shc_bootstrap_delay: 30
splunk:
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
hec_disabled: 0
hec_enableSSL: 1
hec_port: 8088
hec_token: abcd-1234-efgh-5678
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
    secret: null
ignore_license: false
license_download_dest: /tmp/splunk.lic
nfr_license: /tmp/nfr_enterprise.lic
opt: /opt
password: helloworld
pid: /opt/splunk/var/run/splunk/splunkd.pid
s2s_enable: true
s2s_port: 9997
search_head_cluster_url: null
secret: null
shc:
    enable: false
    label: shc_label
    replication_factor: 3
    replication_port: 9887
    secret: null
smartstore: null
svc_port: 8089
tar_dir: splunk
user: splunk
wildcard_license: false
splunk_home_ownership_enforcement: true
```
</p></details>

Execution command:
```
ansible-playbook --inventory hosts --connection local site.yml --extra-vars "@default.yml" 
```

For this case, please take note that the `hec_enableSSL` parameter will govern whether or not the HEC endpoint will be reachable over HTTP or HTTPS.

---

## Provision with Dynamic Inventory
Ansible enables the use of custom inventory scripts. For more information on how to do this and how to create your own inventory script, please go to Ansible's documentation on dynamic inventories.

This codebase includes an example of this, located at `inventory/environ.py`. This script is meant for the local connection use, and is the primary driver in making Splunk's official Docker image successful. The `environ.py` converts environment variables into Ansible variables dynamically so there's no need for the `default.yml` from previous examples. However, in some cases, the `default.yml` is still necessary in order to consolidate state across multiple instances of a distributed deployment.

Execution command:
```
ansible-playbook --inventory inventory/environ.py --connection local site.yml
```

---

## Provision Docker Containers
The playbooks in this repository are already being used in the context of containers! For more information on how this works, please see the [docker-splunk](https://github.com/splunk/docker-splunk/) project and learn how `splunk-ansible` is incorporated.

---
