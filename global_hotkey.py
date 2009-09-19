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

import subprocess, gtk, ConfigParser, os, inspect, re

from gobject import source_remove,io_add_watch
import ConfigParser
import dbus

try:
	from Xlib.display import Display
	from Xlib import X
	import Xlib.XK, Xlib.keysymdef.xkb
	x, xk, xkb = Xlib.X, Xlib.XK, Xlib.keysymdef.xkb
	keysym_to_mask = {
						xk.XK_Shift_L: (x.ShiftMask, "shift"),
						xk.XK_Shift_R: (x.ShiftMask, "shift"),
						xk.XK_Control_L: (x.ControlMask, "control"),
						xk.XK_Control_R: (x.ControlMask, "control"),
						xk.XK_Alt_L: (x.Mod1Mask, "alt"),
						xk.XK_Alt_R: (x.Mod1Mask, "alt"),
						xk.XK_Super_L: (x.Mod4Mask, "winkey"),
						xkb.XK_ISO_Level3_Shift: (x.Mod5Mask, "altgr")
					}
	DISPLAY = Display()
except ImportError:
	X = None


class XlibKeys(object):
	def __init__(self):
		self.display = DISPLAY
		kc = Xlib.XK
		CapsLockKeyCode, NumLockKeyCode, ScrollLockKeyCode = \
			map(self.display.keysym_to_keycode, [kc.XK_Caps_Lock, kc.XK_Num_Lock, kc.XK_Scroll_Lock])

		self.capslock_mask = self.numlock_mask = self.scrolllock_mask = 0
		for index, mask in enumerate(self.display.get_modifier_mapping()):
			if mask[0] == CapsLockKeyCode:
				self.capslock_mask = 1 << index
			elif mask[0] == NumLockKeyCode:
				self.numlock_mask = 1 << index
			elif mask[0] == ScrollLockKeyCode:
				self.scrolllock_mask = 1 << index

		self.action = [ 'play song in playlist', 'stop currently playing song',
						'pause currently playing song', 'play next song',
						'play previous song', 'toggle play/pause',
						'toggle repeat mode','toggle random mode',
						'seek forward', 'seek backward',
						'toggle minimized or visible','popup song notification',
						'now listen info to clipboard']
		#self. keyb = 'name':          [key combination,callback,callback-arguments]
		self.keyb = {
		'play song in playlist':	   ['not defined', 'run_command','"play"'],
		'stop currently playing song': ['not defined', 'run_command','"stop"'],
		'pause currently playing song':['not defined', 'run_command','"pause"'],
		'play next song':              ['not defined', 'run_command','"next"'],
		'play previous song':	       ['not defined', 'run_command','"prev"'],
		'toggle play/pause':	       ['not defined', 'run_command','"pp"'],
		'toggle repeat mode':          ['not defined', 'run_command','"repeat"'],
		'toggle random mode':          ['not defined', 'run_command','"random"'],
		'toggle minimized or visible': ['not defined', 'sonata_commands','"toggle"'],
		'popup song notification':     ['not defined', 'sonata_commands','"popup"'],
		'seek forward':                ['not defined', 'seek','"forward"'],
		'seek backward':               ['not defined', 'seek','"backward"'],
		'now listen info to clipboard':['not defined', 'now_listen', 'None']
					 }
		"""Load configuration from file"""
		conf = ConfigParser.ConfigParser()
		if os.path.isfile(os.path.expanduser('~/.config/sonata/Global hotkey')):
			conf.read(os.path.expanduser('~/.config/sonata/Global hotkey'))
			load_vars = conf.items('DEFAULT')
			for key in conf.items('DEFAULT'):
				self.keyb[key[0]][0] = key[1]

		self.listen()

	def string_to_keycode(self, strcode):
		if len(strcode) > 2 and strcode[0] == "@" and strcode[-1] == "@":
			return int(strcode[1:-1])
		for key in inspect.getmembers(Xlib.XK):
			if len(key) != 2 or key[0].find("XK_") != 0 or strcode != key[0].replace("XK_", ""):
				continue
			return self.display.keysym_to_keycode(key[1])

	def string_to_mask(self, str_modifiers):
		mask = 0
		for str_modifier in str_modifiers:
			for keysym, tmask in keysym_to_mask.items():
				if tmask[1] == str_modifier.lower():
					mask = mask | keysym_to_mask[keysym][0]
					break
		return mask

	def ButtonHit(self,event):
		for i in self.keyb.values():
			modifiers = re.findall("<(\w+)>", i[0])
			mod = self.string_to_mask(modifiers)
			mods = []
			for mask in (0, self.capslock_mask, self.numlock_mask,
						self.scrolllock_mask,self.capslock_mask | self.numlock_mask,
						self.capslock_mask | self.scrolllock_mask,
						self.capslock_mask | self.numlock_mask | self.scrolllock_mask):
				mods.append(mod | mask)
			key = re.findall("(@?\w+@?)$", i[0])[0]
			if self.string_to_keycode(key) == event.detail and event.state in mods:
				eval (i[1]+'('+i[2]+')')

	def freeKey(self):
		source_remove(self.listener)
		self.grabKey('free')

	def grabKey(self,action):
		for command in self.keyb.keys():
			keys = self.keyb[command][0]
			if keys.lower() != 'not defined':
				modifiers = re.findall("<(\w+)>", keys)
				mod = self.string_to_mask(modifiers)
				key = re.findall("(@?\w+@?)$", keys)[0]
				keycode = self.string_to_keycode(key)
				mode = Xlib.X.GrabModeAsync
				if action == 'grab':
					for mask in (0, self.capslock_mask, self.numlock_mask,
						self.scrolllock_mask, self.capslock_mask | self.numlock_mask,
						self.capslock_mask | self.scrolllock_mask,
						self.capslock_mask | self.numlock_mask | self.scrolllock_mask):
						self.root.grab_key(keycode, mod | mask, 1, mode, mode)
				elif action == 'free':
					for mask in (0, self.capslock_mask, self.numlock_mask,
						self.scrolllock_mask, self.capslock_mask | self.numlock_mask,
						self.capslock_mask | self.scrolllock_mask,
						self.capslock_mask | self.numlock_mask | self.scrolllock_mask):
						self.root.ungrab_key(keycode, mod | mask, 1)
					self.display.flush()

	def listen(self):
		self.root = self.display.screen().root
		self.root.change_attributes(event_mask = X.KeyPressMask)
		self.grabKey('grab')

		def checkKey(arg1,arg2):
			#print arg1,arg2
			event = self.display.next_event()
			if event.type == X.KeyPress:
				self.ButtonHit(event)
			return True

		self.listener = io_add_watch(self.display, 1 ,checkKey)
		self.display.pending_events()

