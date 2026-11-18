# Windows permission guidance

Read this before changing filesystem operations reachable on Windows or Cygwin.
[PR #962](https://github.com/splunk/splunk-ansible/pull/962) introduced native
Windows configuration I/O to avoid translating MSI-managed security descriptors
through POSIX file operations.

## Permission contract

- Preserve existing owners, groups, DACL rules, and inheritance protection when
  editing configuration or reconciling state. Repeated provisioning must retain
  the existing access policy.
- Do not add Windows-reachable POSIX ownership or mode enforcement through
  ordinary `file`, `ini_file`, `lineinfile`, or `copy` operations. Omitting only
  `owner` and `group` is insufficient: mode changes and file replacement can also
  translate or replace native ACLs. Audit templates and scripted writes too.
- New Windows files/directories need restricted native ACLs that retain access
  for the installed Splunk service identity. The provisioning account and service
  account can differ.
- Retain configured Unix ownership and restrictive POSIX modes on Unix paths.

Treat `Win32NT` and system names starting with `CYGWIN` as Windows for this policy.
It applies to configuration, managed-value receipts, runtime state, markers, and
any parent directories created for them.

## Implementation and reachability

1. Trace role, include, block, and task conditions. A release or feature flag
   referring to Kubernetes/SOK does not enforce an OS restriction.
2. For Linux-only operations, enforce the restriction in the task/include
   conditions. Otherwise provide native permission-preserving Windows behavior.
3. Use `action_plugins/splunk_config.py` and its
   `library/splunk_windows_config.py` backend for supported configuration edits.
   Read the target revision's supported operations first. The #962 version rejects
   `file: state=touch` and timestamp arguments; changing only the module name does
   not implement safe marker creation.
4. If the target branch predates these helpers, inspect #962 rather than copying
   an older unprotected writer.
5. Check missing and existing files/directories separately. Preserve existing
   directory attributes and marker contents/timestamps unless the feature
   explicitly requires a change. Check reruns and actual service-account access.

The motivating example is
[PR #965](https://github.com/splunk/splunk-ansible/pull/965) at `3039b49`: its
new KVService marker tasks used POSIX `owner`, `group`, and `0700`/`0600` modes
without an OS gate. Windows/Cygwin satisfied the task conditions, but the first
review considered Linux startup behavior only. This identified a compatibility
gap; an actual Windows runtime failure was not established by that review.

## Verification

Read `tests/small/test_windows_config_ownership.py` and
`tests/small/test_windows_config_planner.py`. Their task lists cover specific
writers; passing them does not cover every newly added task.

For a changed writer, test the applicable Linux, `Win32NT`, and Cygwin conditions,
including asserted skips on unsupported platforms. Check creation, existing
security attributes, service-account access, and reruns as applicable. Mocked
conditions and Linux localhost tests do not prove native Windows ACL preservation.
Use the [command guide](agent-validation.md) for tested local checks and report
native Windows validation separately.
