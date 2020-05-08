# Execution

The Ansible plays in the `splunk-ansible` project can be run in two ways: separately on each instance/host of the Splunk Enterprise deployment, or through more traditional separation of control nodes and managed nodes. In the first method each host asynchronously sets itself up using Ansible roles to form the final desired topology which is most clearly displayed through the [docker-splunk](https://github.com/splunk/docker-splunk) project. All execution methods are listed below.

--- 

## Navigation

* [Local](#local)
* [Embedded](#embedded)
* [Remote](#remote)

---

## Local
Local connection is the intended mode of using `splunk-ansible`. The dynamic inventory script `environ.py` reads environment variables and maps them into Ansible run-time variables that determine how Splunk Enterprise is setup. 

In order to bring up the most basic Splunk standalone instance on a local host, you can run the following:

```bash
export SPLUNK_PASSWORD=helloworld
export SPLUNK_BUILD_URL=https://download.splunk.com/products/splunk/releases/8.0.3/linux/splunk-8.0.3-a6754d8441bf-Linux-x86_64.tgz
export SPLUNK_USER=$(whoami)
export SPLUNK_GROUP=$(id -gn)

ansible-playbook --inventory inventory/environ.py --limit localhost site.yml
```

---

## Embedded
The embedded, or wrapper, mode of using `splunk-ansible` involves treating this entire project as a package. See [these instructions](wrapper-example/README.md) on how to install `splunk-ansible` on multiple target machines to bring up an indexer cluster.

---

## Remote
The more traditional and familiar approach to running Ansible can also be used with `splunk-ansible`. This fits the use-case where `splunk-ansible` is installed on some controller node (ex. your personal workstation, Ansible Tower, or Ansible AWX) and this controller uses the ssh connection to setup Splunk on a series of target hosts. 

See [these instructions](remote/README.md) on how to install `splunk-ansible` on multiple target machines to bring up an indexer cluster.
