#!/usr/bin/python

### BEGIN PLUGIN INFO
# [plugin]
# plugin_format: 0, 0
# name: mpDris
# version: 0, 0, 1
# description:  MPD client, which can accept MPRIS commands and emits MPRIS signals.
# author: Fomin Denis
# author_email: fominde@gmail.com
# url: http://ayeon.org/projects/mpDris/
# license: GPL v3 or later
# [capabilities]
# enablables: on_enable
### END PLUGIN INFO

import os
import sys
import signal
import string
import socket

import mpd
import gobject
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import ConfigParser
import threading

# Get host,port,musicdir from config
conf = ConfigParser.ConfigParser()
conf.read(os.path.expanduser('~/.config/sonata/sonatarc'))
profile = conf.get('connection', 'profile_num')
host = conf.get('profiles', 'hosts[%s]' %profile)
port = conf.get('profiles', 'ports[%s]' %profile)
path = conf.get('profiles', 'musicdirs[%s]' %profile)

# MPRIS allowed metadata tags
allowed_tags = {
	"title": str,
	"artist": str,
	"album": str,
	"tracknumber": str,
	"time": int,
	"mtime": int,
	"genre": str,
	"comment": str,
	"rating": int,
	"year": int,
	"date": int,
	"location": str,
	"arturl": str,
	"asin": str,
	"puid fingerprint": str,
	"mb track id": str,
	"mb artist id": str,
	"mb artist sort name": str,
	"mb album id": str,
	"mb release date": str,
	"mb album artist": str,
	"mb album artist id": str,
	"mb album artist sort name": str,
	"audio-bitrate": int,
	"audio-samplerate": int,
	"video-bitrate": int
}

# MPRIS capabilites
CAN_GO_NEXT           = 1 << 0
CAN_GO_PREV           = 1 << 1
CAN_PAUSE             = 1 << 2
CAN_PLAY              = 1 << 3
CAN_SEEK              = 1 << 4
CAN_PROVIDE_METADATA  = 1 << 5
CAN_HAS_TRACKLIST     = 1 << 6

# Default url handlers if MPD doesn't support 'urlhandlers' command
urlhandlers = [ 'http://' ]

def FormatMetadata(metadata, path):
	if 'date' in metadata:
		metadata['year'] = metadata['date']
		del metadata['date']

	if 'track' in metadata:
		metadata['tracknumber'] = metadata['track']
		del metadata['track']
		if 'disc' in metadata:
			metadata['tracknumber'] = metadata['tracknumber'] + '/' + metadata['disc']
			del metadata['disc']

	if 'file' in metadata:
		file = metadata['file']
		# prepend path to library if it isn't a uri
		if len([ x for x in urlhandlers if file.startswith(x) ]) == 0:
			file = os.path.join(path, file)
		metadata['location'] = file
		del metadata['file']

	# Stream: populate some missings tags with stream's name
	if 'name' in metadata:
		if 'title' not in metadata:
			metadata['title'] = metadata['name']
		elif 'album' not in metadata:
			metadata['album'] = metadata['name']

	surplus_tags = set(metadata.keys()).difference(set(allowed_tags.keys()))

	# Remove surplus tags
	for tag in surplus_tags:
		del metadata[tag]

	# Cast metadata to the correct type, or discard it
	for key, value in metadata.items():
		try:
			metadata[key] = allowed_tags[key](value)
		except ValueError, e:
			del metadata[key]
			# FIXME
			print e

	return metadata


# Wrapper to handle socket errors and similar
class MPDWrapper:
	def __init__(self, mpd_client):
		self.__mpd_client = mpd_client

	def __getattr__(self, name):
		try:
			result = getattr(self.__mpd_client, name)
		except (socket.error, mpd.MPDError):
			self.__mpd_client.disconnect()
			raise dbus.DBusException

		return result


class MPRISRoot(dbus.service.Object):
	''' The base object of an MPRIS player '''
	def __init__(self, bus, loop, mpd_wrapper):
		dbus.service.Object.__init__(self, bus, '/')
		self.loop = loop
		self.mpd_wrapper = mpd_wrapper

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 's')
	def Identity(self):
		return 'MPD ' + self.mpd_wrapper.mpd_version

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '')
	def Quit(self):
		print 'Aborting at client request.'
