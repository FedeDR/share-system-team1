#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import json
import time
import shutil
#import check password server function
from ...server.server import PasswordChecker as password_checker

def check_password(password):
    '''
    password checker adapter
    parameters:
        password - string

    return a Boolean
    '''
    if password_checker(password) == password:
        return True
    else:
        return False


def check_username(username):
    '''
    username checker adapter
    parameters:
        username - string

    retunr a Boolean
    '''
    email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
    return email_regex.match(username)


class EnvironmentManager(object):
    
    def __init__(
        self,
        dmn_src_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '/client'),
        svr_src_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '/server/'),
        dmn_test_dir=os.path.join(os.path.expanduser('~'), 'TestEnv'),
        svr_usr_datafile=os.path.join(os.path.dirname(os.path.abspath(__file__)), "server", "user_data.json"),
        svr_usr_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server', 'user_dirs/')
    ):
        '''
        Create a folder tree for the execution of system test.
        patameters:
            dmn_src_path - daemnon and cmd_manager source path
                default - os.path.join(os.path.dirname(os.path.abspath(__file__)),'/client/')
            svr_src_path - server source path
                default - os.path.join(os.path.dirname(os.path.abspath(__file__)),'/server/')
            dmn_test_dir - test folder for inizialization daemon istance ambient.
                for each daemon istance will create a dedicated folder that contain a config directory and a share directory
                default - os.path.join(os.path.expanduser('~'), 'TestEnv')
            svr_usr_datafile - path of server user svr_usr_datafile
                default - os.path.join(os.path.dirname(os.path.abspath(__file__)), "server", "user_data.json")
            svr_usr_dir - server path will contain user's synchronized folder
                default - os.path.join(os.path.dirname(os.path.abspath(__file__), 'server/user_dirs/')

        Daemon's folder structure:
            |root
            -dmn_test_dir-
                        -istance_id-
                                    -config-
                                            -config.ini
                                            -snapshot.json
                                            -RawBox_crash_report.log
                                    -share-
                                            -file_to_share
        Server's folder structure:
            |root
            -svr_usr_dir-
                        -username-
                                 -file_to_shar
        '''
        self.dmn_src_path = dmn_src_path
        self.svr_src_path = svr_src_path
        self.dmn_test_dir = dmn_test_dir
        self.svr_usr_datafile = svr_usr_datafile
        self.svr_usr_dir = svr_usr_dir
        self.dmn_istance_list = {}
        self.inc_id = 1
        self.started_process = []

        self.sync_time = time.time()

        self.dmn_port = 6666
        self.init_time = 5

        #reset base environment tree
        if os.path.exists(self.dmn_test_dir):
            shutil.rmtree(self.dmn_test_dir)

        if os.path.exists(self.svr_usr_dir):
            shutil.rmtree(self.svr_usr_dir)

        os.makedirs(self.dmn_test_dir)
        os.makedirs(self.svr_usr_dir)

        with open(self.svr_usr_datafile, 'w') as datafile:
            to_save = {
                "users": {}
            }
            json.dump(to_save, datafile)

    def add_dmn_istance(self, ist_id=None, credential=None, svr_rec=False, dmn_rec=False):
        '''
        add an istance at the daemon istance list
        parameters:
            id - identifier of istance
                default - None, the id will be automatically assigned
            credential - dict contain compatible username ("usr" key) and compatible password ("psw" key) of istance
                exemple {"usr": "user@test.com", "psw": "Password<3"}
                if svr_rec and dmn_rec are both False this var will be ignore
                default - None, create a void istance
            svr_rec - Boolean, mean the istance is registered on server yet.
                default - False
            dmn_rec - Boolean, mean the istance is logged in yet
                can be True only if svr_rec are True
                default - False
        '''
        if not ist_id:
            condition = True
            while condition:
                ist_id = ''.join(['ist_', self.inc_id])
                if ist_id not in self.dmn_istance_list:
                    condition = False
                self.inc_id += 1
        else:
            if ist_id in self.dmn_istance_list:
                raise

        self.dmn_istance_list[ist_id] = {
            'svr_rec': svr_rec,
            'dmn_rec': dmn_rec,
        }

        if svr_rec or dmn_rec:
            if check_password(credential['psw']) and check_username(credential['usr']):
                self.dmn_istance_list[ist_id]['usr'] = credential['usr']
                self.dmn_istance_list[ist_id]['psw'] = credential['psw']
            else:
                self.dmn_istance_list[ist_id]['usr'] = None
                self.dmn_istance_list[ist_id]['psw'] = None
