# Required Defaults.yml File
For security reasons, we do not ship with our defaults.  This means that it is required to be provided by the user of these images.  The file can be loaded in two different ways.  It can be loaded via a URL or through a mounted volume.

## Loading through a URL
The url must be a text yml file, and accessible through a HTTP GET request.  Currently, no parameters are passed through the request.  Redirects are permitted.

## Loading through a flat file
The flat file must be mounted into the container at /tmp/defaults/default.yml.  It must be readable.

## Defaults.yml format
An example implementation is provided
```
---
# Splunk defaults

retry_num: 100
splunk:
    opt: /opt
    home: /opt/splunk
    user: splunk
    group: splunk
    exec: /opt/splunk/bin/splunk
    pid: /opt/splunk/var/run/splunk/splunkd.pid
    password: "{{ splunk_password | default('invalid_password') }}"
    svc_port: 8089
    s2s_port: 9997
    http_port: 8000
    hec_port: 8088
    hec_disabled: 0
    hec_enableSSL: 1
    #The hec_token here is used for INGESTION only (receiving splunk events).
    #Setting up your environment to forward events out of the cluster is another matter entirely
    hec_token: 00000000-0000-0000-0000-000000000000
    app_paths:
        default: /opt/splunk/etc/apps
        shc: /opt/splunk/etc/shcluster/apps
        idxc: /opt/splunk/etc/master-apps
        httpinput: /opt/splunk/etc/apps/splunk_httpinput

    # Search Head Clustering
    shc:
        enable: false
		#Change these before deploying
        secret: some_secret
        replication_factor: 3
        replication_port: 4001

    # Indexer Clustering
    idxc:
	    #Change before deploying
        secret: some_secret
        search_factor: 2
        replication_factor: 3
        replication_port: 9887
```

