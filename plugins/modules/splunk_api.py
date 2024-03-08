#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import os
import requests
import requests_unixsocket
import json

UDS_SOCKET_PATH = "/opt/splunkforwarder/var/run/splunk/cli.socket"
UDS_SOCKET_PATH_URL = "%2Fopt%2Fsplunkforwarder%2Fvar%2Frun%2Fsplunk%2Fcli.socket"

def supports_uds():
    return os.path.exists(UDS_SOCKET_PATH)

def api_call_tcp(cert_prefix_mode, method, endpoint, username, password, svc_port, payload=None, headers=None, verify=False, status_code=None, timeout=None):
    if not cert_prefix_mode or cert_prefix_mode not in ['http', 'https']:
      cert_prefix_mode = 'https'
    if not svc_port:
      svc_port = 8089
    url = "{}://127.0.0.1:{}{}".format(cert_prefix_mode, svc_port, endpoint)
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    auth = (username, password)

    session = requests.Session()
    # Disable SSL verification for the session
    session.verify = False

    response = None
    excep_str = "No Exception"
    try:
      response = session.request(method, url, headers=headers, auth=auth, data=json.dumps(payload), verify=verify, timeout=timeout)
      if status_code is not None and response.status_code not in status_code:
          raise ValueError("API call for {} and data as {} failed with status code {}: {}".format(url, payload, response.status_code, response.text))
    except Exception as e:
      excep_str = "{}".format(e)
      cwd = os.getcwd()
    return response, excep_str

def api_call_uds(method, endpoint, username, password, svc_port, payload=None, headers=None, verify=False, status_code=None, timeout=None):
    url = "http+unix://{}{}".format(UDS_SOCKET_PATH_URL,endpoint)
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    auth = (username, password)

    session = requests_unixsocket.Session()
    # Disable SSL verification for the session
    session.verify = False

    excep_str = "No Exception"
    response = None
    try:
      response = session.request(method, url, headers=headers, auth=auth, data=json.dumps(payload), verify=verify, timeout=timeout)
      if status_code is not None and response.status_code not in status_code:
        raise ValueError("API call for {} and data as {} failed with status code {}: {}".format(url, payload, response.status_code, response.text))
    except Exception as e:
      excep_str = "{}".format(e)
    return response, excep_str

def main():
    module_args = dict(
        method=dict(type='str', required=True),
        url=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        cert_prefix_mode=dict(type='str', required=False),
        body=dict(type='dict', required=False),
        headers=dict(type='dict', required=False),
        verify=dict(type='bool', required=False),
        status_code=dict(type='list', required=False),
        timeout=dict(type='int', required=False),
        svc_port=dict(type='int', required=False)
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
    cert_prefix_mode = module.params.get('cert_prefix_mode', 'http')
    payload = module.params.get('body', None)
    headers = module.params.get('headers', None)
    verify = module.params.get('verify', False)
    status_code = module.params.get('status_code', None)
    timeout = module.params.get('timeout', None)
    svc_port = module.params.get('svc_port', 8089)

    s = "{}{}{}{}{}{}{}{}{}".format(method, endpoint, username, password, svc_port, payload, headers, verify, status_code, timeout)
    if supports_uds():
        response, excep_str = api_call_uds(method, endpoint, username, password, svc_port, payload, headers, verify, status_code, timeout)
    else:
        response, excep_str = api_call_tcp(cert_prefix_mode, method, endpoint, username, password, svc_port, payload, headers, verify, status_code, timeout)

    if response is not None and ((status_code and response.status_code in status_code) or (status_code is None and response.status_code >= 200 and response.status_code < 300)):
        try:
          content = response.json()
        except:
          content = response.text
        module.exit_json(changed=True, status = response.status_code ,json=content,excep_str=excep_str)
    else:
        if response is None:
          module.fail_json(msg="{};;; failed with NO RESPONSE and EXCEP_STR as {}".format(s, excep_str))
        else:
          module.fail_json(msg="{};;; failed with status code {}: {}".format(s, response.status_code, response.text))

if __name__ == '__main__':
    main()
