#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import json
import time
import re
import ConfigParser
import shutil
from passlib.hash import sha256_crypt

#import check password server function
from server import PasswordChecker

import signal
import subprocess

INIT_TIME = 3


def check_password(password):
    '''
    password checker adapter
    parameters:
        password - string

    return a Boolean
    '''
    if PasswordChecker(password) == password:
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


def start_proc(command):
    return subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        preexec_fn=os.setsid
    )


def terminate_proc(proc):
    os.killpg(os.getpgid(proc), signal.SIGTERM)


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
            dmn_src_path - daemnon and cmd_manager source absolute path
                default - os.path.join(os.path.dirname(os.path.abspath(__file__)),'/client/')
            svr_src_path - server source absolute path
                default - os.path.join(os.path.dirname(os.path.abspath(__file__)),'/server/')
            dmn_test_dir - test absolute path of folder for inizialization daemon istance ambient.
                for each daemon istance will create a dedicated folder that contain a config directory and a share directory
                default - os.path.join(os.path.expanduser('~'), 'TestEnv')
            svr_usr_datafile - server user svr_usr_datafile absolute path
                default - os.path.join(os.path.dirname(os.path.abspath(__file__)), "server", "user_data.json")
            svr_usr_dir - server abspath path will contain user's synchronized folder
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

    def _start_serverproc(self):
        '''
        start a server subprocess. The proc will be accessible in self.svr_process
        '''
        command = 'python {}'.format(os.path.join(self.svr_src_path, 'server.py'))
        self.svr_process = start_proc(command)
        time.sleep(INIT_TIME)

    def _stop_serverproc(self):
        '''
        stop a running server subprocess
        '''
        if self.svr_process:
            terminate_proc(self.svr_process)

    def _start_daemonproc(self, ist_id):
        '''
        execute inizialization routine for the istance identified by ist_id:
        it will propagate folder structure, config for daemon and server and it will start a daemon subprocess
        '''
        if ist_id in self.dmn_istance_list:
            command = 'cd {}; python {}'.format(
                os.path.join(self.dmn_test_dir, ist_id, 'config'),
                os.path.join(self.dmn_src_path, 'client', 'client_daermon.py')
            )
            self.dmn_istance_list[ist_id]['process'] = start_proc(command)

    def _stop_daemonproc(self, ist_id):
        if ist_id in self.dmn_istance_list and not self.dmn_istance_list[ist_id]['process'].poll():
            terminate_proc(self.dmn_istance_list[ist_id]['process'])

    def _ist_propagation(self, ist_id):
        # istance's folder tree creation
        istance_path = os.path.join(self.dmn_test_dir, ist_id)
        conf_path = os.path.join(istance_path, 'config')
        share_path = os.path.join(istance_path, 'share')
        os.makedirs(istance_path)
        os.makedirs(conf_path)
        os.makedirs(share_path)

        # istance's config file creation
        daemon_ini = ConfigParser.ConfigParser()
        daemon_ini.add_section('cmd')
        daemon_ini.set('cmd', 'host', 'localhost')
        daemon_ini.set('cmd', 'port', self.dmn_port)
        daemon_ini.add_section('daemon_communication')
        daemon_ini.set('daemon_communication', 'snapshot_file_path', 'snapshot_file.json')
        daemon_ini.set('daemon_communication', 'dir_path', share_path)
        daemon_ini.set('daemon_communication', 'server_url', 'localhost')
        daemon_ini.set('daemon_communication', 'server_port', 5000)
        daemon_ini.set('daemon_communication', 'api_prefix', 'API/v1')
        daemon_ini.set('daemon_communication', 'crash_repo_path', os.path.join(conf_path, 'RawBox_crash_report.log'))
        daemon_ini.set('daemon_communication', 'stdout_log_level', "DEBUG")
        daemon_ini.set('daemon_communication', 'file_log_level', "ERROR")
        daemon_ini.add_section('daemon_user_data')
        daemon_ini.set('daemon_user_data', 'username', self.dmn_istance_list[ist_id]['usr'])
        daemon_ini.set('daemon_user_data', 'password', self.dmn_istance_list[ist_id]['psw'])
        daemon_ini.set('daemon_user_data', 'active', self.dmn_istance_list[ist_id]['dmn_rec'])

        with open(os.path.join(conf_path, 'config.ini'), 'w') as f:
            daemon_ini.write(f)
        self.dmn_port += 1

        # istance's void snapshot file creation
        open(os.path.join(conf_path, 'snapshot_file.json'), 'w').write('{}')

        # propagation in server user_data.json
        if self.dmn_istance_list[ist_id]['svr_rec']:
            with open(self.svr_usr_datafile, 'rw') as datafile:
                svr_conf = json.load(datafile)
                svr_conf['users'] = {
                    self.dmn_istance_list[ist_id]['usr']: {
                        "paths": {
                            '': [
                                self.dmn_istance_list[ist_id]['usr'],
                                None,
                                self.sync_time
                            ]
                        },
                        "psw": sha256_crypt.encrypt(self.dmn_istance_list[ist_id]['psw']),
                        "timestamp": self.sync_time,
                    },
                }
                json.dump(svr_conf, datafile)

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
