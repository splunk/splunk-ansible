#!/usr/bin/python

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import argparse
import functools
import requests
import splunk.auth as auth
import sys

app_info = '{"app": "Splunk_TA_ForIndexers", "label": "Splunk App For Indexers", "version": "1.0.0", "build": "0"}'
include_indexes = True
imported_apps_only = True
namespace = 'SplunkEnterpriseSecuritySuite'
spl_location = make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'local', 'data', 'appmaker'])


def create_parser():
	parser = argparse.ArgumentParser(description="Script to generate Enterprise Security TA bundle")
	parser.add_argument("--username", default="admin", type=str, help="Splunk username")
	parser.add_argument("--password", default=None, type=str, help="Splunk password")
	return parser

def make_ta_for_indexers(username, password):
    '''
    Splunk_TA_ForIndexers spl generation for ES 4.2.0 and up
    '''
    if not username or not password:
    	raise Exception("Splunk username and password must be defined.")
    sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Utils', 'bin']))
    session_key = auth.getSessionKey(username, password)
    from app_maker.make_index_time_properties import makeIndexTimeProperties
    try:
        archive = makeIndexTimeProperties(app_info, session_key, include_indexes=include_indexes,
        								  imported_apps_only=imported_apps_only, namespace=namespace)
    except TypeError:
        #Some versions have a change that removed the kwarg imported_apps_only
        #For older versions, we'll still need to use the imported_apps_only arg, so that's why we
        #do this second
        archive = makeIndexTimeProperties(app_info, session_key, include_indexes=include_indexes,
        								  namespace=namespace)
    print archive
    assert archive.startswith(spl_location)


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    make_ta_for_indexers(args.username, args.password)
