# Verifying agent changes

Choose checks for the target revision and the behavior changed. Commands in old
documentation are not automatically valid for the current checkout. The examples
below were exercised against the code at `9f9d0e98` while preparing PR #967;
the validation record below identifies the environment and results.

## Check the environment first

Use an isolated development environment. Keep `python3` and `ansible-playbook`
from the same environment: some task tests invoke the executable on `PATH`, while
the medium harness prefers the executable beside its Python interpreter.

The repository's `ansible.cfg` writes logs under `/opt/container_artifact` and
enables privilege escalation. For local checks, select writable scratch paths
before importing Ansible or invoking its CLI:

```sh
validation_tmp=$(mktemp -d)
export ANSIBLE_LOCAL_TEMP="$validation_tmp/local"
export ANSIBLE_REMOTE_TEMP="$validation_tmp/remote"
export ANSIBLE_LOG_PATH="$validation_tmp/ansible.log"
```

This relocates logs and temporary files; it does not disable privilege escalation
or make a provisioning run safe against an arbitrary inventory.

Record tool and collection versions:

```sh
python3 --version
python3 -m pytest --version
ansible --version
ansible-galaxy collection list community.general
ansible-galaxy collection list ansible.posix
python3 -c 'from ansible_collections.community.general.plugins.modules import ini_file; print(ini_file.__file__)'
yamllint --version
```

`tests/requirements.txt` is unpinned. Verify the dependencies used by the selected
tests rather than upgrading a shared environment. The planner imports
`community.general.ini_file`; the configuration probe at this revision supports
`community.general >=10.0.0,<12.0.0`. The medium harness describes Ansible 11 /
ansible-core 2.18 and requires the `ansible.posix.json` callback. Having an
`ansible-playbook` executable alone does not establish those prerequisites.

## Focused checks

Run from the repository root. This representative small-test command covers
version facts, configuration merging, and the existing Windows permission tasks
and planner:

```sh
python3 -m pytest -q \
  tests/small/test_version_facts.py \
  tests/small/test_splunk_conf_files.py \
  tests/small/test_windows_config_ownership.py \
  tests/small/test_windows_config_planner.py
```

Choose or extend tests for the actual change; this selection is not a universal
approval gate. For configuration reconciliation, use the medium task harness
with its compatible environment:

```sh
python3 -m pytest -q tests/medium/test_config_map_reconcile.py
```

The medium harness runs real Ansible tasks on temporary localhost fixtures; it
does not start Splunk or exercise native Windows security APIs. Avoid pytest's
`--import-mode=importlib` here: medium tests use sibling-module imports.

For changed YAML, lint the affected files. This is a verified example; replace
the file selection with the YAML changed by your patch:

```sh
yamllint roles/splunk_common/tasks/set_config_file.yml
ansible-playbook --syntax-check -i localhost, site.yml
git diff --check
```

Syntax checking does not execute the playbook or validate every dynamically
included task. A successful check is not a Splunk startup/topology test.

If unrelated globally installed pytest plugins interfere with collection, use
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` for these self-contained checks and record the
override. It is an environment workaround, not a project dependency requirement.
Do not disable plugins needed by a different selected suite.

## Legacy command traps

- `make medium-tests` has no target at this revision, despite its mention in
  `docs/CONTRIBUTING.md`. Use the verified direct pytest command above.
- `make test`, `make small-tests`, and lint targets run setup that upgrades pip
  and unpinned dependencies. `make test` also invokes legacy `pylint --py3k`,
  `caniusepython3`, and Molecule deployment scenarios. Inspect the target before
  using it; it is not a quick check in an existing shared environment.
- Old architecture text describes Windows as future work. Inspect current
  Windows/Cygwin task conditions and native helpers when assessing compatibility.

## Validation record

Validation date: 2026-11-18. Code revision: `9f9d0e98`; the PR adds documentation
only. These are tested snapshots, not a new repository dependency policy.

The final checks used a temporary virtual environment on macOS with these
versions, confirmed by the version commands above and installed package metadata:

| Component | Verified version |
| --- | --- |
| Python | 3.11.4 |
| Ansible package / ansible-core | 11.0.0 / 2.18.20 |
| `community.general` / `ansible.posix` | 10.0.1 / 1.6.2 |
| pytest / yamllint | 8.3.5 / 1.35.1 |
| PyYAML / Jinja2 | 6.0.2 / 3.1.6 |

Results for the commands above:

- Selected small tests: **128 passed**, no skips.
- `tests/medium/test_config_map_reconcile.py`: **12 passed**, no skips.
- Direct Python import of `community.general.ini_file`: passed.
- Playbook syntax check and example YAML lint: passed.
- Document links and whitespace: checked, including the newly added files.

These final runs used the scratch-path setup above and normal pytest plugin
discovery in the isolated environment. The full suite, Molecule scenarios, native
Windows ACL checks, and real Splunk deployments were not run.

The older Python 3.9.17 / ansible-core 2.15.13 / `community.general` 7.5.2
environment also passed the 128 small tests, with plugin autoload disabled. Its
medium attempt was stopped after two failed unchanged-write assertions. That
collection is outside the probe's supported range and forces fallback writes;
the environment is insufficient to validate the optimization. Passing collection
or small tests alone does not establish compatibility for the medium checks.
