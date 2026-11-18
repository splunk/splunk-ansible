# Agent guidance

These instructions apply to implementation and review throughout this repository.
Preserve existing deployment behavior across applicable roles, releases, and
platforms. A change in a shared provisioning task can affect multiple topologies.

## Repository map

- `site.yml` and `multisite.yml`: provisioning entry points and role selection.
- `inventory/environ.py` and `inventory/*defaults*.yml`: environment parsing,
  platform/product defaults, topology, and effective Ansible variables.
- `inventory/splunk_config.py`: shared configuration merge/normalization logic.
- `roles/*/meta/main.yml`: role dependencies; inspect these before assuming which
  tasks execute. Product roles commonly depend on `splunk_common`.
- `roles/splunk_common/tasks/main.yml`: shared lifecycle and configuration order.
  Role-specific tasks live under the other `roles/` directories.
- `action_plugins/`, `library/`, and role-local `filter_plugins/` and `library/`:
  custom execution, configuration, and probe helpers.
- `tests/small/` and `tests/medium/`: focused logic/task tests and localhost
  integration tests. Role `molecule/` directories contain deployment scenarios.
- `docs/ADVANCED.md`, `docs/CONTRIBUTING.md`, and `roles/splunk_noah/README.md`:
  input contracts, contribution context, and Noah-specific lifecycle details.
  Verify documentation against the target revision; some older guidance is stale.

## Inputs and compatibility

- Trace a setting from defaults and environment parsing through its consuming
  role/task. Preserve defined precedence, mapping/list forms, and the distinction
  between unset, explicit `false`, and `true` where the input defines it.
- Reuse merge and normalization helpers. Mappings, ordinary lists, user entries,
  and entries targeting different configuration directories have different rules.
- Check role, installed-release, feature, and OS conditions together. A Kubernetes
  or SOK feature flag does not itself restrict execution to Linux.
- Keep opt-in behavior scoped to its feature. Check disabled and legacy paths
  before changing shared defaults or adding unconditional configuration writes.

## Configuration ownership

- Use the existing configuration writer, probe, and reconciliation paths rather
  than introducing competing writers with different precedence or cleanup rules.
- Remove stale values using the existing managed-value receipts and policy;
  preserve unrelated customer settings. Batch entries by effective target file
  so one entry does not remove another entry's managed values.
- Preserve fallback behavior when an optimization probe cannot inspect a file.
  A failed optimization must not silently suppress required configuration writes.

## Lifecycle and distributed provisioning

- Trace the full include/dependency chain and task order. Some authentication
  paths invoke or temporarily start Splunk before the normal full startup.
- Distinguish fresh installation, upgrade, running-instance reconciliation, and
  repeated provisioning. Preserve each feature's definition of freshness:
  `first_run` and KVService installation state use different native files.
- Account for CLI side effects when capturing initial state. Write configuration
  at the lifecycle stage its consumer requires.
- Preserve shared restart handlers, final restart-required checks, and the scope
  of restart-deferral flags. Avoid unnecessary restarts for unchanged settings.
- Peers provision asynchronously. Use existing readiness checks and appropriate
  bounded retries/delays, including shared retry variables where applicable.
  Handle known already-configured outcomes without hiding genuine failures.

## Permissions and secrets

- Preserve the execution identity selected by the caller. `site.yml` normally
  provisions as `splunk.user`; installation and service operations may explicitly
  require `privileged_user`. Keep escalation limited to the necessary tasks.
- Preserve Unix ownership and restrictive modes, and Windows/Cygwin native
  ownership, DACLs, inheritance protection, and Splunk service-account access.
- Before adding or changing filesystem writers, read
  [Windows permission guidance](docs/contributing/windows-permissions.md).
  This includes configuration, receipts, runtime markers, parent directories,
  template replacement, and scripted filesystem operations.
- Preserve existing `no_log`/`hide_password` protection. New diagnostics must not
  print credentials or complete sensitive configuration payloads; use sanitized
  summaries. Do not assume the inventory's selective redaction covers every key.

## Verification and review

- Identify the target revision and installed Python, Ansible, and collection
  versions before choosing commands. Follow the
  [verified command guide](docs/contributing/agent-validation.md), which records
  the revision, environment, results, and limits of its examples.
- Run focused behavioral tests for the layer changed. Cover relevant role,
  release, platform, enablement, fresh/existing-state, and rerun cases. Existing
  tests with fixed task lists do not automatically cover new writers.
- Read related platform fixes and helper implementations even when the diff does
  not modify them. Inspect the actual target revision, not a different checkout.
- For functional changes, run applicable YAML and playbook syntax checks in
  addition to tests. Syntax checking does not execute dynamically included tasks.
- Report commands, versions, results, skips, and material validation gaps.
  Distinguish mocked conditions, localhost integration, native Windows ACL tests,
  and real Splunk/topology validation. Do not imply one proves the others.
- For documentation-only changes, check accuracy, links, and whitespace.
  Application tests are only needed when verifying instructions or behavior
  described by the documentation.
