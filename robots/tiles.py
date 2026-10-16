import random 

from .scene import load_sprite, ALT_INCREMENT
from .robot_objects import *
from .objects import *
from .animations import *

from .worldloader import register

class Tile(object):
	sprite = 'tile'

	def __init__(self, alt=0):
		self.alt = alt
		self.reroll()

	def reroll(self):
		if hasattr(self, 'TILE_CHOICES') and self.TILE_CHOICES:
			self.sprite = random.choice(self.TILE_CHOICES)

	def draw(self, screen, x, y, draw_south, draw_east, wx, wy):
		s = self.sprites[self.sprite]
		w, h = s.get_size()
		x_left = x - w/2
		y_top = y - h/2
		if draw_south:
			for i, t in enumerate(self.get_edge_tiles_south(draw_south, wx, wy)):
				screen.blit(t, (x_left, y + i * ALT_INCREMENT))
		if draw_east:
			for i, t in enumerate(self.get_edge_tiles_east(draw_east, wx, wy)):
				screen.blit(t, (x, y + i * ALT_INCREMENT))
		screen.blit(s, (x_left, y_top))

	def get_edge_tiles_south(self, height, wx, wy):
		for i in range(height):
			if self.alt > i:
				yield self.sprites['edge-s']
			else:
				yield self.sprites['edge-s-bottom']

	def get_edge_tiles_east(self, height, wx, wy):
		for i in range(height):
			if self.alt > i:
				yield self.sprites['edge-e']
			else:
				yield self.sprites['edge-e-bottom']

#	@classmethod
#	def load_sprites(cls):
#		if hasattr(cls, 'sprites'):
#			return
#		sprites = {}
#		for k, v in cls.SPRITES.items():
#			sprites[k] = load_sprite(v)
#		cls.sprites = sprites

	def can_actor_enter(self, actor, rel_alt):
		"""Returns True if WorldObject actor may enter when actor is rel_alt higher than the floor of this tile"""
		return rel_alt == 0


class EmptyTile(Tile):
	def draw(self, screen, x, y, draw_south, draw_east, wx, wy):
		pass

	@classmethod
	def load_sprites(cls):
		pass

	def can_actor_enter(self, actor, rel_alt):
		return False


class DefaultTile(Tile):
	class Assets:	
		sprites = {
			'tile': 'tiles/default.png',
			'tile2': 'tiles/default2.png',
			'tile3': 'tiles/default3.png',
			'tile4': 'tiles/default4.png',
			'edge-s': 'tiles/default-s.png',
			'edge-e': 'tiles/default-e.png',
			'edge-s-bottom': 'tiles/default-s-bottom.png',
			'edge-e-bottom': 'tiles/default-e-bottom.png',
		}

	TILE_CHOICES = ['tile', 'tile2', 'tile3', 'tile4']

	def __init__(self, alt=0):
		self.alt = alt


class SandTile(Tile):
	class Assets:
		sprites = {
			'tile': 'tiles/sand-1.png',
			'tile2': 'tiles/sand-2.png',
			'tile3': 'tiles/sand-3.png',
			'edge-s-1': 'tiles/sand-s-1.png',
			'edge-s-2': 'tiles/sand-s-2.png',
			'edge-s-3': 'tiles/sand-s-3.png',
			'edge-s-4': 'tiles/sand-s-4.png',
			'edge-s-shell': 'tiles/sand-s-shell.png',
			'edge-e': 'tiles/sand-e.png',
			'edge-s-bottom': 'tiles/sand-s-bottom.png',
			'edge-e-bottom': 'tiles/sand-e-bottom.png',
		}

	TILE_CHOICES = ['tile', 'tile2', 'tile3']

	def get_edge_tiles_south(self, height, wx, wy):
		r = random.Random()
		r.seed(hash((wx, wy))) # hash wasn't good enough on its own
		for i in range(height):
			if self.alt > i:
				if not r.randint(0, 10):
					yield self.sprites['edge-s-shell']
				else:
					edge = r.randint(1, 4)
					yield self.sprites['edge-s-%d' % edge]
			else:
				yield self.sprites['edge-s-bottom']


