# -*- coding: utf-8 -*-
'''
Interact with UrBackup

https://www.urbackup.org/

'''

# Import Python Libs
from __future__ import absolute_import

# Import 3rd-party libs
# pylint: disable=import-error,no-name-in-module,redefined-builtin
from salt.ext.six.moves.urllib.parse import urlencode, urlparse
import salt.ext.six
import salt.ext.six.moves.http_client
# pylint: enable=import-error,no-name-in-module

# Import salt libs
import salt.utils.http

import json
import pprint
from base64 import b64encode
import hashlib
import binascii

import logging
logger = logging.getLogger(__name__)

from salt.exceptions import SaltInvocationError

# Don't shadow built-ins.
__func_alias__ = {
    'list_': 'list'
}

__virtualname__ = 'urbackup'



class Client():
    '''
    Wrapper inspired from https://github.com/uroni/urbackup-server-python-web-api-wrappe
    '''

    def __init__(self, url=None, username=None, password=None):

        if not url:
            url = __salt__['config.get']('urbackup:url', 'http://127.0.0.1:55414/x')

        if not username:
            username = __salt__['config.get']('urbackup:username', None)

        if not password:
            password = __salt__['config.get']('urbackup:password', None)

        self._url = url
        self._username = username
        self._password = password

        self._session = ''
        self._logged_in = False
        self._lastlogid = 0

    def _get_response(self, action, params, method='POST'):
                
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=UTF-8'
        }

        if not params:
            params = {}

        query_params = {}
        
        if('server_basic_username' in globals() and len(self.server_basic_username)>0):
            userAndPass = b64encode(str.encode(self.server_basic_username+':'+self.server_basic_password)).decode('ascii')
            headers['Authorization'] = 'Basic %s' %  userAndPass
        
        if(len(self._session)>0):
            params['ses']=self._session
            
        query_params['a'] = action

        if not method:
            method = 'POST'
        
        if method=='POST':
            data = urlencode(params)
        else:
            data = None
            query_params.update(params)
        
        http_timeout = 10*60;

        result = salt.utils.http.query(
                self._url,
                method=method,
                params=query_params,
                data=data,
                headers_dict=headers,
                decode=True,
                status=True,
                opts=__opts__,
        )
        return result


    def _get_json(self, action, params = {}):     
        tries = 50
        
        while tries>0:
            response = self._get_response(action, params)
        
            if(response['status'] == 200):
                break
            
            tries=tries-1
            if(tries==0):
                return None
            else:
                logger.error('API call failed. Retrying...')
        
        return response['dict']
                
    
    def _md5(self, s):
        return hashlib.md5(s.encode()).hexdigest()
    
    def login(self):
        
        if( not self._logged_in):
            
            logger.debug('Trying anonymous login...')
            
            login = self._get_json('login', {});

            if(not login or 'success' not in login or not login['success']):
                            
                logger.debug('Logging in...')
            
                pw_salt = self._get_json('salt', {'username': self._username})
                
                if( not pw_salt or not ('ses' in pw_salt) ):
                    logger.warning('Username does not exist')
                    return False
                    
                self._session = pw_salt['ses'];
                    
                if( 'salt' in pw_salt ):
                    password_md5_bin = hashlib.md5((pw_salt['salt']+self._password).encode()).digest()
                    password_md5 = binascii.hexlify(password_md5_bin).decode()
                    
                    if 'pbkdf2_rounds' in pw_salt:
                        pbkdf2_rounds = int(salt['pbkdf2_rounds'])
                        if pbkdf2_rounds>0:
                            password_md5 = binascii.hexlify(hashlib.pbkdf2_hmac('sha256', password_md5_bin, 
                                                            pw_salt['salt'].encode(), pbkdf2_rounds)).decode()
                    
                    password_md5 = self._md5(salt['rnd']+password_md5)
                    
                    login = self._get_json('login', { 'username': self._username,
                                                'password': password_md5 })
                    
                    if(not login or 'success' not in login or not login['success']):
                        logger.warning('Error during login. Password wrong?')
                        return False
                    
                    else:
                        self._logged_in=True
                        return True
                else:
                    return False
            else:
                self._logged_in=True
                self._session = login['session'];
                return True                
        else:
            
            return True
        
    
    def get_client_status(self, clientname):
        
        if not self.login():
            return None
        
        status = self._get_json('status')
        
        if not status:
            return None
        
        if not 'status' in status:
            return None
        
        for client in status['status']:
                
            if (client['name'] == clientname):
                
                return client;
            
        logger.warning('Could not find client status. No permission?')
        return None
    
    def download_installer(self, installer_fn, new_clientname):
        
        if not self.login():
            return False
        
        new_client = self._get_json('add_client', { 'clientname': new_clientname})
        
        if 'already_exists' in new_client:
            
            status = self.get_client_status(new_clientname)
            
            if status == None:
                return False
            
            return self._download_file('download_client', installer_fn,
                                 {'clientid': status['id'] })
        
        
        if not 'new_authkey' in new_client:     
            return False
        
        return self._download_file('download_client', installer_fn,
                             {'clientid': new_client['new_clientid'],
                              'authkey': new_client['new_authkey']
                              })
                
    def add_client(self, clientname):
        
        if not self.login():
            return None
                
        ret = self._get_json('add_client', { 'clientname': clientname})
        if ret==None or 'already_exists' in ret:
            return None
        
        return ret

    
    def get_global_settings(self):
        if not self.login():
            return None
        
        settings = self._get_json('settings', {'sa': 'general'} )
        
        if not settings or not 'settings' in settings:
            return None
        
        return settings['settings']

    def set_global_setting(self, key, new_value):
        if not self.login():
            return False
        
        settings = self._get_json('settings', {'sa': 'general'} )
        
        if not settings or not 'settings' in settings:
            return False
        
        settings['settings'][key] = new_value
        settings['settings']['sa'] = 'general_save'
        
        ret = self._get_json('settings', settings['settings'])
        
        return ret!=None and 'saved_ok' in ret
    
    def get_groups(self):
        if not self.login():
            return None
        
        settings = self._get_json('settings')
        if not settings or \
                'navitems' not in settings or \
                'groups' not in settings['navitems']:
            return []

        return settings['navitems']['groups']

    def get_group(self, groupname):
        if not self.login():
            return None

        groups = self.get_groups()

        for group in groups:
            if group['name'] == groupname:
                return group
        return None

    def add_group(self, groupname):
        
	if not self.login():
	    return None

	ret = self._get_json('settings', { 'sa': 'groupadd', 'name': groupname})

	if ret==None or 'already_exists' in ret:
	    return None

        if not 'added_group' in ret:
            return None
        
        return ret['added_group']

    def del_group(self, groupname):
        
	if not self.login():
	    return None

        group = self.get_group(groupname)
        if not group:
            return group

        groupid = group['id']

	ret = self._get_json('settings', { 'sa': 'groupremove', 'id': groupid})

        if 'delete_ok' not in ret:
            return None

        return ret['delete_ok']

        
    def get_group_settings(self, groupname):
        
        if not self.login():
            return None

        group = self.get_group(groupname)
        if not group:
            return group

        groupid = group['id']

        
        settings = self._get_json('settings', {'sa': 'clientsettings',
                                    't_clientid': -int(groupid)})
        
        if not settings or not 'settings' in settings:
            return None
            
        return settings['settings']

    def set_group_setting(self, groupname, key, new_value):
        if not self.login():
            return False
        
        group = self.get_group(groupname)
        
        if group == None:
            return False
        
        groupid = group['id'];
        
        settings = self._get_json('settings', {'sa': 'clientsettings',
                                    't_clientid': -int(groupid)})
        
        if not settings or not 'settings' in settings:
            return False
        
        settings['settings'][key] = new_value
        settings['settings']['overwrite'] = 'true'
        settings['settings']['sa'] = 'clientsettings_save'
        settings['settings']['t_clientid'] = -int(groupid)
        
        ret = self._get_json('settings', settings['settings'])
        
        return ret!=None and 'saved_ok' in ret

    def get_client_settings(self, clientname):
        
        if not self.login():
            return None
        
        client = self.get_client_status(clientname)
        
        if client == None:
            return None
        
        clientid = client['id'];
        
        settings = self._get_json('settings', {'sa': 'clientsettings',
                                    't_clientid': clientid})
        
        if not settings or not 'settings' in settings:
            return None
            
        return settings['settings']
    
    def set_client_setting(self, clientname, key, new_value):
        if not self.login():
            return False
        
        client = self.get_client_status(clientname)
        
        if client == None:
            return False
        
        clientid = client['id'];
        
        settings = self._get_json('settings', {'sa': 'clientsettings',
                                    't_clientid': clientid})
        
        if not settings or not 'settings' in settings:
            return False
        
        settings['settings'][key] = new_value
        settings['settings']['overwrite'] = 'true'
        settings['settings']['sa'] = 'clientsettings_save'
        settings['settings']['t_clientid'] = clientid
        
        ret = self._get_json('settings', settings['settings'])
        
        return ret!=None and 'saved_ok' in ret
        
    def get_client_authkey(self, clientname):
        
        if not self.login():
            return None
        
        settings = self.get_client_settings(clientname)
        
        if settings:
            return settings['internet_authkey']
        
        return None
    
    def get_server_identity(self):
        
        if not self.login():
            return None
    
        status = self._get_json('status')
        
        if not status:
            return None
        elif not 'server_identity' in status:
            return None
        else:
            return status['server_identity']
    
    def get_status(self):
        if not self.login():
            return None
        
        status = self._get_json('status')
        
        if not status:
            return None
        
        if not 'status' in status:
            return None
        
        return status['status']
    
    def get_livelog(self, clientid = 0):
        if not self.login():
            return None

        log = self._get_json('livelog', {'clientid': clientid, 'lastid': self._lastlogid})

        if not log:
            return None

        if not 'logdata' in log:
            return None

        self._lastlogid = log['logdata'][-1]['id']

        return log['logdata']
      
    def get_usage(self):
        if not self.login():
            return None

        usage = self._get_json('usage')

        if not usage:
            return None

        if not 'usage' in usage:
            return None

        return usage['usage']

    def get_extra_clients(self):
        if not self.login():
            return None
        
        status = self._get_json('status')
        
        if not status:
            return None
        
        if not 'extra_clients' in status:
            return None
        
        return status['extra_clients']
    
    def _start_backup(self, clientname, backup_type):
        
        client_info = self.get_client_status(clientname)
        
        if not client_info:
            return False
        
        ret = self._get_json('start_backup', {'start_client': client_info['id'], 
                                         'start_type': backup_type } );
                                        
        if ( ret==None 
            or 'result' not in ret
            or len(ret['result'])!=1
            or 'start_ok' not in ret['result'][0]
            or not ret['result'][0]['start_ok'] ):
            return False
        
        return True
    
    def start_incr_file_backup(self, clientname):
        return self._start_backup(clientname, 'incr_file');
    
    def start_full_file_backup(self, clientname):
        return self._start_backup(clientname, 'full_file');
    
    def start_incr_image_backup(self, clientname):
        return self._start_backup(clientname, 'incr_image');
    
    def start_full_image_backup(self, clientname):
        return self._start_backup(clientname, 'full_image');
    
    def add_extra_client(self, addr):
        if not self.login():
            return None
        
        ret = self._get_json('status', {'hostname': addr } );
                                        
        if not ret:
            return False
        
        return True
    
    def remove_extra_client(self, ecid):
        if not self.login():
            return None
        
        ret = self._get_json('status', {'hostname': ecid,
                                        'remove': 'true' } );
                                        
        if not ret:
            return False
        
        return True
    
    action_incr_file = 1
    action_full_file = 2
    action_incr_image = 3
    action_full_image = 4
    action_resumed_incr_file = 5
    action_resumed_full_file = 6
    action_file_restore = 8
    action_image_restore = 9
    action_client_update = 10
    action_check_db_integrity = 11
    action_backup_db = 12
    action_recalc_stats = 13
    
    def get_actions(self):
        if not self.login():
            return None
        
        ret = self._get_json('progress')
        
        if not ret or not 'progress' in ret:
            return None
        
        return ret['progress']
    
    def stop_action(self, action):
        if (not 'clientid' in action
            or not 'id' in action):
            return False
        
        if not self.login():
            return None
        
        ret = self._get_json('progress',
                             {'stop_clientid': action['clientid'],
                              'stop_id': action['id']})
        
        if not ret or not 'progress' in ret:
            return False
        
        return True


