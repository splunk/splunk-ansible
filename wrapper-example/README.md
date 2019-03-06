This folder provides guiendence in how to use splunk-ansible in your own environment.  The examples here setup a very
 basic container, that only exposes port 22 and has NOTHING preinstalled (not even ansible). You can follow this exact workflow with 4 baremetal machines.
 
 In this case, first we'll spin up 4 containers to mimic our base baremetal hosts with ssh installed.

First build the container image:
```
cd wrapper-example
docker build -t debian_buster_sshd .
```
Then start up the 4 copies:
```
docker run -d -P --name cluster_master debian_buster_sshd
docker run -d -P --name indexer1 debian_buster_sshd
docker run -d -P --name indexer2 debian_buster_sshd
docker run -d -P --name indexer3 debian_buster_sshd
```
Verify they are all running with docker ps:
```
wrapper-example$ docker ps

CONTAINER ID        IMAGE                COMMAND               CREATED             STATUS              PORTS                   NAMES
83b7ca4b553b        debian_buster_sshd   "/usr/sbin/sshd -D"   5 minutes ago       Up 5 minutes        0.0.0.0:32775->22/tcp   indexer3
fc6ecad25d9b        debian_buster_sshd   "/usr/sbin/sshd -D"   5 minutes ago       Up 5 minutes        0.0.0.0:32774->22/tcp   indexer2
146859678bd2        debian_buster_sshd   "/usr/sbin/sshd -D"   5 minutes ago       Up 5 minutes        0.0.0.0:32773->22/tcp   indexer1
a265a4805600        debian_buster_sshd   "/usr/sbin/sshd -D"   6 minutes ago       Up 6 minutes        0.0.0.0:32772->22/tcp   cluster_master
```

Next we'll copy our target key in for passwordless login:

```
ssh-copy-id -i ~/.ssh/mykey root@0.0.0.0 -p <port>
```
Make sure to do the above command for all 4 servers.

Now lets build an ansible inventory to work with our 4 hosts, I personally am using the yaml version, but you can build your inventory
however you'd like.  See: https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html.  I've attached the sample
inventory, ansible_inventory.yaml.sample

```
$vi ansible_inventory.yaml

all:
  vars:
    ansible_user: root
  children:
    splunk_cluster_master:
      hosts:
        cluster_master:
          ansible_port: 32776
          ansible_host: 0.0.0.0
    splunk_indexer:
      hosts:
        indexer1:
          ansible_port: 32777
          ansible_host: 0.0.0.0
        indexer2:
          ansible_port: 32778
          ansible_host: 0.0.0.0
        indexer3:
          ansible_port: 32779
          ansible_host: 0.0.0.0
```

We're now ready to test our first run.  Let's test this with the hello-world.playbook:

```
$ ansible-playbook -vv -i ansible_inventory.yaml hello-world.playbook
```

This playbook will install a simple python-minimal instance, and then send "echo hello_world" to the command line, and store
the output in a registered var.  By running with -vv on ansible-playbook, we'll be able to see that register in the task:
```
TASK [echo hello_world on each host] ****************************************************************************************************************************************************************
task path: /Projects/splunk-ansible/wrapper-example/hello-world.playbook:13
changed: [indexer3] => {"changed": true, "cmd": ["echo", "hello_world"], "delta": "0:00:00.002486", "end": "2019-03-05 20:41:17.468653", "rc": 0, "start": "2019-03-05 20:41:17.466167", "stderr": "", "stderr_lines": [], "stdout": "hello_world", "stdout_lines": ["hello_world"]}
changed: [indexer1] => {"changed": true, "cmd": ["echo", "hello_world"], "delta": "0:00:00.002334", "end": "2019-03-05 20:41:17.468749", "rc": 0, "start": "2019-03-05 20:41:17.466415", "stderr": "", "stderr_lines": [], "stdout": "hello_world", "stdout_lines": ["hello_world"]}
changed: [cluster_master] => {"changed": true, "cmd": ["echo", "hello_world"], "delta": "0:00:00.002773", "end": "2019-03-05 20:41:17.480882", "rc": 0, "start": "2019-03-05 20:41:17.478109", "stderr": "", "stderr_lines": [], "stdout": "hello_world", "stdout_lines": ["hello_world"]}
changed: [indexer2] => {"changed": true, "cmd": ["echo", "hello_world"], "delta": "0:00:00.003453", "end": "2019-03-05 20:41:17.484681", "rc": 0, "start": "2019-03-05 20:41:17.481228", "stderr": "", "stderr_lines": [], "stdout": "hello_world", "stdout_lines": ["hello_world"]}
```

As long as the hello_world example had no failures, we're now ready to setup this index cluster.  Please setup a defaults.yml file (referenced in the docs)
and place it inside of our current working directory, next to the playbooks.  In the example below, I'm just going to use the
auto-generated defaults off of the splunk container to get started.

```
docker run --rm -it splunk/splunk:latest create-defaults > default.yml
```

The supplied play will setup all of 
the required prereqs for splunk-ansible, copy the defaults file to /tmp/defaults/default.yml, and then will download splunk and configure
the entire index cluster.

```
ansible-playbook -vv -i ansible_inventory.yaml install-splunk.playbook
```