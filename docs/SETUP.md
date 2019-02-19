## Navigation

* [Install](#install)
* [Configure](#configure)
* [Run](#run)
* [Summary](#summary)

----

## Install

This codebase is meant to be used via local connection, which brings up the node you run the `ansible-playbook` command on as a full-fledged Splunk instance. This does require you to embed this entire set of Ansible playbooks into the infrastructure layer itself. While it is entirely possible to provision a remote instance using these same plays, we do not officially support this.

In order to run Ansible and use these plays, you'll need the following prerequisites and dependencies installed on the node you wish to deploy as a Splunk installation:
1. Linux-based operating system (Debian, CentOS, etc.)
2. Python 2 interpreter
3. System utilities:
    * `rsync`
    * `tar`
    * `ps`
    * `wget`
    * `netstat`
    * `curl`
    * `sudo` 
    * `ping`
    * `nslookup`
    * `ansible` (this can also be installed via Python's package manager `pip`)
4. PyPI packages:
    * `pip`
    * `requests`
5. Users/groups:
    * `splunk/splunk`
    * `ansible/ansible` with sudo access
    * `root/root`

Be mindful of the hardware and system requirements for each role in your deployment's topology. For more information, please see [Splunk's hardware and capacity recommendations](https://docs.splunk.com/Documentation/Splunk/7.2.4/Installation/Systemrequirements).

## Configure
Before we can run Ansible, we need to tell it what hosts to act against, as well as tune how Splunk gets set up!

Let's start with standing up a host. For the purposes of bringing up an ephemeral target environment, we'll be using [Docker](https://www.docker.com/) to bring up the image [`splunk/splunk`](https://hub.docker.com/r/splunk/splunk/) as so:
```
$ docker run -d --name splcontainer -p 8000:8000 splunk/splunk no-provision
```

Next, we'll need to generate all the variables necessary to setup Splunk. From here on forward, we'll call this collection of variables the `default.yml`. For the sake of simplicity, let's download the example `default.yml` supplied [here](advanced/default.yml.spec.md#sample).

Feel free to inspect your newly-created `default.yml` and tweak options as you see fit. For a full list of options, please see the [`default.yml.spec`](advanced/default.yml.spec.md#spec).

## Run
In order to get your container to run Ansible, we'll need to give it all the playbooks. This Docker image conveniently has our playbooks already, but for the sake of experimentation let's dump everything into a new location:
```
$ docker cp . splcontainer:/tmp/splunk-ansible/
```

If you've followed all of the directions above, you should be able to run the following command
```
$ docker exec -it splcontainer bash -c 'cd /tmp/splunk-ansible; ansible-playbook --connection local site.yml --extra-vars "@default.yml"'
```

Breaking down what this does:
1. Invoking the `ansible-playbook` command with the master playbook `site.yml`
2. Use the connection plugin to run locally with `--connection local`
3. Supply variables that control how Splunk is started with `--extra-vars "@default.yml"`

Let the magic happen, and if everything provisions successfully you will see:
```
PLAY RECAP ****************************************************************
splunk                     : ok=29   changed=2    unreachable=0    failed=0
```
__NOTE:__ The `ok`/`changed` count may change over time, but it's vital to see `failed=0` if everything went well.

## Summary
You've successfully used `splunk-ansible`! If everything went smoothly, you can login to Splunk with your browser pointed at `http://localhost:8000` using the credentials `admin/helloworld`.

Ready for more? Now that your feet are wet, go learn more about the [design and architecture](ARCHITECTURE.md) of these plays or play around with more [advanced scenarios](ADVANCED.md).
