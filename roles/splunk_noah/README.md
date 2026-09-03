# Noah provisioning role

Noah mode is an explicit layer on top of the existing `splunk.role`. It is
enabled only by `SPLUNK_NOAH_ENABLED=true`; adding a `[noahService]` stanza
does not activate this role.

| `splunk.role` | Noah client behavior | Heartbeats | Peer/bucket-map discovery |
| --- | --- | --- | --- |
| `splunk_indexer` | Peer | Enabled | Disabled |
| `splunk_search_head` | Search client | Disabled | Enabled |
| `splunk_deployer` | None | Disabled | Disabled |

Provisioning has two deliberate entry points:

1. `pre_auth.yml` writes a complete but disabled `[noahService]` stanza
   before docker-splunk starts its temporary authentication process.
2. `post_config.yml` selects exactly one role profile after declarative
   configuration is rendered and before the first full splunkd start.

Unsupported Splunk roles fail validation when Noah mode is enabled. With Noah
mode disabled, Noah client configuration is not written.

The SOK controller owns the shared `[noahService]` values such as `uri`,
`tenant`, and the desired enabled state. Kubernetes identity variables provide
the indexer's advertised address. Authentication material is staged in
`server.conf` from a Kubernetes Secret; this role does not require the Noah
key in an environment variable. If the standard docker-splunk
`splunk.pass4SymmKey` value is also present, the pre-auth path writes it using
`no_log` so existing deployments retain their current behavior.

Search-head cluster formation is deliberately shared rather than implemented
inside this Noah role. The common Linux SHC pre-start task writes the stable
member and replication configuration while splunkd is stopped for both classic
and Noah deployments. Classic mode also writes its Cluster Manager peering;
Noah mode writes only the Noah search-client settings here. The later SHC
commands form and verify the cluster without scheduling duplicate restarts.
