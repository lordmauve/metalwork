from animations import *
from copy import deepcopy

class WorldObject(object):
	def __init__(self, x, y, alt=0):
		self.pos = x, y # actual position
		self.display_pos = None 
		self.alt = alt
		self.display_alt = None

	def position(self):
		return self.display_pos or self.pos

	def altitude(self):
		return self.display_alt or self.alt

	def is_pushable(self):
		return False


class GraphicsLoader(object):
	def __init__(self):
		self.loaded_classes = set()

	def load(self, cls):
		"""Load the assets for class cls, if they are not already loaded"""
		from scene import load_sprite
		from robots.graphics.animation import AnimatedSprite

		if cls not in self.loaded_classes:
			# print "Loading sprites for", cls
			if hasattr(cls, 'Assets'):
				cls.sprites = {}
				cls.anims = {}
				bs = list(cls.__bases__)
				bs.reverse()
				for superclass in bs:
					cs, ca = self.load(superclass)
					cls.sprites.update(cs)
					cls.anims.update(ca)

				try:
					sprites = cls.Assets.sprites
				except AttributeError:
					pass
				else:
					for k, s in sprites.items():
						cls.sprites[k] = load_sprite(s)

				try:
					anims = cls.Assets.anims
				except AttributeError:
					pass
				else:
					for k, a in anims.items():
						cls.anims[k] = AnimatedSprite.load(a + '.txt')
				cls._assets_loaded = True

			if hasattr(cls, 'load_sprites'):
				cls.load_sprites()
			
			self.loaded_classes.add(cls)
		return getattr(cls, 'sprites', {}), getattr(cls, 'anims', {}) 