def get_server_identity():
    """Return server identity."""
    client = Client()
    return client.get_server_identity()


def get_status():
    """Return server identity."""
    client = Client()
    return client.get_status()


def get_global_settings():
    """Return all global settings."""
    client = Client()
    return client.get_global_settings()


def get_global_setting(key):
    """Return a specific global setting."""
    client = Client()
    settings = client.get_global_settings()
    if not settings:
        return None
    elif key not in settings:
        return None
    else:
        return settings[key]


def set_global_setting(key, value):
    """Set a specific global setting."""
    client = Client()
    return client.set_global_setting(key, value)


def get_groups():
    """Return a list with groups."""
    client = Client()
    groups = client.get_groups()
    return groups


def get_group(name):
    """Return a group."""
    client = Client()
    return client.get_group(name)


def add_group(groupname):
    """Add a group."""
    client = Client()
    return client.add_group(groupname)


def del_group(groupname):
    """Add a group."""
    client = Client()
    return client.del_group(groupname)


def get_group_settings(groupname):
    """Return settings for a group."""
    client = Client()
    return client.get_group_settings(groupname)


def set_group_setting(groupname, key, value):
    """Update a group settings."""
    client = Client()
    return client.set_group_setting(groupname, key, value)


def get_client_status(clientname):
    """Return a client settings."""
    client = Client()
    return client.get_client_status(clientname)


def get_client_settings(clientname):
    """Return a client settings."""
    client = Client()
    return client.get_client_settings(clientname)


def set_client_setting(clientname, key, value):
    """Update a client settings."""
    client = Client()
    return client.set_client_setting(clientname, key, value)