def on_enable(*args):
	if args[0]:
		if not X:
			print 'Python-xlib library is not available. '
			useddialog = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT,
										   gtk.MESSAGE_INFO,gtk.BUTTONS_OK,
										   "Python-xlib library is not available.\
										   Global hotkey plugin requires python-Xlib.")
			useddialog.run()
			useddialog.destroy()
			return
		else:
			global a
			a = XlibKeys()
	else:
		if X:
			a.freeKey()

def run_command(action):
	p = subprocess.Popen("sonata " + action, shell=True)

def show_warning(msg):
	dialog = gtk.MessageDialog(parent=None,
			 flags=gtk.DIALOG_MODAL, type=gtk.MESSAGE_WARNING,
			  buttons=gtk.BUTTONS_OK)
	dialog.set_markup(msg)
	gtk.gdk.threads_enter()
	response = dialog.run()
	dialog.destroy()
	gtk.gdk.threads_leave()

### now listen to clipboard ###################################################
def handle_GetMetadata(meta):
	title = 'Unknown Title'
	artist = 'Unknown Artist'
	album = 'Unknown Source'
	clipboard = gtk.clipboard_get()
	gtk.gdk.threads_enter()
	text = clipboard.wait_for_text()

	if 'title' in meta:
		title = meta['title']
	if 'artist' in meta:
		artist = meta['artist']
	if 'album' in meta:
		album = meta['album']
	text = '/me now listen: "%s" by %s from %s' % (title, artist, album)

	clipboard.set_text(text)
	clipboard.store()
	gtk.gdk.threads_leave()

def handle_GetMetadata_error(e):
	print "\t", str(e)

def handle_none():
	pass

def now_listen(arg):
	bus = dbus.SessionBus()
	global player
	try:
		player = bus.get_object('org.mpris.mpd','/Player')
	except dbus.DBusException, msg:
		show_warning('mpDris plugin not started')
		return
	meta = player.GetMetadata(dbus_interface='org.freedesktop.MediaPlayer',
									reply_handler=handle_GetMetadata,
									error_handler=handle_GetMetadata_error)

### seek ######################################################################
def handle_PositionGet(position):
#	print str(position)
	player.PositionSet(dbus.Int32(position + vector_),
							 dbus_interface='org.freedesktop.MediaPlayer',
							 reply_handler=handle_none,
							 error_handler=handle_none)

def handle_PositionGet_error(e):
	print "\t", str(e)