class World(GraphicsLoader):
	"""The world is a 3D grid-based model."""
	def __init__(self, w, h, tiles, actors, phrases, title='Unnamed level'):
		super(World, self).__init__()
		from tiles import EmptyTile
		self.w = w
		self.h = h
		self.actors = actors
		self.tiles = tiles
		self.title = title

		# Replace None with EmptyTile
		et = EmptyTile()
		self.groups = {}
		for i in range(w * h):
			x = i % w
			y = i // w
			t = self.tiles[i]
			if t is None:
				self.tiles[i] = et
			self._add_tile(t, (x, y))

		self.phrases = phrases

		self.load_sprites()

	def save_state(self):
		"""Save the world state, to be restored with restart()"""
		self.initial_actors = deepcopy(self.actors)
		self.initial_tiles = deepcopy(self.tiles)

	def start(self):
		"""initialise all actors with their default animations"""
		for a in self.actors:
			a.play(None)
		self.triggered = set()

	def restart(self):
		"""Reset the world to the initial state and reinitialise"""
		try:
			self.actors = deepcopy(self.initial_actors)
			self.tiles = deepcopy(self.initial_tiles)
		except AttributeError:
			pass
		self._rebuild_groups()
		self.start()

	def add(self, wo):
		"""Add an actor to the world, loading assets if necessary"""
		self.actors.append(wo)
		self.load(wo.__class__)

	def remove(self, wo):
		"""Remove an actor from the world"""
		self.actors.remove(wo)

	def get_actors_by_class(self, cls):
		"""Return a list of all actors by class"""
		return [a for a in self.actors if isinstance(a, cls)]

	def load_sprites(self):
		"""Load the sprites for everything already in the world."""
		classes = set()
		for t in self.tiles:
			if t is not None:
				classes.add(t.__class__)
		for a in self.actors:
			classes.add(a.__class__)

		classes -= self.loaded_classes

		for tc in classes:
			self.load(tc)

	@staticmethod
	def create_blank(w=1, h=1):
		from robot_objects import TrackDozer
		from tiles import DefaultTile

		b = DefaultTile()
		actors = [
			TrackDozer(w//2, h//2, orient='S'),
		]
		world = World(w, h, [b] * (w * h), actors, {})
		return world

	def get_objects(self, pos, alt=None):
		x, y = pos
		os = []
		for a in self.actors:
			if a.pos == (x, y):
				if alt is None or a.alt == alt:
					os.append(a)
		return os

	def get_objects_above(self, pos, alt):
		"""Returns objects at the given position in the world or above."""
		x, y = pos
		os = []
		for a in self.actors:
			if a.pos == (x, y):
				if a.alt >= alt:
					os.append(a)
		return os

	def can_actor_enter(self, actor, pos, check_empty=True):
		try:
			dt = self[pos]
		except IndexError:
			return False
		rel_alt = actor.alt - dt.alt
		if not dt.can_actor_enter(actor, rel_alt):
			for o in self.get_objects(pos, actor.alt - 1):
				if hasattr(o, 'supports_object') and o.supports_object(actor):
					break
			else:
				return False
		if check_empty and any(self.get_objects(pos, actor.alt)):
			return False
		return True

	def _add_tile(self, tile, pos):
		"""Generate lookup information for a tile when it is added to the world"""
		if hasattr(tile, 'group'):
			group = tile.group
			try:
				self.groups[group].append((tile, pos))
			except KeyError:
				self.groups[group] = [(tile, pos)]

	def _remove_tile(self, tile):
		"""Update lookup information when a tile is being removed from the world"""
		if hasattr(tile, 'group'):
			self.groups[tile.group] = [(t, pos) for t, pos in self.groups[tile.group] if t != tile]

	def _rebuild_groups(self):
		"""Rebuilds all lookup information by re-adding each tile"""
		self.groups = {}
		for tile, pos in self.enumerate_tiles():
			self._add_tile(tile, pos)

	def enumerate_tiles(self):
		for i in range(self.w * self.h):
			x = i % self.w
			y = i // self.w
			yield self.tiles[i], (x, y)

	def __getitem__(self, coord):
		x, y = coord
		if x < 0 or x >= self.w or y < 0 or y >= self.h:
			raise IndexError("World coordinate out of bounds")
		return self.tiles[y * self.w + x]

	def get(self, x, y):
		from tiles import EmptyTile
		try:
			return self[x, y]
		except IndexError:
			return EmptyTile()

	def __setitem__(self, coord, tile):
		from tiles import EmptyTile
		x, y = coord
		if x < 0 or x >= self.w or y < 0 or y >= self.h:
			if x < 0:
				newx = self.w - x
				tx = -x
			else:
				newx = max(self.w, x + 1)
				tx = 0

			if y < 0:
				newy = self.h - y
				ty = -y
			else:
				newy = max(self.h, y + 1)
				ty = 0

			self.resize_world(newx, newy, tx, ty)
			x += tx
			y += ty

		ctile = self[x, y]
		self._remove_tile(ctile)

		if tile is None:
			tile = EmptyTile()
		
		self.tiles[y * self.w + x] = tile
		tc = tile.__class__
		if tc not in self.loaded_classes:
			tc.load_sprites()
			self.loaded_classes.add(tc)
		self._add_tile(tile, (x, y))

		pos = x, y
		objs = self.get_objects(pos)
		for o in objs:
			if tile.can_actor_enter(o, 0):
				o.alt = tile.alt
				o.display_alt = None
			else:
				self.remove(o)

	def resize_world(self, w, h, tx=0, ty=0):
		newtiles = []
		for i in range(w * h):
			x = i % w
			y = i // w
			newtiles.append(self.get(x - tx, y - ty))
		if tx != 0 or ty != 0:
			for a in self.actors:
				a.pos = a.pos[0] + tx, a.pos[1] + ty
				a.display_pos = None
		self.tiles = newtiles
		self.w = w
		self.h = h

	def pack(self):
		"""TODO: Remove empty tiles at the edges of the world."""
		pass

	def get_tiles(self):
		"""Enumerate all the tiles in the world, for drawing.

		Returns a list of tuples (x, y, tile, draw_south, draw_east).
		draw_south and draw_east are the number of edge layers to draw downwards.
		"""
		def tile_tuple(x, y, draw_south, draw_east):
			from tiles import EmptyTile
			tile = self[x, y]
			try:
				tile_s = self[x, y + 1]
			except IndexError:
				if draw_south:
					draw_south = tile.alt + 1
				else:
					draw_south = 0
			else:
				if isinstance(tile_s, EmptyTile):
					draw_south = tile.alt + 1
				elif tile_s.alt < tile.alt:
					draw_south = tile.alt - tile_s.alt
			try:
				tile_e = self[x + 1, y]
			except IndexError:
				if draw_east:
					draw_east = tile.alt + 1
				else:
					draw_east = 0
			else:
				if isinstance(tile_e, EmptyTile):
					draw_east = tile.alt + 1
				elif tile_e.alt < tile.alt:
					draw_east = tile.alt - tile_e.alt
			return x, y, self[x, y], draw_south, draw_east

		for x in range(self.w - 1):
			for y in range(self.h - 1):
				yield tile_tuple(x, y, False, False)
			yield tile_tuple(x, self.h - 1, True, False)
		for y in range(self.h - 1):
			yield tile_tuple(self.w -1, y, False, True)
		yield tile_tuple(self.w - 1, self.h - 1, True, True)

	def trigger(self, group, scene):
		if group is None:
			return
		for trigger_tile, pos in self.groups[group]:
			trigger_tile.on_trigger(self.get_objects(pos), scene)
		self.triggered.add(group)

	def untrigger(self, group, scene):
		if group is None:
			return
		for trigger_tile, pos in self.groups[group]:
			trigger_tile.on_untrigger(self.get_objects(pos), scene)
		self.triggered.remove(group)

	def update(self, scene, hud):
		"""Updates the world, possibly adding animations to the scene."""
		from objects import Box, Freezer
		from tiles import WaterTile, HoleTile, SunkBoxTile, LinkTile
		from robot_objects import UplinkRobot

		triggers_hit = set() # record which triggers hit on this update so we can work out which ones weren't
		for a in self.actors:
			t = self[a.pos[0], a.pos[1]]
			rel_alt = a.alt - t.alt
			if isinstance(a, Box) and rel_alt == 0:
				# check for boxes to sink
				if isinstance(t, WaterTile) or isinstance(t, HoleTile):
					if not t.filled:
						scene.add_animation(BoxSinkAnimation(scene, a)) 
			if isinstance(a, Freezer) and a.cube:
				# if a freezer has a cube and can eject it, do so
				x, y, alt = a.eject_pos()
				occ = self.get_objects((x, y), alt)
				if not occ:
					scene.add_animation(FreezerEjectAnimation(scene, a))
			if isinstance(a, UplinkRobot):
				# check if UplinkRobots have a link
				a.set_link(isinstance(t, LinkTile))
				if a.triggering is not None:
					group = a.triggering.trigger
					triggers_hit.add(group)
					if group not in self.triggered:
						self.trigger(group, scene)
					try:
						hud.show_messages(self.phrases[group])
					except KeyError:
						pass
			if hasattr(t, 'trigger'):
				group = t.trigger
				triggers_hit.add(group)
				if group not in self.triggered:
					self.trigger(group, scene)
					try:
						hud.show_messages(self.phrases[group])
					except KeyError:
						pass

		# release triggers
		for group in list(self.triggered):
			if group not in triggers_hit:
				self.untrigger(group, scene)
