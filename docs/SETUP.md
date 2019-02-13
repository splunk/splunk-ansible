## Install ##

This codebase is meant to be used in-place, however there are cases where you would want to embed the entire set of Ansible playbooks into an application itself.

In order to run Ansible and use these plays, you'll need the following prerequisites installed on the Ansible controller (host machine running the `ansible-playbook` command):
1. Linux-based operating system (Debian, CentOS, etc.)
2. Python 2 interpreter
3. System utilities:
    * `openssh-client` (this is not needed if you play to use the [local connection](https://docs.ansible.com/ansible/latest/user_guide/playbooks_delegation.html#local-playbooks))
    * `ansible` (this can also be installed via Python's package manager `pip`)

In addition to the prerequisites for the host machine, you'll also need to ensure the following dependencies are available on each instance you wish to provision and deploy as a full-fledged Splunk installation:
1. Linux-based operating system (Debian, CentOS, etc.)
2. Python 2 interpreter
3. System utilities:
    * `openssh-server` (this is not needed if you play to use the [local connection](https://docs.ansible.com/ansible/latest/user_guide/playbooks_delegation.html#local-playbooks))
    * `ps`
    * `wget`
    * `netstat`
    * `curl`
    * `sudo` 
    * `ping`
    * `nslookup`
4. PyPI packages:
    * `pip`
    * `requests`

Lastly, on each of the instances you plan on running Splunk, be mindful of the hardware and system requirements for each role in your deployment's topology. Splunk's hardware and capacity recommendations can be found [here](https://docs.splunk.com/Documentation/Splunk/7.2.4/Installation/Systemrequirements).


## Configure ##

Before we can run Ansible, we need to tell it what hosts to act against, as well as tune how Splunk gets set up!

Let's start with determining a host to run against. For the purposes of bringing up an ephemeral target host, we'll use [Docker](https://www.docker.com/) and stand up the image [`splunk/splunk`](https://hub.docker.com/r/splunk/splunk/) as such:
```
$ docker run -d --name splcontainer -p 8000:8000 splunk/splunk no-provision
```

To confirm that this above host started properly, we should be able to reach it via Ansible. Let's generate an inventory file as so, then ping it:
```
$ cat << EOF >> hosts
splcontainer ansible_connection=docker
EOF

$ ansible -i hosts splunk -m ping
[WARNING]: log file at /opt/container_artifact/ansible.log is not writeable and we cannot create it, aborting

splunk | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

Next, we'll need to generate all the variables necessary to setup Splunk. The easiest way to do this is to again use the `splunk/splunk` image with the `create-defaults` argument. For the sake of this demo, we're going to install Splunk from a URL:
```
$ BUILD=https://download.splunk.com/products/splunk/releases/7.2.4/linux/splunk-7.2.4-8a94541dcfac-Linux-x86_64.tgz
$ PASSWORD=helloworld
$ docker run -it --rm -e SPLUNK_PASSWORD=$PASSWORD -e SPLUNK_BUILD_URL=$BUILD splunk/splunk create-defaults > vars.yml
```

## Run ##

If you've followed the examples above, you should be able to run the following command:
```
$ ansible-playbook --inventory hosts site.yml --extra-vars "@vars.yml"
```

Breaking down what this does:
1. Invoking the `ansible-playbook` command with the master playbook `site.yml`
2. Pass in what target hosts you want to provision with `--inventory hosts`
3. Supply variables that control how Splunk is started with `--extra-vars "@vars.yml"`

Let the magic happen, and if everything provisions successfull you should notice:
```
PLAY RECAP ****************************************************************
splunk                     : ok=29   changed=2    unreachable=0    failed=0
```
__NOTE:__ The `ok`/`changed` count may change over time, but primarily important that `failed=0`.

You've successfully used `splunk-ansible`! If everything went smoothly, you should be able to log into Splunk with your browser pointed to `http://localhost:8000` using the credentials `admin/helloworld`.
