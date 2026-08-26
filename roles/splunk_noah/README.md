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
mode disabled, existing classic provisioning follows its original path.

The SOK controller owns the shared `[noahService]` values such as `uri`,
`tenant`, and the desired enabled state. Kubernetes identity variables provide
the indexer's advertised address. Authentication material is staged in
`server.conf` from a Kubernetes Secret; this role does not require the Noah
key in an environment variable. If the standard docker-splunk
`splunk.pass4SymmKey` value is also present, the pre-auth path writes it using
`no_log` so existing deployments retain their current behavior.

Search-head cluster settings remain in the search-head lifecycle role. This
role only writes their first-start configuration before splunkd starts, which
lets the existing SHC commands verify or form the cluster without an
unnecessary configuration restart.
