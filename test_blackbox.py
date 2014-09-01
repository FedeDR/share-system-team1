#!/usr/bin/env python
#-*- coding: utf-8 -*-

import subprocess
import time
import os
import shutil
import random
import ConfigParser
from passlib.hash import sha256_crypt
import json
import unittest
import filecmp
import hashlib
import string

import select
import fcntl

INIT_TIME = 5
TRY_TIME = 5
MAX_TRY = 3

PROCESS = []

TEST_ENV_DIR = os.path.join(os.path.expanduser('~'), 'TestEnv')

# test user information:
# user: user1@test.it
#     istance1: istance sinked with server
#     istance2: istance of daemon not sinked with server

CONF_USERS = {
    'istance1': {
        'username': 'user1@test.it',
        'password': 'password',
        'conf_path': os.path.join(TEST_ENV_DIR, 'istance1/user1@test.it_config'),
        'share_path': os.path.join(TEST_ENV_DIR, 'istance1/user1@test.it_share'),
        'dmn_command': 'cd {}; python {}/client/client_daemon.py'.format(
            os.path.join(TEST_ENV_DIR, 'istance1/user1@test.it_config'),
            os.path.dirname(os.path.abspath(__file__)))
    },
    'istance2': {
        'username': 'user1@test.it',
        'password': 'password',
        'conf_path': os.path.join(TEST_ENV_DIR, 'istance2/user1@test.it_config'),
        'share_path': os.path.join(TEST_ENV_DIR, 'istance2/user1@test.it_share'),
        'dmn_command': 'cd {}; python {}/client/client_daemon.py'.format(
            os.path.join(TEST_ENV_DIR, 'istance2/user1@test.it_config'),
            os.path.dirname(os.path.abspath(__file__)))
    }
}

# local server sincronized test directory for user "user1"
SERVER_USER_DATA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "server", "user_data.json")
SERVER_USER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'server/user_dirs/',
    'user1@test.it')

SYNC_TIME = time.time()


def non_block_readline(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return output.readline()
    except IOError:
        pass


def check_folder(src_folder, dst_folder):
    for root, dirs, files in os.walk(src_folder):
        for f in files:
            full_src_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_src_path, src_folder)
            full_dst_path = os.path.join(dst_folder, rel_path)
            try:
                result = filecmp.cmp(full_src_path, full_dst_path)
            except OSError:
                result = False
            if not result:
                print "---"
                print "check propagation for: {}".format(rel_path)
                print "from: {}".format(full_src_path)
                print "to: {}".format(full_dst_path)
                return result
    return result


def check_propagation(first_folder, second_folder):
    '''
    check identity betwen two specific folders contenute
    '''
    # direct check
    if not check_folder(first_folder, second_folder):
        return False

    # reverse check
    if not check_folder(second_folder, first_folder):
        return False

    return True


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


def create_folder_tree(main_path, user):
    folders = ['mass_copy', 'mass_move', 'mass_delete', 'mass_modify']
    client_snap = {}
    svr_filelist = {}
    svr_filelist[''] = [
        user,
        None,
        SYNC_TIME
    ]

    for folder in folders:
        os.makedirs(os.path.join(main_path, folder))
        svr_filelist[folder] = [
            '/'.join([user, folder]),
            None,
            SYNC_TIME
        ]
        for i in range(10):
            full_path, md5 = create_file(os.path.join(main_path, folder))
            rel_path = os.path.relpath(full_path, main_path)
            if md5 in client_snap:
                client_snap[md5].append(rel_path)
            else:
                client_snap[md5] = [rel_path]

            svr_filelist[rel_path] = [
                '/'.join([user, rel_path]),
                md5,
                SYNC_TIME
            ]

    return client_snap, svr_filelist


