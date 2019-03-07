## Navigation

* [Defaults](#defaults)
    * [Loading defaults through file](#loading-defaults-through-file)
    * [Loading defaults through URL](#loading-defaults-through-url)
    * [Schema](#schema)
* [Apps](#app)
* [SmartStore](@smartstore)
* [Defaults](#defaults)

---

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