class FillableTile(Tile):
	def __init__(self, alt=0, filled=None):
		self.alt = alt
		self.filled = None if filled in (None, 'None', '') else filled

	def fill(self, fill):
		self.filled = fill
		fill.play('filling')

	def draw(self, screen, x, y, draw_south, draw_east, wx, wy):
		super(FillableTile, self).draw(screen, x, y, draw_south, draw_east, wx, wy)
		if isinstance(self.filled, str):
			sprite = self.sprites.get('filled-' + self.filled)
			if sprite is not None:
				screen.draw_center(sprite, (x, y))
		elif self.filled:
			self.filled.draw(screen, x, y)

	def accepts_object(self, object):
		return False


class ReservoirTile(object):
	"""A tile that provides an infinite pool of a fluid."""
	def fluid_available(self, direction):
		return self.FLUID

	def draw_up_fluid(self):
		return self.FLUID

	def accepts_fluid(self, fluid, direction):
		return fluid == self.FLUID

	def fill_fluid(self, fluid):
		pass


class WaterTile(FillableTile, ReservoirTile):
	FLUID = 'water'

	class Assets:
		sprites = {
			'tile': 'tiles/water.png',
			'filled-box': 'tiles/box-sunk.png',
			'edge-s': 'tiles/water-s.png',
			'edge-s2': 'tiles/water-s2.png',
			'edge-e': 'tiles/water-e.png',
			'edge-s-bottom': 'tiles/water-s-bottom.png',
			'edge-s2-bottom': 'tiles/water-s2-bottom.png',
			'edge-e-bottom': 'tiles/water-e-bottom.png',
		}
	
	frame = 0
	floating_ice_frames = ['filled-ice', 'filled-ice-2', 'filled-ice-2', 'filled-ice', 'filled-ice-3', 'filled-ice-3']
	FRAME_DELAY = 20

	def fill(self, fill):
		if hasattr(fill, 'floats'):
			if fill.floats():
				fill.play('floating')
			else:
				fill.play('sunk')
		self.filled = fill

#	def draw(self, screen, x, y, draw_south, draw_east, wx, wy):
#		if self.filled:	
#			if self.filled == 'ice':
#				self.frame = (self.frame + 1) % (len(self.floating_ice_frames) * self.FRAME_DELAY)
#				self.sprite = self.floating_ice_frames[self.frame // self.FRAME_DELAY]
#			else:
#				self.sprite = 'filled-' + self.filled
#		else:
#			self.sprite = 'tile'
#		super(FillableTile, self).draw(screen, x, y, draw_south, draw_east, wx, wy)

	def get_edge_tiles_south(self, height, wx, wy):
		if wx % 2 == 0:
			base = 'edge-s'
		else:
			base = 'edge-s2'
		
		for i in range(height):
			if self.alt > i:
				yield self.sprites[base]
			else:
				yield self.sprites[base + '-bottom']

	def can_actor_enter(self, actor, rel_alt):
		hovers = hasattr(actor, 'hovers') and actor.hovers()
		return rel_alt == 0 and hovers or (isinstance(actor, Box) and not self.filled)


class OceanTile(WaterTile):
	FLUID = 'sea-water'

	class Assets:
		sprites = {
			'tile': 'tiles/ocean.png',
			'filled-box': 'tiles/box-sunk.png',
			'edge-s': 'tiles/ocean-s.png',
			'edge-e': 'tiles/ocean-e.png',
			'edge-s-bottom': 'tiles/ocean-s-bottom.png',
			'edge-e-bottom': 'tiles/ocean-e-bottom.png',
		}

	def get_edge_tiles_south(self, height, wx, wy):	
		return Tile.get_edge_tiles_south(self, height, wx, wy)


class SunkBoxTile(WaterTile):
	class Assets:
		sprites = {
			'tile': 'tiles/box-sunk.png',
			'edge-s': 'tiles/default-s.png',
			'edge-e': 'tiles/default-e.png',
			'edge-s-bottom': 'tiles/default-s-bottom.png',
			'edge-e-bottom': 'tiles/default-e-bottom.png',
		}

	def can_actor_enter(self, actor, rel_alt):
		return rel_alt == 0 and isinstance(actor, HoverRobot) or isinstance(actor, Box)


