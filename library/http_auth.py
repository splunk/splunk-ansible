#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import requests
import os

def run_module():
    module_args = dict(
        url=dict(type='str', required=True),
        dest=dict(type='str', required=True),
        token=dict(type='str', required=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    headers = {
        "Authorization": "Bearer {}".format(module.params['token'].split(":")[1])
    }

    try:
        response = requests.get(
            module.params['url'],
            headers=headers,
        )
        response.raise_for_status()

        # Extract filename from URL
        filename = os.path.basename(module.params['url'])

        # Join dest directory with filename
        file_path = os.path.join(module.params['dest'], filename)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    except requests.exceptions.RequestException as e:
        module.fail_json(msg="Failed to download the file. Error: {}".format(e))

    module.exit_json(changed=True, dest=file_path)

if __name__ == '__main__':
    run_module()