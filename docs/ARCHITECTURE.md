## Navigation

* [Architecture](#architecture)
    * [Using defaults](#using-defaults)
    * [Users and groups](#users-and-groups)
    * [Remote networking](#remote-networking)
    * [Dynamic inventory](#dynamic-inventory)
* [Supported Platforms](#supported-platforms)
* [Usage](#usage)
    * [Docker](#docker)
    * [AWS](#aws)

----

## Architecture
From a design perspective, the plays within `splunk-ansible` are meant to be run locally on each instance of your intended Splunk deployment. The execution flow of the provisioning process is meant to gracefully handle interoperability in this manner, while also maintaining idempotency and reliability. 

##### Using defaults
TODO

##### Users and groups 
TODO

##### Remote networking 
Particularly when bringing up distributed Splunk topologies, there is a need for one Splunk instances to make a request against another Splunk instance in order to construct the cluster. These networking requests are often prone to failure, as when Ansible is executed asyncronously there are no guarantees that the requestee is online/ready to receive the message.

While developing new playbooks that require remote Splunk-to-Splunk connectivity, we employ the use of `retry` and `delay` options for tasks. For instance, in this example below, we add indexers as search peers of individual search head. To overcome error-prone networking, we have retry counts with delays embedded in the task. There are also break-early conditions that maintain idempotency so we can progress if successful:
```
- name: Set all indexers as search peers
  command: "{{ splunk.exec }} add search-server {{ cert_prefix }}://{{ item }}:{{ splunk.svc_port }} -auth {{ splunk.admin_user }}:{{ splunk.password }} -remoteUsername {{ splunk.admin_user }} -remotePassword {{ splunk.password }}"
  become: yes
  become_user: "{{ splunk.user }}"
  with_items: "{{ groups['splunk_indexer'] }}"
  register: set_indexer_as_peer
  until: set_indexer_as_peer.rc == 0 or set_indexer_as_peer.rc == 24
  retries: "{{ retry_num }}"
  delay: 3
  changed_when: set_indexer_as_peer.rc == 0
  failed_when: set_indexer_as_peer.rc != 0 and 'already exists' not in set_indexer_as_peer.stderr
  notify:
    - Restart the splunkd service
  no_log: "{{ hide_password }}"
  when: "'splunk_indexer' in groups"
```

Another utility you can add when creating new plays is an implicit wait. For more information on this, see the `roles/splunk_common/tasks/wait_for_splunk_instance.yml` play which will wait for another Splunk instance to be online before making any connections against it.
```
- name: Check Splunk instance is running
  uri:
    url: https://{{ splunk_instance_address }}:{{ splunk.svc_port }}/services/server/info?output_mode=json
    method: GET
    user: "{{ splunk.admin_user }}"
    password: "{{ splunk.password }}"
    validate_certs: false
  register: task_response
  until:
    - task_response.status == 200
    - lookup('pipe', 'date +"%s"')|int - task_response.json.entry[0].content.startup_time > 10
  retries: "{{ retry_num }}"
  delay: 3
  ignore_errors: true
  no_log: "{{ hide_password }}"
```

##### Dynamic inventory
This Ansible repository also contains a custom dynamic inventory script, located at `inventory/environ.py`. Using a dynamic inventory when everything runs within the context of a local connection may seem counterproductive, but the purpose of this script is to build out the Splunk topology from the information provided by environment variables.

Particularly, this can be demonstrated with the approach used in the Docker image. If the Docker image is ran with certain environment variables (ex. `SPLUNK_INDEXER_URLS=idx1`), then each instance you're provisioning to assume a specific Splunk role will know how to add itself or other instances to build out the cluster.

The `environ.py` is responsible for choreographing everything together and giving a shared context to each separate, distinct host. It does all this by reading special `SPLUNK_`-prefixed variables and passing it into the `ansible-playbook` command. To utilize this feature, you can run your command as so:
```
$ ansible-playbook --inventory inventory/environ.py ...
$ ansible-playbook -i inventory/environ.py ...
```

---

## Supported Platforms
At the current time, this only supports Linux-based platforms (Debian, CentOS, etc.). We do have plans to incorporate Windows in the future. 

---

## Usage
See how the `splunk-ansible` project is being used in the wild! You can use these projects as reference for how to most effectively bring these playbooks into your cloud provider or technology stack.

##### Docker
The playbooks in this repository are already being used in the context of containers! For more information on how this works, please see the [docker-splunk](https://github.com/splunk/docker-splunk/) project and learn how `splunk-ansible` is incorporated.

##### AWS
TODO