# TODO: What should do a plug-in or a player?
		#self.loop.stop()

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '(qq)')
	def MprisVersion(self):
		return (dbus.UInt16(1), dbus.UInt16(0))


class MPRISTrackList(dbus.service.Object):
	''' Class describing a Track List '''
	def __init__(self, bus, path, mpd_wrapper):
		dbus.service.Object.__init__(self, bus, '/TrackList')
		self.__path = path
		self.mpd_wrapper = mpd_wrapper

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'i', out_signature = 'a{sv}')
	def GetMetadata(self, index):
		return FormatMetadata(self.mpd_wrapper.playlistinfo(index)[0], self.__path)

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 'i')
	def GetCurrentTrack(self):
		return dbus.Int32(self.mpd_wrapper.currentsong()['id'])

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 'i')
	def GetLength(self):
		return dbus.Int32(self.mpd_wrapper.status()['playlistlength'])

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'sb', out_signature = 'i')
	def AddTrack(self, track, play_immediately):
# TODO: Is this even possible?
		raise dbus.DBusException

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'i', out_signature = '')
	def DelTrack(self, index):
		self.mpd_wrapper.deleteid(index)
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'b', out_signature = '')
	def SetLoop(self, value):
		''' NOP, since MPD does not support this '''
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'b', out_signature = '')
	def SetRandom(self, value):
		self.mpd_wrapper.random(value)
		return

	@dbus.service.signal('org.freedesktop.MediaPlayer', signature = 'i')
	def TrackListChange(self, length):
		return


class MPRISPlayer(dbus.service.Object):
	def __init__(self, bus, path, mpd_wrapper):
		dbus.service.Object.__init__(self, bus, '/Player');
		self.__path = path
		self.mpd_wrapper = mpd_wrapper

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '')
	def Next(self):
		self.mpd_wrapper.next()
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '')
	def Prev(self):
		self.mpd_wrapper.previous()
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '')
	def Pause(self):
		self.mpd_wrapper.pause()
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '')
	def Stop(self):
		self.mpd_wrapper.stop()
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '')
	def Play(self):
		self.mpd_wrapper.play()
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'b', out_signature = '')
	def Repeat(self, value):
		self.mpd_wrapper.repeat(value)
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = '(iiii)')
	def GetStatus(self):
		status = self.mpd_wrapper.status()
		if status['state'] == 'play':
			play_status = 0
		elif status['state'] == 'pause':
			play_status = 1
		elif status['state'] == 'stop':
			play_status = 2

		return (play_status, dbus.Int32(status['random']), dbus.Int32(status['repeat']), 0)

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 'a{sv}')
	def GetMetadata(self):
		return FormatMetadata(self.mpd_wrapper.currentsong(), self.__path)

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 'i')
	def GetCaps(self):
		caps = CAN_HAS_TRACKLIST

		status = self.mpd_wrapper.status()
		if int(status['playlistlength']) != 0:
			caps |= CAN_GO_NEXT | CAN_GO_PREV | CAN_PAUSE | CAN_PLAY | CAN_SEEK | CAN_PROVIDE_METADATA

		return dbus.Int32(caps)

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'i', out_signature = '')
	def VolumeSet(self, volume):
		self.mpd_wrapper.setvol(int(volume))
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 'i')
	def VolumeGet(self):
		status = self.mpd_wrapper.status()
		return dbus.Int32(status['volume'])

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = 'i', out_signature = '')
	def PositionSet(self, position):
		status = self.mpd_wrapper.status()
		if status['state'] == 'stop':
			return

		self.mpd_wrapper.seek(status['songid'], int(position / 1000))
		return

	@dbus.service.method('org.freedesktop.MediaPlayer', in_signature = '', out_signature = 'i')
	def PositionGet(self):
		status = self.mpd_wrapper.status()
		if status['state'] == 'stop':
			return 0
		else:
			return dbus.Int32(status['time'].split(':', 1)[0]) * 1000

	@dbus.service.signal('org.freedesktop.MediaPlayer', signature = 'a{sv}')
	def TrackChange(self, metadata):
		return

	@dbus.service.signal('org.freedesktop.MediaPlayer', signature = '(iiii)')
	def StatusChange(self, status):
		return

	@dbus.service.signal('org.freedesktop.MediaPlayer', signature = 'i')
	def CapsChange(self, caps):
		return


