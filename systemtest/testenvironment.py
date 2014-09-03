#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os


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
        self.dmn_istance_list = []
        self.started_process = []

        self.init_time = 5
