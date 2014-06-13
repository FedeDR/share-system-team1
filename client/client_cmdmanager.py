#!/usr/bin/env python
#-*- coding: utf-8 -*-

import platform
import getpass
import cmd
import sys
import re
import os

from communicaton_system import CmdMessageClient
import asyncore
from client_daemon import load_config

sys.path.insert(0, 'temp_mock/')
import fakerequests as requests

sys.path.insert(0, 'utility/')
from colorMessage import Message

class RawBoxCmd(cmd.Cmd):
	"""RawBox command line interface"""

	intro = Message().color('INFO','##### Hello guy!... or maybe girl, welcome to RawBox ######\ntype ? to see help\n\n')
	doc_header = Message().color('INFO',"command list, type ? <topic> to see more :)")
	prompt = Message().color('HEADER', '(RawBox) ')
	ruler = Message().color('INFO','~')

	def __init__(self):
		cmd.Cmd.__init__(self)
		conf = load_config()
		self.comm_sock = CmdMessageClient(conf['cmd_host'], int(conf['cmd_port']), self)
		
	def _create_user(self, username = None):
		"""create user if not exists"""
		command_type = 'create_user'
		  
		if not username:
			username  = raw_input('insert your user name: ')

		password = getpass.getpass('insert your password: ')
		rpt_password = getpass.getpass('Repeat your password: ')
		
		while password != rpt_password:	
			Message('WARNING', 'password not matched')
			password = getpass.getpass('insert your password: ')
			rpt_password = getpass.getpass('Repeat your password: ')

		email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
		email = raw_input('insert your user email: ')
		
		while not email_regex.match(email):
			Message('WARNING', 'invalid email')
			email = raw_input('insert your user email: ')

		param = 	{	
					'user': username, 
					'psw': password, 
					'email': email
				}

		self.comm_sock.send_message(command_type, param)
		self.comm_sock.handle_read()

	def _create_group(self, *args):
		"""create group/s"""
		command_type = 'create_group'
		param = {'group': args}

		self.comm_sock.send_message(command_type, param)
		self.comm_sock.handle_read()

	def _add_user(self, *args):
		"""add user/s to a group """
		command_type = 'add_to_group'
		param = {'user': args}

		self.comm_sock.send_message(command_type, param)
		self.comm_sock.handle_read()

	def _add_admin(self, *args):
		"""add admin/s to a group """
		command_type = 'add_admin'
		param = {'admin': args}

		self.comm_sock.send_message(command_type, param)
		self.comm_sock.handle_read()

	def error(self, *args):
		print "hum... unknown command, please type help"

	def do_add(self, line):
		"""
	add user <*user_list> group=<group_name> (add a new RawBox user to the group)
	add admin <*user_list> group=<group_name> (add a new RawBox user as admin to the group)
		"""
		if line:
			command = line.split()[0]
			arguments = line.split()[1:]
			{
				'user': self._add_user,
				'admin': self._add_admin,
			}.get(command, self.error)(arguments)
		else: 
			Message('INFO', self.do_add.__doc__)

	def do_create(self, line):
		""" 
	create user <name>  (create a new RawBox user)
	create group <name> (create a new shareable folder with your friends)	
		"""
		if line:
			command = line.split()[0]
			arguments = line.split()[1:]
			{
				'user': self._create_user,
			 	'group': self._create_group,
			}.get(command, self.error)(arguments)
		else: 
			Message('INFO', self.do_create.__doc__)

	def do_q(self, line = None):
		""" exit from RawBox"""
		if raw_input('[Exit] are you sure? y/n ') == 'y':
			return True

	def do_quit(self, line = None):
		""" exit from RawBox"""
		if raw_input('[Exit] are you sure? y/n ') == 'y':
			return True

	def print_response(self, response):
		print 'Response for "{}" command\nresult: {}'.format(response['request'],response['body'])


def main():
	if platform.system() == 'Windows':
		os.system('cls')
	else:
		os.system('clear')

	try:
		RawBoxCmd().cmdloop()
	except KeyboardInterrupt:
		print "[exit]"

if __name__ == '__main__':
	main()
