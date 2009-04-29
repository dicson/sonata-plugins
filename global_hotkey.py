#!/usr/bin/env python

### BEGIN PLUGIN INFO
# [plugin]
# plugin_format: 0, 0, 0
# name: Global hotkey.
# version: 0, 0, 0
# description: Global hotkey support.Requires python-Xlib.
# author: Fomin Denis
# author_email: fominde@gmail.com
# url: http://sonata.berlios.de
# [capabilities]
# enablables: on_enable
### END PLUGIN INFO

from gettext import gettext as _
import subprocess
import gtk
from gobject import source_remove,io_add_watch

try:
	from Xlib.display import Display
	from Xlib import X
except ImportError:
	X = None


class XlibKeys(object):
	def __init__(self):
		# keyb = 'name':[keyname,keycode,shift,ctrl,alt,mod1,mod2,callback,callback-arguments]
		self.keyb = {'play':		  ['exclam', 10, 1, 1, 0, 1, 0, 'run_command','"play"'],
					 'stop':		  ['numbersign', 12, 1, 1, 0, 1, 0, 'run_command','"stop"'],
					 'pause':         ['at', 11, 1, 0, 0, 1, 0, 'run_command','"pause"'],
					 'next':          ['greater', 60, 1, 0, 0, 1, 0, 'run_command','"next"'],
					 'prev':          ['less', 59, 1, 0, 0, 1, 0, 'run_command','"prev"'],
					 }

		self.listen()

	def ButtonHit(self,event):
		for i in self.keyb.values():
			if i[1] == event:
				eval (i[7]+'('+i[8]+')')

	def freeKey(self):
		source_remove(self.listener)
		self.grabKey('free')

	def grabKey(self,action):
		for key in self.keyb.keys():
			if self.keyb[key][0] != 'not defined':
				maske = ''
				if self.keyb[key][2] == 1:
					maske += '|X.ShiftMask'
				if self.keyb[key][3] == 1:
					maske += '|X.ControlMask'
				if self.keyb[key][4] == 1:
					maske += '|X.Mod1Mask'
				if self.keyb[key][5] == 1:
					maske += '|X.Mod2Mask'
				if self.keyb[key][6] == 1:
					maske += '|X.Mod3Mask'

				def checkmask(maske):
					# make sure the mask is valid
					if maske != '':
						amaske = maske.lstrip('|')
						return eval(amaske)
					else:
						return X.AnyModifier

				if action == 'grab':
					self.root.grab_key(self.keyb[key][1], checkmask(maske),  1,X.GrabModeAsync, X.GrabModeAsync)
				elif action == 'free':
					self.root.ungrab_key(self.keyb[key][1], checkmask(maske))
					self.disp.flush()

	def listen(self):
		self.disp = Display()
		self.root = self.disp.screen().root
		self.root.change_attributes(event_mask = X.KeyPressMask)
		self.grabKey('grab')

		def checkKey(arg1,arg2):
			#print arg1,arg2
			event = self.disp.next_event()
			if event.type == X.KeyPress:
				self.ButtonHit(event.detail)
			return True

		self.listener = io_add_watch(self.disp, 1 ,checkKey)
		self.disp.pending_events()

def on_enable(state):
	if state:
		if not X:
			print 'Python-xlib library is not available. '
		global a
		a = XlibKeys()
	else:
		a.freeKey()

def run_command(action):
	print action
	p = subprocess.Popen("sonata " + action, shell=True)
