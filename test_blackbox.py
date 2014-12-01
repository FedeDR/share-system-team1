#!/usr/bin/env python
#-*- coding: utf-8 -*-

from systemtest import BlackBoxTest, rand_content
import unittest
import os
import shutil


class IntegrationTest(BlackBoxTest):

    def test_mass_copy(self):
        ist_id = self.env.add_dmn_istance(
            credential={'usr': 'test@test.it', 'psw': 'TestPsw1<'},
            svr_rec=True,
            dmn_rec=True)
        src_path = self.env.add_fld_to_ist(ist_id, 'src_path')
        self.env.add_rndfile_to_ist(ist_id, relpath='src_path')
        dst_path = os.path.join(
            self.env.get_rawbox_dir(ist_id),
            'dst_path')

        self.env.start_test_environment()

        shutil.copytree(
            src_path,
            dst_path)

        self._check_folder()

    def test_mass_move(self):
        ist_id = self.env.add_dmn_istance(
            credential={'usr': 'test@test.it', 'psw': 'TestPsw1<'},
            svr_rec=True,
            dmn_rec=True)
        src_path = self.env.add_fld_to_ist(ist_id, 'src_path')
        self.env.add_rndfile_to_ist(ist_id, relpath='src_path')
        dst_path = os.path.join(
            self.env.get_rawbox_dir(ist_id),
            'dst_path')

        self.env.start_test_environment()

        shutil.move(
            src_path,
            dst_path)

        self._check_folder()

    def test_mass_delete(self):
        ist_id = self.env.add_dmn_istance(
            credential={'usr': 'test@test.it', 'psw': 'TestPsw1<'},
            svr_rec=True,
            dmn_rec=True)
        del_folder = self.env.add_fld_to_ist(ist_id, 'del_folder')
        self.env.add_rndfile_to_ist(ist_id, relpath='del_folder')

        self.env.start_test_environment()

        shutil.rmtree(del_folder)

        self._check_folder()

    def test_mass_create(self):
        ist_id = self.env.add_dmn_istance(
            credential={'usr': 'test@test.it', 'psw': 'TestPsw1<'},
            svr_rec=True,
            dmn_rec=True)

        self.env.start_test_environment()

        self.env.add_rndfile_to_ist(ist_id)

        self._check_folder()

    def test_mass_modify(self):
        ist_id = self.env.add_dmn_istance(
            credential={'usr': 'test@test.it', 'psw': 'TestPsw1<'},
            svr_rec=True,
            dmn_rec=True)

        self.env.add_rndfile_to_ist(ist_id)

        self.env.start_test_environment()

        for root, dirs, files in os.walk(self.env.get_rawbox_dir(ist_id)):
            for f in files:
                filepath = os.path.join(root, f)
                open(filepath, 'w').write(rand_content(15))

        self._check_folder()

    def test_new_daemon(self):
        ist_id = self.env.add_dmn_istance(
            credential={'usr': 'test@test.it', 'psw': 'TestPsw1<'},
            svr_rec=True,
            dmn_rec=False)

        self.env.add_rndfile_to_ist(ist_id)
        self.env.sync_dmn_share(
            ist_id,
            file_dmn_sync=False,
            file_svr_sync=True,
            snap_sync=False)

        self.env.start_test_environment()
        self._check_folder()


if __name__ == "__main__":
    unittest.main()
