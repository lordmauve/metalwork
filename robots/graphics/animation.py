import os
import os.path
import re
import pygame

from pygame.rect import Rect


ANIMATIONS_ROOT = 'assets/anims'
IMAGES_ROOT = 'assets/images'

def load_sprite(fname):
	return pygame.image.load(os.path.join(IMAGES_ROOT, fname)).convert_alpha()

class AnimationLayer(object):
	def __init__(self, fname, num_sprites=1, offs=None):
		self.base = fname
		self.num_sprites = num_sprites
		if offs is not None and len(offs) > num_sprites:
			self.frames = len(offs)
		else:
			self.frames = num_sprites
		if self.frames < 1:
			raise ValueError("Invalid number of frames for animation layer %s" % fname)

		sprites = [self.load_frame(f) for f in range(self.num_sprites)]
		self.sprites = []
		for i in range(self.frames):
			s = sprites[i % self.num_sprites]
			if offs is None:
				self.sprites.append((0, 0, s))
			elif offs[i] is None:
				self.sprites.append((0, 0, None))
			else:
				ox, oy = offs[i]
				self.sprites.append((ox, oy, s))

	def load_frame(self, frame):
		if self.num_sprites < 2:
			return load_sprite('%s.png' % self.base)
		else:
			return load_sprite('%s-%d.png' % (self.base, frame))

	def sprite(self, frame):
		s = frame % self.frames
		return self.sprites[s]

	def translate(self, frame, dx, dy):
		s = frame % self.frames
		x, y, sprite = self.sprites[s]
		if sprite is None:
			return
		self.sprites[s] = x + dx, y + dy, sprite

	def draw(self, screen, frame, pos):
		x, y, s = self.sprite(frame)
		if s is None:
			return
		screen.blit(s, (x + pos[0], y + pos[1]))

	def bounds(self, frame):
		x, y, s = self.sprite(frame)
		if s is None:
			return Rect(0,0,0,0)
		return Rect((x, y), s.get_size())


class AnimatedSprite(object):
	def __deepcopy__(self, memo):
		# Animation definitions are shared; Instance holds playback state.
		return self

	class Instance(object):
		"""An instance of an animated sprite.
	
		The frame timings, layer visibility, etc, are here.
		"""
		def __init__(self, a, framedelay, loop):
			self.a = a
			self.ftime = 0
			self.currentframe = 0
			self.loop = loop
			self.framedelay = framedelay
			self.paused = False
			self.finished = False
			self.layer_vis = [True] * len(self.a.layers)

			self.listeners = []

		def pause(self):
			self.paused = True

		def play(self):
			self.paused = False

		def go(self, frame):
			if frame < 0:
				self.currentframe = (self.a.frames + frame) % self.a.frames
			else:
				self.currentframe = frame % self.a.frames
			
			fin = not self.loop and self.currentframe == (self.a.frames - 1)
			if fin and not self.finished:
				self.finished = fin
				self.fire_finish_event()

		def set_layer_visible(self, layer, vis):
			self.layer_vis[self.a._get_layer_id(layer)] = vis

		def get_layer_offset(self, layer):
			layer = self.a.layers[self.a._get_layer_id(layer)]
			x, y, s = layer.sprite(self.currentframe)
			return x, y

		def bounds(self, frame=None):
			if frame is None:
				frame = self.currentframe
			r = Rect(0, 0, 0, 0)
			for i, l in enumerate(self.a.layers):
				if not self.layer_vis[i]:
					continue
				b = l.bounds(frame)
				r.union_ip(b)
			return r

		def draw(self, screen, x, y):
			framedelay = self.framedelay

			if self.finished:
				return

			if not self.paused:
				self.ftime += 1

			if self.ftime == framedelay:
				self.ftime = 0
				if self.currentframe == (self.a.frames - 1):
					if self.loop:
						self.currentframe = 0
					else:
						if not self.finished:
							self.finished = True
							self.fire_finish_event()
				else:
					self.currentframe += 1

			for i, l in enumerate(self.a.layers):
				if self.layer_vis[i]:
					l.draw(screen, self.currentframe, (x, y))

		def add_finish_listener(self, listener):
			self.listeners.append(listener)

		def fire_finish_event(self):
			for l in self.listeners:
				l.animation_finished(self)

		def is_finished(self):
			return self.finished

	def __init__(self, layers=[], layer_names={}, name=''):
		self.layers = layers
		self.frames = max([l.frames for l in layers])
		self.layer_names = layer_names
		self.name = name

	def new(self, framedelay=3, loop=True, start_paused=False):
		inst = AnimatedSprite.Instance(self, framedelay=framedelay, loop=loop)
		if start_paused:
			inst.pause()
		return inst

	def draw(self, screen, frame, pos):
		for l in self.layers:
			l.draw(screen, frame, pos)

	def bounds(self, frame):
		r = None
		for l in self.layers:
			b = l.bounds(frame)
			if r is None:
				r = b
			else:
				r.union_ip(b)
		return r
				

	def __str__(self):
		return self.name

	def _get_layer_id(self, layer):
		if isinstance(layer, int):
			return layer
		try:
			return self.layer_names[layer]
		except KeyError:
			raise KeyError('Invalid layer id %s in animation %s' % (layer, self))

	@staticmethod
	def load(fname):
		layers = []
		base = None
		frames = 0
		offs = None
		layer_names = {}
		name = None

		for l in open(os.path.join(ANIMATIONS_ROOT, fname), 'r'):
			mo = re.match(r'^(base|name|frames|angles|offsets):\s*(.*)', l)
			if not mo:
				continue
			k = mo.group(1)
			v = mo.group(2)
			if k == 'base':
				if base and offs:
					if name:
						layer_names[name] = len(layers) 
					layers.append(AnimationLayer(base, frames, offs))
				base = v
				offs = None
				angles = 0
				name = None
			elif k in ('frames', 'angles'):
				frames = int(v)
			elif k == 'name':
				name = v
			elif k == 'offsets':
				tuples = re.split(r'\s+', v.strip())
				offs = []
				for t in tuples:
					if t == '-':
						offs.append(None)
					else:
						x, y = t.split(',')
						x, y = int(x), int(y)
						offs.append((x, y))
		if base and offs:
			if name:
				layer_names[name] = len(layers) 
			layers.append(AnimationLayer(base, frames, offs))

		if not layers:
			raise ValueError('No layers found')

		return AnimatedSprite(layers, layer_names, name=fname)

