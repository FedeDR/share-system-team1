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

#import client daemon snapshot manager object
from client import DirSnapshotManager

import string
import random
import hashlib
import signal
import subprocess


def rand_content(size=4, chars=string.ascii_uppercase + string.digits):
    ''' function for random string creation '''

    return ''.join(random.choice(chars) for _ in range(size))


def create_file(folder):
    '''
    function for random file creation in a specific folder.
    return the path of file and the md5 of content
    '''
    while True:
        filename = rand_content()
        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            content = rand_content(10)
            open(filepath, 'w').write(content)
            md5 = hashlib.md5(content).hexdigest()
            return filepath, md5


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
    '''
    start subprocess
    parameters:
        command - shell command to start
    return subprocess object
    '''
    return subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        preexec_fn=os.setsid
    )


def terminate_proc(proc):
    '''
    send SIGTERM to process
    paramenters:
        proc - subprocess object
    '''
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)


def update_srv_userdata_adt(ist_information, svr_datastorage, sync_time, svr_usr_dir):
    '''
    save the init user information on the server userdata storage system
    parameters:
        ist_information - dict with the daemon istance information
            as EnvironmentManager's dmn_istance_list
        svr_datastorage - server storage reference
        sync_time - timestamp of synchronization
    '''
    try:
        svr_conf = json.load(open(svr_datastorage, 'r'))
    except IOError:
        svr_conf = {
            "users": {}
        }

    svr_conf['users'][ist_information['usr']] = {
        "paths": {
            '': [
                ist_information['usr'],
                None,
                sync_time
            ]
        },
        "psw": sha256_crypt.encrypt(ist_information['psw']),
        "timestamp": sync_time,
    }
    if 'svr_filelist' in ist_information:
        shutil.copytree(
            ist_information['share_path'],
            os.path.join(svr_usr_dir, ist_information['usr']))
        svr_conf['users'][ist_information['usr']]['paths'].update(
            ist_information['svr_filelist'])
    json.dump(svr_conf, open(svr_datastorage, 'w'))


def create_ist_conf_file(ist_information):
    '''
    create a daemon config.ini file in the configuration path
    '''
    daemon_ini = ConfigParser.ConfigParser()
    daemon_ini.add_section('cmd')
    daemon_ini.set('cmd', 'host', 'localhost')
    daemon_ini.set('cmd', 'port', ist_information['dmn_port'])
    daemon_ini.add_section('daemon_communication')
    daemon_ini.set('daemon_communication', 'snapshot_file_path', 'snapshot_file.json')
    daemon_ini.set('daemon_communication', 'dir_path', ist_information['share_path'])
    daemon_ini.set('daemon_communication', 'server_url', 'localhost')
    daemon_ini.set('daemon_communication', 'server_port', 5000)
    daemon_ini.set('daemon_communication', 'api_prefix', 'API/v1')
    daemon_ini.set('daemon_communication', 'crash_repo_path', os.path.join(ist_information['conf_path'], 'RawBox_crash_report.log'))
    daemon_ini.set('daemon_communication', 'stdout_log_level', "DEBUG")
    daemon_ini.set('daemon_communication', 'file_log_level', "ERROR")
    daemon_ini.add_section('daemon_user_data')
    daemon_ini.set('daemon_user_data', 'username', ist_information['usr'])
    daemon_ini.set('daemon_user_data', 'password', ist_information['psw'])
    daemon_ini.set('daemon_user_data', 'active', ist_information['dmn_rec'])

    with open(os.path.join(ist_information['conf_path'], 'config.ini'), 'w') as f:
        daemon_ini.write(f)


def create_spanshot_file(share_path, timestamp, snap_path, synced=True):
    open(snap_path, 'w').write('{}')

    if synced:
        snap_manager = DirSnapshotManager(snap_path, share_path)
        snap_manager.save_snapshot(timestamp)


