#!/usr/bin/env python

### BEGIN PLUGIN INFO
# [plugin]
# plugin_format: 0, 0
# name: Global hotkey
# version: 0, 0, 1
# description: Global hotkey support.Requires python-Xlib. Suggests mpDris plugin for seek commands
# author: Fomin Denis
# author_email: fominde@gmail.com
# url:
# [capabilities]
# enablables: on_enable
# configure: on_configure
### END PLUGIN INFO

import subprocess, gtk, ConfigParser, os

from gobject import source_remove,io_add_watch
import ConfigParser
import dbus

try:
	from Xlib.display import Display
	from Xlib import X
except ImportError:
	X = None

class XlibKeys(object):
	def __init__(self):
		# keyb = 'name':[keyname,keycode,shift,ctrl,alt,mod1,mod2,callback,callback-arguments]
		self.action = ['play', 'stop', 'pause', 'next', 'prev', 'pp','repeat', 'random', 'seek forward', 'seek backward' ]
		self.keyb = {'play':	['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"play"'],
					 'stop':	['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"stop"'],
					 'pause':   ['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"pause"'],
					 'next':	['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"next"'],
					 'prev':	['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"prev"'],
					 'pp':	  ['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"pp"'],
					 'repeat':  ['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"repeat"'],
					 'random':  ['not defined', 0, 0, 0, 0, 0, 0, 'run_command','"random"'],
					 'seek forward':  ['not defined', 0, 0, 0, 0, 0, 0, 'seek','"forward"'],
					 'seek backward':  ['not defined', 0, 0, 0, 0, 0, 0, 'seek','"backward"'],
					 }
		"""Load configuration from file"""
		conf = ConfigParser.ConfigParser()
		if os.path.isfile(os.path.expanduser('~/.config/sonata/Global hotkey')):
			conf.read(os.path.expanduser('~/.config/sonata/Global hotkey'))
			load_vars = conf.items('DEFAULT')
			for key in conf.items('DEFAULT'):
				z = key[1].strip("[]").split(', ')
				z[0] = z[0].replace("'", '')
				z[1] = int(z[1])
				z[2] = int(z[2])
				z[3] = int(z[3])
				z[4] = int(z[4])
				z[5] = int(z[5])
				z[6] = int(z[6])
				z[7] = z[7].replace("'", '')
				z[8] = z[8].replace("'", '')
				self.keyb[key[0]] = z

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
					self.root.grab_key(self.keyb[key][1], checkmask(maske),
										1,X.GrabModeAsync, X.GrabModeAsync)
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

def on_enable(*args):
	if args[0]:
		if not X:
			print 'Python-xlib library is not available. '
		global a
		a = XlibKeys()
	else:
		a.freeKey()

def run_command(action):
	print action
	p = subprocess.Popen("sonata " + action, shell=True)

### seek ######################################################################

def handle_PositionGet(position):
#	print str(position)
	player.PositionSet(dbus.Int32(position + vector_),
							 dbus_interface='org.freedesktop.MediaPlayer',
							 reply_handler=handle_PositionSet,
							 error_handler=handle_PositionSet)

def handle_PositionGet_error(e):
	print "\t", str(e)

def handle_PositionSet():
	pass

def seek(vector):
	bus = dbus.SessionBus()
	global player, vector_
	try:
		player = bus.get_object('org.mpris.mpd','/Player')
	except dbus.DBusException, msg:
		dialog = gtk.MessageDialog(parent=None,
			 flags=gtk.DIALOG_MODAL, type=gtk.MESSAGE_WARNING,
			  buttons=gtk.BUTTONS_OK)
		dialog.set_markup('mpDris plugin not started')
#		dialog.format_secondary_text(str(msg))
		gtk.gdk.threads_enter()
		response = dialog.run()
		dialog.destroy()
		gtk.gdk.threads_leave()
		return
	if vector == 'forward':
		# forward 5 sec
		vector_ = 5000
	else:
		# backward 5 sec
		vector_ = -5000
	position = player.PositionGet(dbus_interface='org.freedesktop.MediaPlayer',
									reply_handler=handle_PositionGet,
									error_handler=handle_PositionGet_error)
###############################################################################

