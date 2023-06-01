#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import os
import requests
import json

UDS_SOCKET_PATH = "/var/run/splunk/cli.socket"

def supports_uds():
    return os.path.exists(UDS_SOCKET_PATH)

def api_call_port_8089(method, endpoint, username, password, payload=None, headers=None, verify=False, status_code=None, timeout=None):
    url = f"https://127.0.0.1:8089{endpoint}"
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    auth = (username, password)

    session = requests.Session()
    session.verify = verify

    response = session.request(method, url, headers=headers, auth=auth, data=json.dumps(payload), timeout=timeout)

    result = {
        'url': url,
        'status': response.status_code,
        'headers': dict(response.headers),
        'body': response.text
    }

    if status_code is not None and response.status_code not in status_code:
        raise ValueError(f"API call failed with status code {response.status_code}: {response.text}")
    return result

def main():
    module_args = dict(
        method=dict(type='str', required=True),
        url=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        body=dict(type='dict', required=False),
        headers=dict(type='dict', required=False),
        verify=dict(type='bool', required=False, default=False),
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
    payload = module.params.get('body', None)
    headers = module.params.get('headers', None)
    verify = module.params.get('verify', False)
    status_code = module.params.get('status_code', None)
    timeout = module.params.get('timeout', None)

    response = api_call_port_8089(method, endpoint, username, password, payload, headers, verify, status_code, timeout)

    if response['status'] >= 200 and response['status'] < 300:
        module.exit_json(changed=True, content=response)
    else:
        module.fail_json(msg=f"API call failed with status code {response['status']}: {response['body']}")

if __name__ == '__main__':
    main()