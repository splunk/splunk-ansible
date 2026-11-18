# Repository guidance for agents

These instructions apply to the whole repository, including implementation and
code review. Splunk provisioning supports Linux and Windows/Cygwin. Shared roles
must preserve platform-specific behavior even when a feature is primarily used
by Linux containers.

## Preserve native Windows permissions

[PR #962](https://github.com/splunk/splunk-ansible/pull/962) establishes the
Windows permission handling that future changes must respect:

- Preserve existing Windows file and directory owners, groups, DACL rules, and
  inheritance protection. MSI-managed permissions must survive configuration
  edits and repeated provisioning.
- Do not introduce Windows-reachable POSIX ownership or mode enforcement through
  ordinary `file`, `ini_file`, `lineinfile`, or `copy` operations. Omitting only
  `owner` and `group` is insufficient: mode changes and file replacement can also
  translate or replace native ACLs.
- Use the platform-aware `splunk_config` action and its
  `library/splunk_windows_config.py` backend where available in the target
  revision. Inspect their supported operations before using them. The version
  introduced by #962 does not support `file: state=touch`; marker creation needs
  a supported native operation or an explicit platform restriction.
- If working on an older branch without these helpers, inspect #962 and preserve
  its permission guarantees rather than copying an older unprotected writer.
- New Windows files and directories need restricted native ACLs that retain
  access for the installed Splunk service identity. Do not assume the service
  account and provisioning account are the same.
- Retain configured Unix ownership and restrictive POSIX modes on Unix paths.

Treat both `Win32NT` and systems whose name starts with `CYGWIN` as Windows for
this policy. Review configuration files, managed-value receipts, runtime state,
marker files, and any parent directories created for them. Include template
replacements and scripted `chmod`/`chown` or filesystem writes in this audit.

## Check platform reachability before approving filesystem changes

For every new or modified filesystem writer in a shared role:

1. Trace the actual role, include, block, and task conditions. A feature flag,
   release gate, or reference to Kubernetes/SOK does not enforce a Linux gate.
2. Check Windows/Cygwin behavior explicitly. If an operation is Linux-only,
   enforce that restriction in the task/include conditions. Otherwise provide
   permission-preserving Windows behavior.
3. Check both creation and existing-state behavior. Preserve existing directory
   attributes and marker contents/timestamps unless the change explicitly
   requires updating them. Verify repeated execution is safe.
4. Read related platform fixes and helpers in the review's target revision,
   even when the new diff does not modify them. Do not infer compatibility from
   an unchanged helper or from a similar legacy task.

The motivating example is
[PR #965](https://github.com/splunk/splunk-ansible/pull/965) at `3039b49`: its
new KVService marker tasks used POSIX `owner`, `group`, and `0700`/`0600` modes
without an OS gate. A Linux-first review missed that Windows/Cygwin satisfied
the conditions. Apply the permission policy to newly added paths, not just
files changed by #962.

## Verification and review evidence

- Read `tests/small/test_windows_config_ownership.py` and, where present,
  `tests/small/test_windows_config_planner.py` when changing shared filesystem or
  configuration writers. Their task lists cover specific writers; passing them
  does not automatically cover a newly added task.
- Add relevant coverage for new writers on Linux, `Win32NT`, and a Cygwin system
  name. Exercise the applicable enablement, version, role, and fresh/existing
  installation conditions, including an asserted skip for unsupported platforms.
- Check that Windows operations avoid POSIX attribute enforcement and Unix
  operations retain required ownership/modes. Test preservation on reruns.
- Run focused tests and applicable YAML/syntax checks. For documentation-only
  changes, inspect the text and check whitespace; application tests are unnecessary.
- Distinguish condition/argument tests from native Windows ACL validation in the
  review result. Linux localhost tests and Splunk runtime tests do not establish
  preservation of Windows security descriptors.