# Periodic status check function
def check_mpd_status(mpd_client, host, port, track_list, player):
	# TODO: This should perhaps be exception-checked?
	status = mpd_client.status()

	# Invalidate some fields, so that we throw out events at start
	status['state'] = 'invalid'
	status['songid'] = -1

	song = mpd_client.currentsong()
	is_stream = 'name' in song

	while True:
		old_status = status
		try:
			status = mpd_client.status()
		except (socket.error, mpd.MPDError):
			# Command, failed - try to reconnect
			while True:
				try:
					# Clean out any bad socket FDs before trying to connect..
					# this might leave stray FDs!
					mpd_client._reset()
					mpd_client.connect(host, port)
				except (socket.error, mpd.MPDError), e:
					yield old_status
					# Retry..
					continue

				break

			# Successful reconnection
			pass

		if old_status['state'] != status['state'] or \
		   old_status['random'] != status['random'] or \
		   old_status['repeat'] != status['repeat']:
			player.StatusChange(player.GetStatus())

		if status['state'] != 'stop' and \
		   old_status['state'] != 'stop':
			if old_status['songid'] != status['songid'] or \
			(old_status['state'] == 'pause' and status['state'] == 'play'):
				player.TrackChange(player.GetMetadata())
				is_stream = 'name' in mpd_client.currentsong()
			# Stream: can provide song's metadata, check it
			elif is_stream:
				old_song = song
				song = mpd_client.currentsong()
				if song.get('title') != old_song.get('title') or \
				   song.get('artist') != old_song.get('artist') or \
				   song.get('album') != old_song.get('album'):
					player.TrackChange(player.GetMetadata())



		if 0 == int(status['playlistlength']):
			player.CapsChange(player.GetCaps())

		if old_status['playlist'] != status['playlist']:
			track_list.TrackListChange(track_list.GetLength())

		yield status

class Loop(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self)

	def run(self):

		self.loop = gobject.MainLoop()

		# Init DBUS connection
		self.session_bus = dbus.SessionBus()
		self.name = dbus.service.BusName('org.mpris.mpd', self.session_bus)

		# Init MPD connection
		mpd_client = mpd.MPDClient()
		try:
			mpd_client.connect(host, port)
		except socket.error, e:
			print "Fatal: Could not connect to MPD: " + str(e)
			sys.exit(2)

		# Get URL handlers supported by MPD
		if 'urlhandlers' in mpd_client.commands():
			urlhandlers = mpd_client.urlhandlers()

		# Create wrapper to handle connection failures with MPD more gracefully..
		# i.e. throw another kind of exception.. :P
		mpd_wrapper = MPDWrapper(mpd_client)

		self.root = MPRISRoot(self.session_bus, self, mpd_wrapper)
		self.track_list = MPRISTrackList(self.session_bus, path, mpd_wrapper)
		self.player = MPRISPlayer(self.session_bus, path, mpd_wrapper)

		# Add periodic status check for MPRIS signals
		self.func = gobject.timeout_add(250, check_mpd_status(mpd_client, host, port, self.track_list, self.player).next)
		self.loop.run()

	def stop(self):
		gobject.source_remove(self.func)
		self.loop.quit()
		a = {'year' : '','tracknumber' : '','location' : '',
			 'title' : '','album' : '','time' : '',
			 'genre' : '','artist' : '' }
		self.player.TrackChange(a)
		del self.name
		self.root.remove_from_connection()
		self.track_list.remove_from_connection()
		self.player.remove_from_connection()


def on_enable(state):
	if state:
		global thread
		thread = Loop()
		thread.start()
	else:
		if thread.isAlive():
			thread.stop()