class HoleTile(FillableTile):
	class Assets:
		sprites = {
			'tile': 'tiles/hole.png',
			'filled-water': 'tiles/hole-filled-water.png',
			'edge-s': 'tiles/default-s.png',
			'edge-e': 'tiles/default-e.png',
			'edge-s-bottom': 'tiles/default-s-bottom.png',
			'edge-e-bottom': 'tiles/default-e-bottom.png',
		}

	def __init__(self, alt=0, filled=None):
		self.alt = alt
		self.filled = None if filled in (None, 'None', '') else filled

	def can_actor_enter(self, actor, rel_alt):
		if rel_alt != 0:
			return False
		if not self.filled:
			return self.accepts_object(actor) or hasattr(actor, 'fits_hole') and not actor.fits_hole()
		elif self.filled in ['water']:
			return isinstance(actor, HoverRobot)
		return True

	def accepts_object(self, object):
		return isinstance(object, Box)

	def fluid_available(self, direction):
		if self.filled in ['water']:
			return self.filled

	def draw_up_fluid(self):
		f = self.filled
		self.filled = None
		return f

	def accepts_fluid(self, fluid, direction):
		return not self.filled and fluid in ['water']

	def fill_fluid(self, fluid):
		self.filled = fluid


class LiftTile(Tile):
	class Assets:
		sprites = {
			'lift': 'tiles/lift.png',
			'lift-open': 'tiles/lift-open.png',
			'lift-platform': 'tiles/lift-platform.png',
			'edge-s': 'tiles/default-s.png',
			'edge-e': 'tiles/default-e.png',
			'edge-s-bottom': 'tiles/default-s-bottom.png',
			'edge-e-bottom': 'tiles/default-e-bottom.png',
		}

	def __init__(self, alt=0, open=False, group=None):
		self.alt = alt
		if open:
			self.frac = 1
			self.trigger_frac = 0
		else:
			self.frac = 0
			self.trigger_frac = 1

		self.group = group

	def draw(self, screen, x, y, draw_south, draw_east, wx, wy):
		if self.frac == 0:
			self.sprite = 'lift'
		else:
			self.sprite = 'lift-open'

		super(LiftTile, self).draw(screen, x, y, draw_south, draw_east, wx, wy)

		if self.frac != 0:
			self.draw_center(screen, self.sprites['lift-platform'], x, y - int(self.frac * ALT_INCREMENT))

	def draw_center(self, screen, sprite, x, y):
		w, h = sprite.get_size()
		screen.blit(sprite, (x - w/2, y - h/2))

	def can_actor_enter(self, actor, rel_alt):
		return self.frac == rel_alt

	def on_trigger(self, actors, scene):
		scene.add_animation(LiftAnimation(self, actors, self.trigger_frac))

	def on_untrigger(self, actors, scene):
		scene.add_animation(LiftAnimation(self, actors, 1 - self.trigger_frac))


class ButtonTile(Tile):
	class Assets:
		sprites = {
			'tile': 'tiles/button.png',
			'tile-on': 'tiles/button-on.png',
			'edge-s': 'tiles/default-s.png',
			'edge-e': 'tiles/default-e.png',
			'edge-s-bottom': 'tiles/default-s-bottom.png',
			'edge-e-bottom': 'tiles/default-e-bottom.png',
		}

	def __init__(self, alt=0, trigger=None):
		self.alt = alt
		if trigger is None:
			trigger = str(id(self))
		self.trigger = trigger
		self.group = trigger
		self.triggered = False

	def on_trigger(self, actors, scene):
		self.triggered = True

	def on_untrigger(self, actors, scene):
		self.triggered = False

	def draw(self, screen, x, y, draw_south, draw_east, wx, wy):
		self.sprite = self.triggered and 'tile-on' or 'tile'
		super(ButtonTile, self).draw(screen, x, y, draw_south, draw_east, wx, wy)


class LinkTile(DefaultTile):
	class Assets:
		sprites = {
			'tile': 'tiles/link.png',
		}


class ShoreTile(OceanTile):
	class Assets:
		sprites = {
			'tile': 'tiles/shore-w-1.png',
			'tile-2': 'tiles/shore-w-1.png',
		}
	TILE_CHOICES = ['tile', 'tile-2']


class SandHoleTile(SandTile, HoleTile):
	class Assets:
		sprites = {
			'tile': 'tiles/sand-hole.png',
		}
	TILE_CHOICES = ['tile']


