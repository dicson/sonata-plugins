#!/usr/bin/env python

### BEGIN PLUGIN INFO
# [plugin]
# plugin_format: 0, 0
# name: Old view
# version: 0, 0, 0
# description: Return library to the old view.
# author: Fomin Denis
# author_email: fominde@gmail.com
# url: http://sonata.berlios.de
# license: GPL v3 or later
# [capabilities]
# enablables: on_enable
### END PLUGIN INFO

import gtk, pango
from sonata import consts, misc
from sonata import mpdhelper as mpdh
import operator, os
import locale

store = None

def library_populate_toplevel_data(AP= None, genreview=False, artistview=False, albumview=False):
	bd = APP.library.library_get_toplevel_cache(genreview, artistview, albumview)
	if bd is not None:
		# We have our cached data, woot.
		return bd
	bd = []
	if genreview or artistview:
		# Only for artist/genre views, album view is handled differently
		# since multiple artists can have the same album name
		if genreview:
			items = APP.library.library_return_list_items('genre')
			pb = APP.library.genrepb
		else:
			items = APP.library.library_return_list_items('artist')
			pb = APP.library.artistpb
		if not (APP.library.NOTAG in items):
			items.append(APP.library.NOTAG)
		for item in items:
			if genreview:
				playtime, num_songs = APP.library.library_return_count(genre=item)
				data = APP.library.library_set_data(genre=item)
			else:
				playtime, num_songs = APP.library.library_return_count(artist=item)
				data = APP.library.library_set_data(artist=item)
			if num_songs > 0:
				display = misc.escape_html(item)
				#display += APP.library.add_display_info(num_songs, int(playtime)/60)
				bd += [(misc.lower_no_the(item), [pb, data, display])]
	elif albumview:
		albums = []
		untagged_found = False
		for item in mpdh.call(APP.library.client, 'listallinfo', '/'):
			if 'file' in item and 'album' in item:
				album = mpdh.get(item, 'album')
				artist = mpdh.get(item, 'artist', APP.library.NOTAG)
				year = mpdh.get(item, 'date', APP.library.NOTAG)
				filepath = os.path.dirname(mpdh.get(item, 'file'))
				data = APP.library.library_set_data(album=album, artist=artist, year=year, path=filepath)
				albums.append(data)
				if album == APP.library.NOTAG:
					untagged_found = True
		if not untagged_found:
			albums.append(APP.library.library_set_data(album=APP.library.NOTAG))
		albums = misc.remove_list_duplicates(albums, case=False)
		albums = APP.library.list_identify_VA_albums(albums)
		for item in albums:
			album, artist, year, path = APP.library.library_get_data(item, 'album', 'artist', 'year', 'path')
			playtime, num_songs = APP.library.library_return_count(artist=artist, album=album, year=year)
			if num_songs > 0:
				data = APP.library.library_set_data(artist=artist, album=album, year=year, path=path)
				display = misc.escape_html(album)
				if artist and year and len(artist) > 0 and len(year) > 0 and artist != APP.library.NOTAG and year != APP.library.NOTAG:
					display += " <span weight='light'>(" + misc.escape_html(artist) + ", " + misc.escape_html(year) + ")</span>"
				elif artist and len(artist) > 0 and artist != APP.library.NOTAG:
					display += " <span weight='light'>(" + misc.escape_html(artist) + ")</span>"
				elif year and len(year) > 0 and year != APP.library.NOTAG:
					display += " <span weight='light'>(" + misc.escape_html(year) + ")</span>"
				#display += APP.library.add_display_info(num_songs, int(playtime)/60)
				bd += [(misc.lower_no_the(album), [APP.library.albumpb, data, display])]
	bd.sort(locale.strcoll, key=operator.itemgetter(0))
	if genreview:
		APP.library.lib_view_genre_cache = bd
	elif artistview:
		APP.library.lib_view_artist_cache = bd
	elif albumview:
		APP.library.lib_view_album_cache = bd
	return bd

