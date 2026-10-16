import re
import os.path
import math

import pygame
from pygame.locals import *

from .world import World

ALT_INCREMENT = 35
IMAGES_ROOT = 'assets/images'

def load_sprite(fname):
	return pygame.image.load(os.path.join(IMAGES_ROOT, fname)).convert_alpha()


class Actor(object):
	"""An actor is an object with visual presence, but not necessarily physical
	presence, in the 3D world."""
	def __init__(self, x, y, alt=0, description=None):
		self.pos = x, y # actual position
		self.display_pos = None 
		self.alt = alt
		self.display_alt = None
		self.description = description

	def __deepcopy__(self, memo):
		# Sprite surfaces are shared assets; only gameplay state is copied.
		from copy import deepcopy
		clone = self.__class__.__new__(self.__class__)
		memo[id(self)] = clone
		for key, value in self.__dict__.items():
			setattr(clone, key, value if isinstance(value, pygame.Surface) else deepcopy(value, memo))
		return clone

	def play(self, name):
		"""Play a named animation.

		If name is None, configure the base animation."""

	def position(self):
		return self.display_pos or self.pos

	def altitude(self):
		return self.display_alt or self.alt

	def draw_center(self, screen, sprite, x, y):
		w, h = sprite.get_size()
		screen.blit(sprite, (x - w/2, y - h/2))
	
	def tooltip(self):
		return re.sub(r'([a-z])([A-Z])', r'\1 \2', self.__class__.__name__)

	def is_pushable(self, direction):
		return False


#class AnimatedSprite(object):
#	class Instance(object):
#		def __init__(self, a):
#			self.a = a
#			self.ftime = 0
#			self.currentframe = 0
#			self.finished = False
#
#		def draw(self, screen, x, y):
#			framedelay = self.a.framedelay
#			frames = self.a.frames
#
#			if self.finished:
#				return
#
#			self.ftime += 1
#			if self.ftime == framedelay:
#				self.ftime = 0
#				self.currentframe += 1
#				if self.currentframe == len(frames):
#					if self.a.loop:
#						self.currentframe = 0
#					else:
#						self.currentframe = len(frames) - 1
#						self.finished = True
#
#			dx, dy, f = frames[self.currentframe]
#			w, h = f.get_size()
#			x = x + dx - w/2
#			y = y + dy - h/2
#			screen.blit(f, (x, y))
#
#		def is_finished(self):
#			return self.finished
#
#	def __init__(self, frames, framedelay=3, loop=True):
#		self.framedelay = framedelay
#		self.frames = frames
#		self.loop = loop
#
#	def new(self):
#		return AnimatedSprite.Instance(self)
#
#	@staticmethod
#	def load(path, range, framedelay=3, loop=True):
#		fs = [(0, 0, load_sprite(path % i)) for i in range]
#		return AnimatedSprite(fs, framedelay, loop)


class Viewport(object):
	TILE_SIZE = (124, 72)
	def __init__(self, w=640, h=480, x=0, y=0):
		self.x = x
		self.y = y
		self.w = w
		self.h = h

	def world_pos(self, tx, ty):
		"""Center point of the square in the world"""
		tw, th = self.TILE_SIZE
		return int((tx - ty + 1) * (tw / 2 - 1) + 0.5), int((tx + ty + 1) * (th / 2 - 1) + 0.5)

	def screen_pos(self, t_x, t_y, alt=0):
		"""Center of the square on the screen"""
		x, y = self.world_pos(t_x, t_y)
		return x - int(self.x), y - int(self.y) - alt * ALT_INCREMENT

	def translate(self, dx, dy):
		self.x -= dx
		self.y -= dy

	def translate_tiles(self, tx, ty):
		wx0, wy0 = self.world_pos(0, 0)
		wx, wy = self.world_pos(tx, ty)
		self.x -= wx - wx0
		self.y -= wy - wy0

	def move_to(self, tx, ty):
		self.x, self.y = self.world_pos(tx, ty)
		self.x -= self.w/2
		self.y -= self.h/2

	def tile_for_pos(self, sx, sy):
		tw, th = self.TILE_SIZE
		htw = tw / 2 - 1
		hth = th / 2 - 1
		sx = float(sx + self.x)
		sy = float(sy + self.y)
		tx = (sx / htw + sy / hth) / 2 - 1
		ty = sy / hth - tx - 1
		return int(math.floor(tx + 0.5)), int(math.floor(ty + 0.5))

	def screen_bounds(self, actor):
		r = actor.bounds()
		ax, ay = actor.position()
		x, y = self.screen_pos(ax, ay, actor.altitude())
		return pygame.Rect(r.left + x, r.top + y, r.width, r.height)


