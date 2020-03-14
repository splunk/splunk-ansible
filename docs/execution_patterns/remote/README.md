This folder provides guiendence in how to use splunk-ansible in your own environment.  The examples here setup a very
 basic container, that only exposes port 22 and has NOTHING preinstalled (not even ansible). You can follow this exact workflow with baremetal machines / vm's.
 
 In this case, first we'll spin up 4 containers to mimic our base baremetal hosts with ssh installed.  I've included a docker-compose file to easily build the image, and spin up the stack.

```
docker-compose -f docker-compose.yml up -d
```
This should stand up the full deployment and create all the required networking.

Verify they are all running with docker ps:
```
wrapper-example$ docker ps

CONTAINER ID        IMAGE                       COMMAND               CREATED             STATUS              PORTS                   NAMES
1337ac381424        debian_buster_sshd          "/usr/sbin/sshd -D"   5 seconds ago       Up 3 seconds        0.0.0.0:32772->22/tcp   wrapper-example_cluster_master_1
a325a28ba9ea        debian_buster_sshd          "/usr/sbin/sshd -D"   5 seconds ago       Up 4 seconds        0.0.0.0:32771->22/tcp   wrapper-example_indexer3_1
88d8ab42bc11        debian_buster_sshd          "/usr/sbin/sshd -D"   5 seconds ago       Up 4 seconds        0.0.0.0:32770->22/tcp   wrapper-example_indexer1_1
29d73413c155        debian_buster_sshd          "/usr/sbin/sshd -D"   5 seconds ago       Up 4 seconds        0.0.0.0:32769->22/tcp   wrapper-example_indexer2_1
2646ede6484a        debian_buster_sshd          "/usr/sbin/sshd -D"   6 seconds ago       Up 5 seconds        0.0.0.0:32768->22/tcp   wrapper-example_search_head_1
```

Next we'll copy our target key in for passwordless login:

```
ssh-copy-id -i ~/.ssh/mykey root@0.0.0.0 -p <port>
```
Make sure to do the above command for all containers. (Assuming you haven't changed the password for root in the Dockerfile, it's set to "**screencast**")

Now lets build an ansible inventory to work with our hosts, I personally am using the yaml version, but you can build your inventory
however you'd like.  See: https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html.  I've attached the sample
inventory, ansible_inventory.yaml.sample

```
$vi ansible_inventory.yaml

all:
  vars:
    ansible_user: root
  children:
    splunk_search_head:
      hosts:
        wrapper-example_search_head_1:
          ansible_port: 32768
          ansible_host: 0.0.0.0
    splunk_cluster_master:
      hosts:
        wrapper-example_cluster_master_1:
          ansible_port: 32772
          ansible_host: 0.0.0.0
    splunk_indexer:
      hosts:
        wrapper-example_indexer1_1:
          ansible_port: 32770
          ansible_host: 0.0.0.0
        wrapper-example_indexer2_1:
          ansible_port: 32769
          ansible_host: 0.0.0.0
        wrapper-example_indexer3_1:
          ansible_port: 32771
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

As long as the hello_world example had no failures, we're now ready to setup this index cluster. Please note, if you did not manually
 log into each container ahead of time, you may get a "host key not verified" error for ssh.  Either manually login and approve each
 container's ssh key, or you can add host_key_checking=False to the ansible-playbook commands.  Please setup a defaults.yml file (referenced in the docs)
and place it inside of our current working directory, next to the playbooks.  In the example below, I'm just going to use the
auto-generated defaults off of the splunk container to get started.

```
docker run --rm -it splunk/splunk:latest create-defaults > default.yml
```

The supplied play will setup all of  "install-splunk-ansible.playbook" will setup all the required prereqs for splunk-ansible, 
copy the defaults file to /tmp/defaults/default.yml and prep the install of splunk.  Run it now using:

```
ansible-playbook -vv -i ansible_inventory.yaml install-splunk-ansible.playbook
```
Grab some coffee, this might take a bit!

Once the play finishes for splunk-ansible, we're now ready to embed splunk-ansible as a module.  There's a couple of different ways to do this,
one you could use the "delegate_to" function of an ansible playbook command, or two, we tell ansible to run in an async method.  The install-splunk.playbook, runs
in the form of the latter. 

You can now create different default.yml for each role of splunk, or override the options in your playbook for each group.  Once your playbook is configured, run:
```
ansible-playbook -vv -i ansible_inventory.yaml install-splunk.playbook
```
*PLEASE NOTE: If you don't have a machine fast enough to handle 5 instances of splunk in containers starting, you may hit timeouts during the installation!*

You should now have a setup splunk instance, configured entirely asynchronously and utilizing splunk-ansible without needing to 
touch splunk-ansible's inventory directly. You're free now to connect to your searchhead / cluster_master port 8000's that are exposed!