class GrassTile(Tile):
	class Assets:
		sprites = {
			'tile': 'tiles/grass-1.png',
			'tile2': 'tiles/grass-2.png',
			'tile3': 'tiles/grass-3.png',
			'edge-s': 'tiles/grass-s.png',
			'edge-e': 'tiles/grass-e.png',
			'edge-s-top': 'tiles/grass-s-top.png',
			'edge-e-top': 'tiles/grass-e-top.png',
			'edge-s-bottom': 'tiles/grass-s-bottom.png',
			'edge-e-bottom': 'tiles/grass-e-bottom.png',
			'edge-s-1layer': 'tiles/grass-s-1layer.png',
			'edge-e-1layer': 'tiles/grass-e-1layer.png',
		}

	TILE_CHOICES = ['tile', 'tile2', 'tile3']

	def get_edge_tiles_south(self, height, wx, wy):
		for i in range(height):
			if self.alt > i:
				if i == 0:
					yield self.sprites['edge-s-top']
				else:
					yield self.sprites['edge-s']
			else:
				if i == 0:
					yield self.sprites['edge-s-1layer']
				else:
					yield self.sprites['edge-s-bottom']

	def get_edge_tiles_east(self, height, wx, wy):
		for i in range(height):
			if self.alt > i:
				if i == 0:
					yield self.sprites['edge-e-top']
				else:
					yield self.sprites['edge-e']
			else:
				if i == 0:
					yield self.sprites['edge-e-1layer']
				else:
					yield self.sprites['edge-e-bottom']


class GrassHoleTile(GrassTile, HoleTile):
	class Assets:
		sprites = {
			'tile': 'tiles/grass-hole.png',
		}
	TILE_CHOICES = ['tile']


class OrientableTile(Tile):
	# A list of the orientations this tile supports, in clockwise order
	ORIENTATIONS = ['NS', 'EW']
	TILE_CHOICES = []

	def __init__(self, alt=0, orient=None):
		super(OrientableTile, self).__init__(alt)
		if orient in self.ORIENTATIONS:
			self.orient = orient
		else:
			self.orient = self.ORIENTATIONS[0]
		self.sprite = self.orient

	def rotate_clockwise(self):
		i = self.ORIENTATIONS.index(self.orient)
		self.orient = self.ORIENTATIONS[(i + 1) % len(self.ORIENTATIONS)]
		self.sprite = self.orient

	def rotate_anticlockwise(self):
		i = self.ORIENTATIONS.index(self.orient)
		self.orient = self.ORIENTATIONS[(i - 1) % len(self.ORIENTATIONS)]
		self.sprite = self.orient


class RoadTile(OrientableTile, DefaultTile):
	class Assets:
		sprites = {
			'NS': 'tiles/road-ns.png',
			'EW': 'tiles/road-ew.png',
		}


class RoadCornerTile(OrientableTile, DefaultTile):
	class Assets:
		sprites = {
			'ES': 'tiles/road-es.png',
			'NE': 'tiles/road-ne.png',
			'WN': 'tiles/road-wn.png',
			'SW': 'tiles/road-sw.png',
		}
	ORIENTATIONS = ['SW', 'WN', 'NE', 'ES']


class RoadCrossingTile(OrientableTile, DefaultTile):
	class Assets:
		sprites = {
			'NS': 'tiles/crossing-ns.png',
			'EW': 'tiles/crossing-ew.png',
		}

class PavementTile(OrientableTile, DefaultTile):
	class Assets:
		sprites = {
			'NS': 'tiles/pavement-ns.png',
			'EW': 'tiles/pavement-ew.png',
		}

class DirtTile(Tile):
	class Assets:
		sprites = {
			'tile': 'tiles/dirt.png', 
			'edge-s': 'tiles/grass-s.png',
			'edge-e': 'tiles/grass-e.png',
			'edge-s-bottom': 'tiles/grass-s-bottom.png',
			'edge-e-bottom': 'tiles/grass-e-bottom.png',
		}

class DryGrassTile(DirtTile):
	class Assets:
		sprites = {
			'tile': 'tiles/dry-grass.png',
		}

	
register(DefaultTile)
register(SandTile)
register(EmptyTile)
register(ButtonTile, ['trigger'])
register(LiftTile, ['open', 'group'])
#register(SunkBoxTile)
register(WaterTile)
register(OceanTile)
register(ShoreTile)
register(HoleTile, ['filled'])
register(SandHoleTile, ['filled'])
register(LinkTile)
register(GrassTile)
register(DirtTile)
register(DryGrassTile)
register(GrassHoleTile, ['filled'])
register(RoadTile, ['orient'])
register(RoadCornerTile, ['orient'])
register(RoadCrossingTile, ['orient'])
register(PavementTile, ['orient'])