class Scene(object):
	"""The scene is a 2D representation of a 3D World.

	This class knows how to draw that world and handle mapping of input to world space. A scene
	also contains a list of actors which are displayed in the 3D world but are not physical objects.
	Icons such as move arrows, require this functionality.

	The scene also maintains a list of animations, playing in the world, which
	represent the transition between one world state and another.
	"""
	TILE = 0
	ACTOR = 1

	def __init__(self, world, viewport):
		self.world = world
		self.viewport = viewport
		self.viewport.move_to(self.world.w/2, self.world.h/2)
		self.animations = []
		self.actions = []
		self.gamestate = None
		self.tilecache = None

		self.hovered = None

		self.load_actions()

		self.world.start()

	def load_actions(self):
		"""Graphics for actions get pre-loaded automagically when the scene
		starts. We could try to do this by listing dependencies for objects,
		but then we would have to work around circular import problems."""

		from robots import actions
		for cls in list(actions.__dict__.values()):
			try:
				is_act = issubclass(cls, actions.Action)
			except TypeError:
				continue
			else:
				if is_act:
					self.world.load(cls)

	def draw_order(self, x, y, alt, type):
		return math.ceil(x + y + 0.1 * type), alt, type, x + y

	def tiles(self):
		if self.tilecache:
			return self.tilecache
		ts = []
		for x, y, tile, draw_south, draw_east in self.world.get_tiles():
			if tile is not None:
				ts.append((self.draw_order(x, y, tile.alt, Scene.TILE), Scene.TILE, (x, y, tile.alt), tile, draw_south, draw_east))
		ts.sort(key=lambda item: item[:2])
		self.tilecache = ts
		return ts

	def actors(self):
		ts = []
		for a in self.world.actors + self.actions:
			ax, ay = a.position()
			ts.append((self.draw_order(ax, ay, a.altitude(), Scene.ACTOR), Scene.ACTOR, a))
		return ts

	def add(self, a):
		self.actions.append(a)
		self.world.load(a.__class__)
		a.play(None)

	def remove(self, a):
		self.actions.remove(a)

	def remove_all(self):
		self.actions = []

	def draw_tile(self, screen, t):
		p, t, draw_south, draw_east = t
		x, y, alt = p
		sx, sy = self.viewport.screen_pos(x, y, alt)
		screen.start(hash((id(t), x, y)))
		t.draw(screen, sx, sy, draw_south, draw_east, x, y)
			
	def draw_actor(self, screen, act):
		screen.start(id(act))
		a = act[0]
		x, y = a.position()
		sx, sy = self.viewport.screen_pos(x, y, a.altitude())
		a.draw(screen, sx, sy)

	def draw(self, scenegraph):
		"""Draw the world."""
		scenegraph.fill(0)
		s = self.tiles() + self.actors()
		s.sort(key=lambda item: item[:2])
		for i in s:
			if i[1] == Scene.TILE:
				self.draw_tile(scenegraph, i[2:])
			elif i[1] == Scene.ACTOR:
				self.draw_actor(scenegraph, i[2:])

	def update(self):
		for anim in self.animations[:]:
			anim.update()
			if anim.is_finished():
				self.animations.remove(anim)

	def add_animation(self, a):
		self.animations.append(a)

	def animation_playing(self):
		return len(self.animations) > 0

	def actors_sorted(self, pos):
		"""Actors sorted in hit order.

		The hit testing checks for actions first, as action graphics
		are generally smaller than objects, and so they are clickable
		"through" anything else."""
		from robots.actions import Action
		actors = [a for a in self.actors() if self.viewport.screen_bounds(a[-1]).collidepoint(pos)]
		actors.sort(key=lambda item: item[:2])
		actors.reverse()# detect clicks in reverse draw order
		actions = []
		objects = []
		for a in actors:
			actor = a[-1]
			if isinstance(actor, Action):
				actions.append(actor)
			else:
				objects.append(actor)
		return actions + objects

	def onclick(self, pos):
		if not self.gamestate:
			return
		if self.animation_playing():
			return
		for a in self.actors_sorted(pos):
			if self.gamestate.onclick(a, pos):
				break

	def update_hover(self, pos):
		if not self.gamestate:
			return
		if self.animation_playing():
			if self.hovered:
				self.gamestate.onunhover(self.hovered)
				self.hovered = None
			return
		for a in self.actors_sorted(pos):
			if self.hovered == a:
				return

			if self.gamestate.onhover(a):
				self.gamestate.onunhover(self.hovered)
				self.hovered = a
				return

		if self.hovered:
			self.gamestate.onunhover(self.hovered)
			self.hovered = None