def on_configure(plugin_name):
	def defineNewKey(widget,data):

		def keypressed(widget, event):

			# put pressed modifiers into the list and count them
			####
			a.keyb[data][2]=0
			a.keyb[data][3]=0
			a.keyb[data][4]=0
			a.keyb[data][5]=0
			a.keyb[data][6]=0
			mod = 0

			if 'GDK_SHIFT_MASK' in event.state.value_names:
				a.keyb[data][2] = 1
				mod += 1

			if 'GDK_CONTROL_MASK' in event.state.value_names:
				a.keyb[data][3] = 1
				mod += 1

			if 'GDK_MOD1_MASK' in event.state.value_names:
				a.keyb[data][4] = 1
				mod += 1

			if 'GDK_MOD2_MASK' in event.state.value_names:
				a.keyb[data][5] = 1
				mod += 1

			if 'GDK_MOD3_MASK' in event.state.value_names:
				a.keyb[data][6] = 1
				mod += 1

			#### now sort out the exceptions
			# omitt doing an action for modifier key events
			if event.string == '':
				print 'mod hit'

			elif mod == 0:
				print 'no mod used'

			else:
				# If the user entered a valid keycombination, save the key in the dict
				# and reload the main-plugin-configuration dialog
				# so that the label on the button shows the correct key
				# but first check if the key is already mapped
				used = ''
				for kcode in a.keyb:
					if a.keyb[kcode][1] == event.hardware_keycode:
						if a.keyb[kcode][0] != a.keyb[data][0]:
							used = kcode

				if used == '':
					a.keyb[data][0] = gtk.gdk.keyval_name(event.keyval)
					a.keyb[data][1] = event.hardware_keycode
					pkeyinfo.destroy()
					update()
				else:
					useddialog = gtk.MessageDialog(window, gtk.DIALOG_DESTROY_WITH_PARENT,
												   gtk.MESSAGE_INFO,
												   gtk.BUTTONS_OK,
												   _("Key already mapped by %s") % used)
					useddialog.run()
					useddialog.destroy()

		pkeyinfo = gtk.MessageDialog(window, gtk.DIALOG_DESTROY_WITH_PARENT,
									 gtk.MESSAGE_INFO, gtk.BUTTONS_CANCEL,
									 _("Please Press a Key for '%s' while holding one or more modifier Keys (ctrl, shift, alt)") % data)

		pkeyinfo.add_events(gtk.gdk.KEY_PRESS_MASK)
		pkeyinfo.connect('key-press-event', keypressed)
		pkeyinfo.run()
		pkeyinfo.destroy()

	def clearKey(widget, data):
		# user clicked the 'clear' button
		a.keyb[data][0]='not defined'
		a.keyb[data][1]=0
		a.keyb[data][2]=0
		a.keyb[data][3]=0
		a.keyb[data][4]=0
		a.keyb[data][5]=0
		a.keyb[data][6]=0
		update()


	def update():
		global col
		window.vbox.remove(col)
		col = gtk.HBox(False, 0)
		window.vbox.pack_start(col, False, False, 5)
		command = gtk.VBox(True, 0)
		keyf = gtk.VBox(True, 0)
		clear = gtk.VBox(True, 0)
		col.pack_start(command, False, False, 5)
		col.pack_start(keyf, True, True, 5)
		col.pack_start(clear, False, False, 5)

		for key in a.action:
			label = gtk.Label(key)
			command.pack_start(label, False, False)

			knopf = str(a.keyb[key][0])
			if a.keyb[key][2] == 1:
				knopf += ' + shift'
			if a.keyb[key][3] == 1:
				knopf += ' + ctrl'
			if a.keyb[key][4] == 1:
				knopf += ' + mod1'
			if a.keyb[key][5] == 1:
				knopf += ' + mod2'
			if a.keyb[key][6] == 1:
				knopf += ' + mod3'

			button = gtk.Button(knopf)
			keyf.pack_start(button, False, False, 5)
			button.connect("clicked",defineNewKey, key)

			button_clear = gtk.Button('clear')
			clear.pack_start(button_clear, False, False, 5)
			button_clear.connect("clicked",clearKey, key)

			label.show()
			button.show()
			button_clear.show()

	#	window.show_all()
		command.show()
		keyf.show()
		clear.show()
		col.show()

	window = gtk.Dialog(("%s configuration") %plugin_name)
	window.add_button("gtk-cancel", gtk.RESPONSE_CANCEL)
	window.add_button("gtk-ok", gtk.RESPONSE_OK)
	a.freeKey()
	a.grabKey('free')
	source_remove(a.listener)
	global col
	col = gtk.HBox(False, 0)
	window.vbox.pack_start(col, False, False, 5)
	update()
	window.show_all()
	response = window.run()

	if response == gtk.RESPONSE_OK:
		a.listen()
		window.destroy()
		## return save variables
		#save_vars = []
		#for key in a.keyb.keys():
			#save_vars.append((key, a.keyb[key]))
		#return save_vars

		#"""Save configuration in file"""
		conf = ConfigParser.ConfigParser()
		for key in a.keyb.keys():
			conf.set(None, key, a.keyb[key])
		conf.write(file(os.path.expanduser('~/.config/sonata/Global hotkey'), 'w'))

	else:
		window.destroy()
