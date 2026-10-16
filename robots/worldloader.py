import os
import codecs

from xml.sax.saxutils import escape
from xml.parsers import expat

from .world import World

OBJECTS = {}

def register(cls, extra_attrs=(), name=None):
	if name is not None:
		OBJECTS[name] = cls, extra_attrs
	else:
		OBJECTS[cls.__name__] = cls, extra_attrs

class WorldLoader(object):
	def __init__(self, fname):
		self.parser = expat.ParserCreate()
		self.parser.StartElementHandler = self.start_element
		self.parser.EndElementHandler = self.end_element
		self.parser.CharacterDataHandler = self.cdata
		self.stack = []
		self.title = fname
		self.phrases = {}
		self.phrase_id = None
		with open(fname, 'rb') as source:
			self.parser.ParseFile(source)

	def object_for_name(self, name):
		try:
			return OBJECTS[name]
		except KeyError:
			raise ValueError('Unknown object name %s' % name)

	def start_element(self, name, attrs):
		from .robot_objects import Robot
		from .tiles import Tile
		from .scene import Actor

		self.stack.append(name)
		if name == 'World':
			self.w = int(attrs['w'])
			self.h = int(attrs['h'])
			if 'default' in attrs:
				default = attrs['default']
				tile, extra_attrs = self.object_for_name(default)
				if not issubclass(tile, Tile):
					raise ValueError("Invalid default tile class %s" % default)
				self.tiles = [tile() for i in range(self.w * self.h)]
			else:
				self.tiles = [None for i in range(self.w * self.h)]
			self.actors = []
		elif name == 'Title':
			self.title = ''
		elif name == 'Phrase':
			self.phrase_id = attrs['id']
			self.phrase = ''
		else:
			t, extra_attrs = self.object_for_name(name)
			x, y = [int(c) for c in attrs['at'].split(',')]
			
			if 'alt' in attrs:
				alt = int(attrs['alt'])
			else:
				alt = 0

			atts = {}
			for k in extra_attrs:
				v = attrs.get(k, None)
				if v:
					atts[k] = v

			if issubclass(t, Tile):
				self.tiles[y * self.w + x] = t(alt=alt, **atts)
			elif issubclass(t, Actor):
				self.actors.append(t(x, y, alt, **atts))
	
	def end_element(self, name):
		self.stack.pop()
		if name == 'Phrase':
			try:
				self.phrases[self.phrase_id].append(self.phrase)
			except KeyError:
				self.phrases[self.phrase_id] = [self.phrase]
			self.phrase_id = None

	def cdata(self, data):
		if self.stack[-1] == 'Title':
			self.title = data
		if self.phrase_id:
			self.phrase += data

	def get_world(self):
		return World(self.w, self.h, self.tiles, self.actors, self.phrases, self.title)


class WorldSaver(object):
	ENCODING = 'UTF-8'

	def __init__(self, world):
		self.world = world
		self.type_map = {}
		for name, ob in list(OBJECTS.items()):
			cls, attrs = ob
			self.type_map[cls] = name, attrs

	def save(self, filename):
		self.world.pack()
		encoder = codecs.getwriter(self.ENCODING)
		tmp = filename + '.tmp'
		f = open(tmp, 'wb')
		self.write_world(encoder(f))
		f.close()
		os.rename(tmp, filename)

	def write_world(self, f):
		print('<?xml version="1.0" encoding="%s" ?>' % self.ENCODING, file=f)
		print('<World w="%d" h="%d">' % (self.world.w, self.world.h), file=f)
		if self.world.title:
			print('\t<Title>%s</Title>' % escape(self.world.title), file=f)
			print(file=f)

		self.write_tiles(f)
		self.write_actors(f)
		print('</World>', file=f)

	def attrs(self, obj, pos=None):
		if pos is None:
			pos = obj.pos
		attrs = [('at', '%d,%d' % pos)]
		if obj.alt:
			attrs += [('alt', str(obj.alt))]
		name, extra_attrs = self.type_map[obj.__class__]
	
		if hasattr(obj, 'serialize'):
			attrs += list(obj.serialize().items())
		else:
			for k in extra_attrs:
				v = getattr(obj, k)
				if v:
					attrs += [(k, str(v))]
		
		return ' '.join([escape(name)] + ['%s="%s"' % (escape(k), escape(v)) for k, v in attrs])
		
	def write_tiles(self, f):
		for t, pos in self.world.enumerate_tiles():
			print('\t<%s/>' % (self.attrs(t, pos)), file=f)
		print(file=f)

	def write_actors(self, f):
		for a in self.world.actors:
			print('\t<%s/>' % (self.attrs(a)), file=f)
		print(file=f)
