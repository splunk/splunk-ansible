#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import os
import requests
# import requests_unixsocket
import json

UDS_SOCKET_PATH = "/var/run/splunk/cli.socket"

def supports_uds():
    return os.path.exists(UDS_SOCKET_PATH)

# update to take svc_port variable
def api_call_port_8089(method, endpoint, username, password, payload=None, headers=None, verify=False, status_code=None, timeout=None):
    url = f"https://127.0.0.1:8089{endpoint}"
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    auth = (username, password)

    session = requests.Session()
    # Disable SSL verification for the session
    session.verify = False

    response = session.request(method, url, headers=headers, auth=auth, data=json.dumps(payload), verify=verify, timeout=timeout)
    if status_code is not None and response.status_code not in status_code:
        raise ValueError(f"API call failed with status code {response.status_code}: {response.text}")
    return response

def main():
    module_args = dict(
        method=dict(type='str', required=True),
        url=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        body=dict(type='dict', required=False),
        headers=dict(type='dict', required=False),
        verify=dict(type='bool', required=False),
        status_code=dict(type='list', required=False),
        timeout=dict(type='int', required=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(changed=False)

    method = module.params['method']
    endpoint = module.params['url']
    username = module.params['username']
    password = module.params['password']
    payload = module.params.get('payload', None)
    headers = module.params.get('headers', None)
    verify = module.params.get('verify', False)
    status_code = module.params.get('status_code', None)
    timeout = module.params.get('timeout', None)

    if supports_uds():
        # TODO: Update back
        response = api_call_port_8089(method, endpoint, username, password, payload, headers, verify, status_code, timeout)
    else:
        response = api_call_port_8089(method, endpoint, username, password, payload, headers, verify, status_code, timeout)

    if response.status_code >= 200 and response.status_code < 300:
        try:
            content = response.json()
        except json.decoder.JSONDecodeError:
            content = response.text
        module.exit_json(changed=True, content=content)
    else:
        module.fail_json(msg=f"API call failed with status code {response.status_code}: {response.text}")

if __name__ == '__main__':
    main()