class InputError(Exception):
    '''
    Exception raised for errors in the input parameters
    '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class EnvironmentManager(object):

    def __init__(
        self,
        dmn_src_path=os.path.join(os.getcwd(), 'client'),
        svr_src_path=os.path.join(os.getcwd(), 'server'),
        dmn_test_dir=os.path.join(os.path.expanduser('~'), 'TestEnv'),
        svr_usr_datafile=os.path.join(os.getcwd(), "server", "user_data.json"),
        svr_usr_dir=os.path.join(os.getcwd(), 'server', 'user_dirs')
    ):
        '''
        Create a folder tree for the execution of system test.
        patameters:
            dmn_src_path - daemnon and cmd_manager source absolute path
                default - os.path.join(os.getcwd(),'/client/')
            svr_src_path - server source absolute path
                default - os.path.join(os.getcwd(),'/server/')
            dmn_test_dir - test absolute path of folder for inizialization daemon istance ambient.
                for each daemon istance will create a dedicated folder that contain a config directory and a share directory
                default - os.path.join(os.path.expanduser('~'), 'TestEnv')
            svr_usr_datafile - server user svr_usr_datafile absolute path
                default - os.path.join(os.getcwd(), "server", "user_data.json")
            svr_usr_dir - server abspath path will contain user's synchronized folder
                default - os.path.join(os.getcwd(), 'server/user_dirs/')

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

        self.sync_time = time.time()

        self.dmn_port = 6666
        self.init_time = 3

        #reset base environment tree
        if os.path.exists(self.dmn_test_dir):
            shutil.rmtree(self.dmn_test_dir)

        if os.path.exists(self.svr_usr_dir):
            shutil.rmtree(self.svr_usr_dir)

        os.makedirs(self.dmn_test_dir)
        os.makedirs(self.svr_usr_dir)

    def _start_serverproc(self):
        '''
        start a server subprocess. The proc will be accessible in self.svr_process
        '''
        command = 'python {}'.format(os.path.join(self.svr_src_path, 'server.py'))
        self.svr_process = start_proc(command)

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
                os.path.join(self.dmn_src_path, 'client_daemon.py')
            )
            self.dmn_istance_list[ist_id]['process'] = start_proc(command)

    def _stop_daemonproc(self, ist_id):
        if ist_id in self.dmn_istance_list and not self.dmn_istance_list[ist_id]['process'].poll():
            terminate_proc(self.dmn_istance_list[ist_id]['process'])

    def _ist_propagation(self, ist_id):
        # istance's config file creation
        create_ist_conf_file(self.dmn_istance_list[ist_id])

        # istance's stapshot file creation
        create_spanshot_file(
            self.dmn_istance_list[ist_id]['share_path'],
            self.sync_time,
            os.path.join(self.dmn_istance_list[ist_id]['conf_path'], 'snapshot_file.json'),
            self.dmn_istance_list[ist_id]['self_sync'])

        # propagation in server user_data.json
        if self.dmn_istance_list[ist_id]['svr_rec']:
            update_srv_userdata_adt(
                self.dmn_istance_list[ist_id],
                self.svr_usr_datafile,
                self.sync_time,
                self.svr_usr_dir)

    def start_test_environment(self):
        # daemon settings propagation
        for ist_id in self.dmn_istance_list:
            self._ist_propagation(ist_id)

        # start server process
        self._start_serverproc()
        time.sleep(self.init_time)

        # start daemon process
        for ist_id in self.dmn_istance_list:
            self._start_daemonproc(ist_id)

    def stop_test_environment(self):
        # stop daemon process
        for ist_id in self.dmn_istance_list:
            self._stop_daemonproc(ist_id)

        #stop server process
        self._stop_serverproc()

    def flush(self):
        '''
        remove environment file structure
        '''
        try:
            shutil.rmtree(self.dmn_test_dir)
        except OSError:
            pass
        try:
            shutil.rmtree(self.svr_usr_dir)
        except OSError:
            pass
        try:
            os.remove(self.svr_usr_datafile)
        except OSError:
            pass

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
                can be True only if svr_rec is True
                default - False
        return: string istance id
        '''
        if not ist_id:
            condition = True
            while condition:
                ist_id = 'ist_{}'.format(self.inc_id)
                if ist_id not in self.dmn_istance_list:
                    condition = False
                self.inc_id += 1
        else:
            if ist_id in self.dmn_istance_list:
                raise InputError('id not valid')

        self.dmn_istance_list[ist_id] = {}
        self.dmn_istance_list[ist_id]['dmn_port'] = self.dmn_port
        self.dmn_port += 1

        if svr_rec:
            if check_password(credential['psw']) and check_username(credential['usr']):
                self.dmn_istance_list[ist_id]['usr'] = credential['usr']
                self.dmn_istance_list[ist_id]['psw'] = credential['psw']
                self.dmn_istance_list[ist_id]['dmn_rec'] = dmn_rec
            else:
                raise InputError('credential not valid')
        else:
            self.dmn_istance_list[ist_id]['usr'] = None
            self.dmn_istance_list[ist_id]['psw'] = None
            self.dmn_istance_list[ist_id]['dmn_rec'] = False
        self.dmn_istance_list[ist_id]['svr_rec'] = svr_rec

        self.sync_dmn_share(ist_id)

        istance_path = os.path.join(self.dmn_test_dir, ist_id)
        conf_path = os.path.join(istance_path, 'config')
        share_path = os.path.join(istance_path, 'share')
        self.dmn_istance_list[ist_id]['root_path'] = istance_path
        self.dmn_istance_list[ist_id]['conf_path'] = conf_path
        self.dmn_istance_list[ist_id]['share_path'] = share_path

        if os.path.exists(istance_path):
            shutil.rmtree(istance_path)
        if os.path.exists(conf_path):
            shutil.rmtree(conf_path)
        if os.path.exists(share_path):
            shutil.rmtree(share_path)
        os.makedirs(istance_path)
        os.makedirs(conf_path)
        os.makedirs(share_path)

        return ist_id

    def sync_dmn_share(self, ist_id, self_sync=True, server_sync=True):
        '''
        synchronize istance share folder in the configuration file.
        Attributes:
            ist_id - istance id
            self_sync - boolean. if true it will synchronize the snapshot file
                default True
            server_sync - boolean. if true it will synchronize the server user data
                default True
        '''
        self.dmn_istance_list[ist_id]['self_sync'] = self_sync
        self.dmn_istance_list[ist_id]['server_sync'] = server_sync

    def add_rndfile_to_ist(self, ist_id, num_file=10, relpath=None):
        '''
        add text random files to specified istance's relpath
        '''
        if relpath:
            dst_path = os.path.join(
                self.dmn_istance_list[ist_id]['share_path'],
                relpath)
        else:
            dst_path = self.dmn_istance_list[ist_id]['share_path']

        if 'svr_filelist' not in self.dmn_istance_list[ist_id]:
            self.dmn_istance_list[ist_id]['svr_filelist'] = {}

        for e_file in range(num_file):
            filename, full_path, md5 = create_file(dst_path)
            rel_path = os.path.relpath(
                full_path,
                self.dmn_istance_list[ist_id]['share_path'])

            if filename not in self.dmn_istance_list[ist_id]['svr_filelist']:
                self.dmn_istance_list[ist_id]['svr_filelist'][rel_path] = []

            self.dmn_istance_list[ist_id]['svr_filelist'][rel_path].append(
                os.path.join(self.dmn_istance_list[ist_id]['usr'], rel_path))
            self.dmn_istance_list[ist_id]['svr_filelist'][rel_path].append(md5)
            self.dmn_istance_list[ist_id]['svr_filelist'][rel_path].append(
                self.sync_time)