def create_test_environment():
    if os.path.exists(TEST_ENV_DIR):
        shutil.rmtree(TEST_ENV_DIR)

    if os.path.exists(SERVER_USER_DIR):
        shutil.rmtree(SERVER_USER_DIR)

    os.makedirs(TEST_ENV_DIR)
    os.makedirs(CONF_USERS['istance1']['conf_path'])
    os.makedirs(CONF_USERS['istance1']['share_path'])
    os.makedirs(CONF_USERS['istance2']['conf_path'])
    os.makedirs(CONF_USERS['istance2']['share_path'])

    client_snap, svr_filelist = create_folder_tree(
        CONF_USERS['istance1']['share_path'],
        CONF_USERS['istance1']['username'])
    shutil.copytree(CONF_USERS['istance1']['share_path'], SERVER_USER_DIR)

    # Create daemon config
    port = 6666
    for k, v in CONF_USERS.items():
        daemon_ini = ConfigParser.ConfigParser()
        daemon_ini.add_section('cmd')
        daemon_ini.set('cmd', 'host', 'localhost')
        daemon_ini.set('cmd', 'port', port)
        daemon_ini.add_section('daemon_communication')
        daemon_ini.set('daemon_communication', 'snapshot_file_path', 'snapshot_file.json')
        daemon_ini.set('daemon_communication', 'dir_path', v['share_path'])
        daemon_ini.set('daemon_communication', 'server_url', 'localhost')
        daemon_ini.set('daemon_communication', 'server_port', 5000)
        daemon_ini.set('daemon_communication', 'api_prefix', 'API/v1')
        daemon_ini.set('daemon_communication', 'crash_repo_path', os.path.join(v['conf_path'], 'RawBox_crash_report.log'))
        daemon_ini.set('daemon_communication', 'stdout_log_level', "DEBUG")
        daemon_ini.set('daemon_communication', 'file_log_level', "ERROR")
        daemon_ini.add_section('daemon_user_data')
        daemon_ini.set('daemon_user_data', 'username', v['username'])
        daemon_ini.set('daemon_user_data', 'password', v['password'])
        daemon_ini.set('daemon_user_data', 'active', 'True')

        with open(os.path.join(v['conf_path'], "config.ini"), "w") as f:
            daemon_ini.write(f)
        port += 1

    #snapshot for sinked instance
    with open(os.path.join(CONF_USERS['istance1']['conf_path'], "snapshot_file.json"), "w") as f:
        for k, v in client_snap.items():
            v.sort()
        snap_list = sorted(list(client_snap.items()))
        hashlib.md5(str(snap_list)).hexdigest()
        snap = {
            "timestamp": SYNC_TIME,
            "snapshot": hashlib.md5(str(snap_list)).hexdigest(),
        }
        json.dump(snap, f)

    # Create server config
    svr_conf = {}
    svr_conf['users'] = {
        CONF_USERS['istance1']['username']: {
            "paths": svr_filelist,
            "psw": sha256_crypt.encrypt(CONF_USERS['istance1']['password']),
            "timestamp": SYNC_TIME,
        },
    }
    json.dump(svr_conf, open(SERVER_USER_DATA, 'w'))

    # Start subprocess
    svr_process = subprocess.Popen(
        "cd server; python server.py",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    print "server PID: {}".format(svr_process.pid)
    time.sleep(2)

    dmn_process = subprocess.Popen(
        CONF_USERS['istance1']['dmn_command'],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    print "daemon PID: {}".format(dmn_process.pid)

    time.sleep(INIT_TIME)
    return svr_process, dmn_process


class BlackBoxTest(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        for proc in PROCESS:
            print '---'
            print proc.pid
            print proc.poll()
            proc.kill()
            print proc.poll()

        shutil.rmtree(TEST_ENV_DIR)
        shutil.rmtree(SERVER_USER_DIR)

    def _check_folder(self, shared_path, server_path):
        retry = 0
        while True:
            print " try: {}".format(retry)
            time.sleep(TRY_TIME)
            try:
                self.assertTrue(
                    check_propagation(
                        shared_path,
                        server_path))
                break
            except AssertionError:
                if retry >= MAX_TRY:
                    raise
                else:
                    retry += 1

    def test_mass_copy(self):
        src_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_copy')
        dst_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_copy_dst')
        shutil.copytree(
            src_folder,
            dst_folder)

        self._check_folder(
            CONF_USERS['istance1']['share_path'],
            SERVER_USER_DIR)

    def test_mass_move(self):
        src_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_move')
        dst_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_move_dst')
        os.makedirs(dst_folder)
        shutil.move(
            src_folder,
            dst_folder)

        self._check_folder(
            CONF_USERS['istance1']['share_path'],
            SERVER_USER_DIR)

    def test_mass_delete(self):
        del_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_delete')
        shutil.rmtree(del_folder)
        
        self._check_folder(
            CONF_USERS['istance1']['share_path'],
            SERVER_USER_DIR)

    def test_mass_create(self):
        crt_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_create')
        os.makedirs(crt_folder)
        for i in range(15):
            create_file(crt_folder)

        self._check_folder(
            CONF_USERS['istance1']['share_path'],
            SERVER_USER_DIR)

    def test_mass_modify(self):
        mod_folder = os.path.join(
            CONF_USERS['istance1']['share_path'],
            'mass_modify')
        for root, dirs, files in os.walk(mod_folder):
            for f in files:
                print f
                filepath = os.path.join(root, f)
                open(filepath, 'w').write(rand_content(15))

        self._check_folder(
            CONF_USERS['istance1']['share_path'],
            SERVER_USER_DIR)

    def test_new_client(self):
        dmn_process = subprocess.Popen(
            CONF_USERS['istance2']['dmn_command'],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        print "daemon PID: {}".format(dmn_process.pid)
        PROCESS.append(dmn_process)
        time.sleep(INIT_TIME)

        self._check_folder(
            CONF_USERS['istance2']['share_path'],
            SERVER_USER_DIR)


if __name__ == "__main__":
    
    svr_process, dmn_process = create_test_environment()
    PROCESS.append(svr_process)
    PROCESS.append(dmn_process)
    
    test = True

    if test:
        unittest.main()
    else:
        out_list = []
        read_comm = {}

        for proc in PROCESS:
            out_list.append(proc.stdout.fileno())
            read_comm[proc.stdout.fileno()] = proc.stdout
            out_list.append(proc.stderr.fileno())
            read_comm[proc.stderr.fileno()] = proc.stderr

        for k in read_comm:
            print 'fileno: {}'.format(k)

        while True:
            try:
                r, w, e = select.select(out_list, [], [], 5)
            except select.error, err:
                    raise

            for fd in r:
                message = non_block_readline(read_comm.get(fd, None)).strip()
                if message != "":
                    print "read message: {}".format(fd)
                    print message
                    print "---"
