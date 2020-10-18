## Navigation

* [Install Splunk-Ansible](#install-splunk-ansible)
* [Configure parameters](#configure-parameters)
* [Execute playbooks](#execute-playbooks)
* [See also](#see-also)

----

## Install Splunk-Ansible
The playbooks of Splunk-Ansible are executed through a local connection. You should run the `ansible-playbook` command on the node you wish to bring up as a fully-fledged Splunk Enterprise instance. Accordingly, this means the contents of this repository must be packaged into the infrastructure layer itself.

While it can be possible to provision a remote instance using these same playbooks, we do not officially support this.

#### Requirements
In order to run Ansible and use these plays, you need to install the following dependencies on the host you want to deploy as a Splunk Enterprise installation:
* Linux-based operating system (Debian, CentOS, etc.)
* Python 2 interpreter
* System utilities:
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
* PyPI packages:
    * `pip`
    * `requests`
* Users/groups:
    * `splunk/splunk`
    * `ansible/ansible` with sudo access
    * `root/root`

Be mindful of the different hardware and system requirements for each node in your Splunk Enterprise deployment. For more information, see [Splunk Enterprise recommended hardware](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements#Recommended_hardware) guidelines.

## Configure parameters
Before you run Ansible, you need to tell it what hosts to act against, as well as tune how Splunk Enterprise gets set up!

1. Start with standing up a host. For the purposes of bringing up an ephemeral target environment, we'll be using [Docker](https://www.docker.com/) to bring up the image [`splunk/splunk:latest`](https://hub.docker.com/r/splunk/splunk/) as so:
```
$ docker run -d --name splcontainer -p 8000:8000 splunk/splunk:latest no-provision
```

2. Next, you must generate all the variables necessary to setup Splunk Enterprise. From here on forward, this collection of variables will be known as the `default.yml`. The [`splunk/splunk:latest`](https://hub.docker.com/r/splunk/splunk/) Docker image can also be used to generate these variables:
```
$ docker run -it splunk/splunk:latest create-defaults > default.yml
```
Alternatively, you can download the example `default.yml` supplied [here](advanced/default.yml.spec.md#sample).

3. Define a few key variables in your `default.yml`:
* `splunk.role`: the role this instance will play in the Splunk Enterprise deployment. (e.g. `splunk_standalone`)
* `splunk.build_location`: URL to dynamically fetch the Splunk Enterprise build and install it at run time
* `splunk.password`: default `admin` user password that Splunk will be provisioned with on first-time run

4. Inspect your newly-created `default.yml` and tweak options as you see fit. For a full list of parameters, please see the [`default.yml.spec`](advanced/default.yml.spec.md#spec).

## Execute playbooks
In order to get your container to run Ansible, it needs a copy of all the playbooks. 

1. If you're using the `splunk/splunk` Docker image, it conveniently already has all of the playbooks available - but for the sake of this exercise, copy everything in this repo into your remote host which is the container:
```
$ docker cp . splcontainer:/tmp/splunk-ansible/
```

2. Run the following command
```
$ docker exec -it splcontainer bash -c 'cd /tmp/splunk-ansible; ansible-playbook --inventory localhost, --connection local site.yml --extra-vars "@default.yml"'
```
You should see streaming Ansible output in your terminal. Here is what is happening when you run the above command:
* `ansible-playbook` command is invoked using the playbook `site.yml`
* The local connection plugin is explicitly used with `--connection local`
* Splunk Enterprise is configured towards your desired state as defined in `--extra-vars "@default.yml"`

3. If everything went smoothly, you can log in to Splunk Enterprise with your browser pointed at `http://localhost:8000` using the credentials `admin/helloworld`. Additionally, Ansible should exit gracefully and you will the following if there are no errors:
```
PLAY RECAP ****************************************************************
splunk                     : ok=29   changed=2    unreachable=0    failed=0
```
**NOTE:** The `ok`/`changed` count may change over time, but it's vital to see `failed=0` if everything went well.

## See also

* [More examples](EXAMPLES.md)
* [Architecture of Splunk-Ansible](ARCHITECTURE.md)
* [Adding advanced configuration](ADVANCED.md)