def seek(vector):
	bus = dbus.SessionBus()
	global player, vector_
	try:
		player = bus.get_object('org.mpris.mpd','/Player')
	except dbus.DBusException, msg:
		show_warning('mpDris plugin not started')
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

### sonata commands ###########################################################
def sonata_commands(command):
	bus = dbus.SessionBus()
	player = bus.get_object('org.MPD', '/org/MPD/Sonata')
	player_method = getattr(player, command)
	player_method(dbus_interface='org.MPD.SonataInterface',
								reply_handler=handle_none,
								error_handler=handle_none)

def on_configure(plugin_name):
	if not X:
		return

	def defineNewKey(widget,data):
		def keycodes_to_string(keycodes):
			string = 'not defined'
			if keycodes_pressed:
				keycodes_to_modifier = {}
				for keysym, tmask in keysym_to_mask.items():
					modifier = tmask[1]
					keycodes_to_modifier[DISPLAY.keysym_to_keycode(keysym)] = modifier
				strmod = strkey = ""
				current_modifiers = []
				for keycode in keycodes_pressed:
					if keycode in keycodes_to_modifier:
						string = keycodes_to_modifier[keycode]
						if string in current_modifiers: continue
						strmod += "<" + string + ">"
						current_modifiers.append(string)
						continue
					keysym = DISPLAY.keycode_to_keysym(keycode, 0)

					for key in inspect.getmembers(Xlib.XK):
						if len(key) != 2 or key[0].find("XK_") != 0 or \
													key[1] != keysym: continue
						strkey = key[0].replace("XK_", "")
						break
					else: strkey = "@%d@" %keycode
					break
				string = strmod + strkey
			# set button label
			#button.set_label(string)
			pkeyinfo.set_property( "secondary-text",string)
			return string

		def key_press(widget, event):
			keycode = event.hardware_keycode
			if keycode not in keycodes_pressed:
				keycodes_pressed.append(keycode)

			string = keycodes_to_string(keycodes_pressed)

			is_keycode_modifier = False
			for keysym in keysym_to_mask:
				if keycode == DISPLAY.keysym_to_keycode(keysym):
					is_keycode_modifier = True

			def keycodes_to_mask(display, keycodes):
				mask = 0
				for keycode in keycodes:
					for keysym, tmask in keysym_to_mask.items():
						modmask = tmask[0]
						if keycode == display.keysym_to_keycode(keysym):
							mask = mask | modmask
				return mask

			if keycodes_to_mask(DISPLAY, keycodes_pressed) and not is_keycode_modifier:
				for m in a.keyb.keys():
					if string ==a.keyb[m][0]:
						useddialog = gtk.MessageDialog(
									window, gtk.DIALOG_DESTROY_WITH_PARENT,
									gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
									"Key combination already mapped by '%s'" % m)
						useddialog.run()
						useddialog.destroy()
						a.keyb[data][0] = 'not defined'
						pkeyinfo.destroy()
						update()
						return
				a.keyb[data][0] = string
				pkeyinfo.destroy()
				update()

		def key_release(widget, event):
			keycode = event.hardware_keycode
			while keycode in keycodes_pressed:
				keycodes_pressed.remove(keycode)
			keycodes_to_string(keycodes_pressed)

		keycodes_pressed = []
		pkeyinfo = gtk.MessageDialog(window, gtk.DIALOG_DESTROY_WITH_PARENT,
									 gtk.MESSAGE_INFO, gtk.BUTTONS_CANCEL)
		msg = "Please Press a Key for '%s' " \
				"while holding one or more modifier Keys " \
				"(ctrl, shift, alt, winkey, alt_gr)" % data
		pkeyinfo.set_markup('<span style="normal">%s</span>' % msg)
		pkeyinfo.add_events(gtk.gdk.KEY_PRESS_MASK)
		global button
		button = widget
		pkeyinfo.connect('key-press-event', key_press)
		pkeyinfo.connect('key-release-event', key_release)
		pkeyinfo.run()
		pkeyinfo.destroy()

	def clearKey(widget, data):
		# user clicked the 'clear' button
		a.keyb[data][0]='not defined'
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
			label.set_alignment(xalign=0, yalign=0.5)
			command.pack_start(label, False, False)

			knopf = str(a.keyb[key][0])

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

		#"""Save configuration in file"""
		conf = ConfigParser.ConfigParser()
		for key in a.keyb.keys():
			conf.set(None, key, a.keyb[key][0])
		conf.write(file(os.path.expanduser('~/.config/sonata/Global hotkey'), 'w'))
	window.destroy()

######################## for test #############################################
if __name__ == '__main__':
	on_enable(True)
	#on_configure(None)
	import gobject
	loop = gobject.MainLoop()
	loop.run()
