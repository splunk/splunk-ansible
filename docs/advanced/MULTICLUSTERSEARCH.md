## Multi-cluster Search

When configuring a search head, it's possible that enable multi-cluster search. This enables the ability to search for data across a series of indexer clusters, whether they be located in different datacenters or different geographical regions.

For more information, see [Splunk docs on multi-cluster search](https://docs.splunk.com/Documentation/Splunk/latest/Indexer/Configuremulti-clustersearch).

The Ansible playbooks provided in this repository offer this feature through the `auxiliary_cluster_masters` option in the `default.yml` variables. To enable this, modify this section of the `default.yml` to include a list of cluster masters responsible for brokering the indexer clusters:
```
splunk:
  ...
  cluster_master_url: master-primary.regionA.corp.net
  auxiliary_cluster_masters:
    - url: https://master-secondary.regionA.corp.net:8089
      pass4SymmKey: secretidxckey
    - url: https://master-tertiary.regionB.corp.net:8089
      pass4SymmKey: newsecretidxckey
  ...
```

Note that in the above, the search head being created must also set `cluster_master_url`. It is only possible to peer multiple indexer clusters when the search head has a primary indexer cluster to send its own internal logs and data to. 

Each additional cluster master must also be given their own `pass4SymmKey` to enable authorization for this Splunk search head to connect and search over the various other clusters. 

To confirm that the multi-cluster search works after Ansible has been completed, visit SplunkWeb on this search head and run the following query:
```
search index=_internal
```

If successful, you should see:
* The data from `host=master-primary.regionA.corp.net`, plus any downstream indexers that connect to this cluster
* The data from `host=master-secondary.regionA.corp.net`, plus any downstream indexers that connect to this cluster
* The data from `host=master-tertiary.regionB.corp.net`, plus any downstream indexers that connect to this cluster
* The data from the node just provisioned, which should be forwarded to `master-primary.regionA.corp.net`