def library_populate_data(self=None, genre=None, artist=None, album=None, year=None):
	# Create treeview model info
	bd = []
	if genre is not None and artist is None and album is None:
		# Artists within a genre
		artists = APP.library.library_return_list_items('artist', genre=genre)
		if len(artists) > 0:
			if not APP.library.NOTAG in artists:
				artists.append(APP.library.NOTAG)
			for artist in artists:
				playtime, num_songs = APP.library.library_return_count(genre=genre, artist=artist)
				if num_songs > 0:
					display = misc.escape_html(artist)
					#display += APP.library.add_display_info(num_songs, int(playtime)/60)
					data = APP.library.library_set_data(genre=genre, artist=artist)
					bd += [(misc.lower_no_the(artist), [APP.library.artistpb, data, display])]
	elif artist is not None and album is None:
		# Albums/songs within an artist and possibly genre
		# Albums first:
		if genre is not None:
			albums = APP.library.library_return_list_items('album', genre=genre, artist=artist)
		else:
			albums = APP.library.library_return_list_items('album', artist=artist)
		for album in albums:
			if genre is not None:
				years = APP.library.library_return_list_items('date', genre=genre, artist=artist, album=album)
			else:
				years = APP.library.library_return_list_items('date', artist=artist, album=album)
			if not APP.library.NOTAG in years:
				years.append(APP.library.NOTAG)
			for year in years:
				if genre is not None:
					playtime, num_songs = APP.library.library_return_count(genre=genre, artist=artist, album=album, year=year)
					if num_songs > 0:
						files = APP.library.library_return_list_items('file', genre=genre, artist=artist, album=album, year=year)
						path = os.path.dirname(files[0])
						data = APP.library.library_set_data(genre=genre, artist=artist, album=album, year=year, path=path)
				else:
					playtime, num_songs = APP.library.library_return_count(artist=artist, album=album, year=year)
					if num_songs > 0:
						files = APP.library.library_return_list_items('file', artist=artist, album=album, year=year)
						path = os.path.dirname(files[0])
						data = APP.library.library_set_data(artist=artist, album=album, year=year, path=path)
				if num_songs > 0:
					cache_data = APP.library.library_set_data(artist=artist, album=album, path=path)
					display = misc.escape_html(album)
					if year and len(year) > 0 and year != APP.library.NOTAG:
						display += " <span weight='light'>(" + misc.escape_html(year) + ")</span>"
					#display += APP.library.add_display_info(num_songs, int(playtime)/60)
					ordered_year = year
					if ordered_year == APP.library.NOTAG:
						ordered_year = '9999'
					pb = APP.library.artwork.get_library_artwork_cached_pb(cache_data, APP.library.albumpb)
					bd += [(ordered_year + misc.lower_no_the(album), [pb, data, display])]
		# Now, songs not in albums:
		bd += APP.library.library_populate_data_songs(genre, artist, APP.library.NOTAG, None)
	else:
		# Songs within an album, artist, year, and possibly genre
		bd += APP.library.library_populate_data_songs(genre, artist, album, year)
	if len(bd) > 0:
		bd = APP.library.library_populate_add_parent_rows() + bd
	bd.sort(locale.strcoll, key=operator.itemgetter(0))
	return bd


# this gets called when the plugin is loaded, enabled, or disabled:
def on_enable(state):
	APP.library.lib_view_artist_cache = None
	global store
	if state:
		store = (APP.library.library_populate_toplevel_data,APP.library.library_populate_data)		
		APP.library.albumpb = gtk.gdk.pixbuf_new_from_file_at_size(APP.library.album_filename, 16, 16)
		APP.artwork.library_artwork_init(APP.librarydata, 16)
		APP.library.library_populate_toplevel_data = library_populate_toplevel_data
		APP.library.library_populate_data = library_populate_data
		APP.library.library_browse(root=APP.library.config.wd)
	else:
		APP.library.albumpb = gtk.gdk.pixbuf_new_from_file_at_size(APP.library.album_filename, 32, 32)
		APP.artwork.library_artwork_init(APP.librarydata, 32)
		APP.library.library_populate_toplevel_data = store[0]
		APP.library.library_populate_data = store[1]
		APP.library.library_browse(root=APP.library.config.wd)
