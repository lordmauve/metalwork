import random

from pygame import Rect
from scene import Actor, load_sprite
from graphics.animation import AnimatedSprite

from robots.compass import *
from robots.worldloader import register


class PassiveObject(Actor):
	Y_OFF = 0
	anim = None

	def draw(self, screen, x, y):
		if self.anim and self.anim.is_finished():
			self.play(None)
		
		if self.anim:
			self.anim.draw(screen, x, y)
		else:
			self.draw_center(screen, self.sprite, x, y + self.Y_OFF)

	def bounds(self):
		if self.anim:
			return self.anim.bounds()
		w, h = self.sprite.get_size()
		return Rect(-w/2, self.Y_OFF - h/2, w, h)


class AutoRegisterMetaClass(type):
	def __new__(cls, name, bases, dict):
		t = super(AutoRegisterMetaClass, cls).__new__(cls, name, bases, dict)
		if name != 'Scenery':
			# Could try to automatically generate the parameters
			# from dict['__init__'].im_func.func_code.co_varnames?
			register(t, ['description'])
		return t


class Scenery(PassiveObject):
	__metaclass__ = AutoRegisterMetaClass
	@classmethod
	def load_sprites(cls):
		if hasattr(cls, 'SPRITE'):
			cls.sprite = load_sprite(cls.SPRITE)


class PalmTree(Scenery):
	Y_OFF = -35
	SPRITE = 'objects/palm-tree.png'


class FruitTree(Scenery):
	Y_OFF = -35
	SPRITE = 'objects/fruit-tree.png'

class Fence(Scenery):
	Y_OFF = -12
	class Assets:
		sprites = {
			'NS': 'objects/fence-ns.png',
			'EW': 'objects/fence-ew.png',
		}

	def __init__(self, x, y, alt=0, orient='', description=''):
		super(Fence, self).__init__(x, y, alt, description)
		if orient == 'EW':
			self.orient = 'EW'
		else:
			self.orient = 'NS'

	def play(self, name):
		self.sprite = self.sprites[self.orient]

	def rotate_anticlockwise(self):
		self.orient = (self.orient == 'EW') and 'NS' or 'EW'
		self.play(None)

	def tooltip(self):
		return 'Fence'


class Pushable(PassiveObject):
	"""Class for objects that are pushable"""

	def is_pushable(self, direction):
		return True

	def friction_distance(self):
		"""The friction distance is the maximum distance an object will
		travel when pushed. Thus low-friction objects have a very high
		friction distance. Normal friction would be 1."""
		return 1

	def fits_hole(self):
		return True


class Box(Pushable):
	class Assets:
		sprites = {
			'box': 'objects/box.png',
			'sunk': 'objects/box-sunk.png',
		}
		anims = {
			'box-drop': 'objects/box-drop',
#			'box-burn': 'objects/box-burn'
		}
	Y_OFF = -18

	def floats(self):
		return True

	def play(self, name):
		if name == 'filling':
			self.anim = self.anims['box-drop'].new(1, start_paused=True)
			self.anim.go(-1)
		elif name == 'drop':
			self.anim = self.anims['box-drop'].new(2, loop=False)
		else:
			self.anim = None
			self.sprite = self.sprites['box']


class Container(Pushable):
	def __init__(self, x, y, alt=0, description=''):
		super(Container, self).__init__(x, y, alt, description)
		self.fill = None

	def floats(self):
		return self.fill is None

	def accepts_fill(self, fill, direction):
		return fill is None

	def fill(self, fill):
		self.fill = fill


class Bucket(Container, Box):
	class Assets:
		sprites = {
			'box': 'objects/bucket.png',
		}
		anims = {
			'box-drop': 'objects/bucket-drop',
			'floating': 'objects/bucket-floating'
		}
	Y_OFF = -18

	def play(self, name):
		if name == 'floating':
			self.anim = self.anims['floating'].new(15)
		elif name == 'drop':
			self.anim = self.anims['box-drop'].new(4, loop=False)
		else:
			super(Bucket, self).play(name)

class RubberRing(Pushable):
	class Assets:
		sprites = {
			'toy': 'objects/beach-toy.png',
		}
	Y_OFF = -10

	def hovers(self):
		return True

	def play(self, name):
		self.sprite = self.sprites['toy']

	def fits_hole(self):
		return False


class Ice(Box):
	class Assets:
		sprites = {
			'box': 'objects/ice.png' 
		}
		anims = {
			'box-drop': 'objects/ice-drop',
			'floating': 'objects/ice-floating'
		}

	def play(self, name):
		if name == 'floating':
			self.anim = self.anims['floating'].new(15)
		elif name == 'drop':
			self.anim = self.anims['box-drop'].new(4, loop=False)
		else:
			super(Ice, self).play(name)

	def floats(self):
		return True

	def friction_distance(self):
		return 2 ** 31 # Infinity!


class Freezer(PassiveObject):
	class Assets:
		anims = {
			'freezer': 'objects/freezer',
			'freezer-eject': 'objects/freezer-eject',
		}
	SPRITE = 'objects/freezer-0.png'
	Y_OFF = -21

	cube = False

	def __init__(self, *args, **kwargs):
		if 'cube' in kwargs:
			cube = kwargs.pop('cube')
			self.cube = (cube is not None and cube.lower() == 'true')
		super(Freezer, self).__init__(*args, **kwargs)

	def play(self, name):
		if name == 'freeze':
			self.anim = self.anims['freezer'].new(10, loop=False)
		elif name == 'eject':
			self.anim = self.anims['freezer-eject'].new(6, loop=False)
		else:
			self.anim = self.anims['freezer'].new(start_paused=True)
			if self.cube:
				self.anim.go(5)

	def accepts_fluid(self, fluid, direction):
		return direction == Compass.EAST and fluid == 'water' and not self.cube

	def fill_fluid(self, fluid):
		self.cube = True

	def eject_pos(self):
		return self.pos[0], self.pos[1] + 1, self.alt

	@classmethod
	def load_sprites(cls):
		for l in cls.anims['freezer-eject'].layers:
			for f in range(l.frames):
				l.translate(f, 62, -36)


class Cow(PassiveObject):
	class Assets:
		anims = {
			'cow-s': 'objects/cow-s',
			'cow-e': 'objects/cow-e',
		}

	FLUID = 'milk'
	Y_OFF = -15
	filled = True

	def __init__(self, x, y, alt=0, orient='', description=''):
		super(Cow, self).__init__(x, y, alt, description)
		if orient == 'E':
			self.orient = 'E'
		else:
			self.orient = 'S'

	def rotate_anticlockwise(self):
		self.orient = (self.orient == 'E') and 'S' or 'E'
		self.play(None)

	def play(self, name):
		a = self.anims['cow-' + self.orient.lower()]
		if name == 'emptying':
			self.anim = a.new(9, loop=False)
			self.anim.add_finish_listener(self)
		else:
			if self.filled:
				frame = 0
			else:
				frame = -1
			self.anim = a.new(start_paused=True)
			self.anim.go(frame)

	def animation_finished(self, anim):
		self.play(None)

	def fluid_available(self, direction):
		if self.filled:
			if self.orient == 'S' and direction in [Compass.EAST, Compass.WEST] or \
				self.orient == 'E' and direction in [Compass.NORTH, Compass.SOUTH]:
				return self.FLUID

	def start_draw_up_fluid(self):
		self.play('emptying')

	def draw_up_fluid(self):
		self.filled = False
		self.play(None)
		return self.FLUID


class Downlink(PassiveObject):
	class Assets:
		anims = {'downlink': 'objects/downlink'}

	def __init__(self, x, y, alt=0, description=None, trigger=None):
		self.trigger = trigger
		super(Downlink, self).__init__(x, y, alt)

	def play(self, name):
		if name == 'link':
			self.anim.set_layer_visible('bulb', False)
			self.anim.set_layer_visible('bulb-green', True)
		else:
			self.anim = self.anims['downlink'].new(start_paused=True)
			self.anim.set_layer_visible('bulb', True)
			self.anim.set_layer_visible('bulb-green', False)

	@classmethod
	def load_sprites(cls):
		if hasattr(cls, 'anims'):
			return
		cls.anims = {
			'downlink': AnimatedSprite.load('objects/downlink.txt'),
		}

	def bounds(self):
		return self.anim.bounds()


class Car(Pushable):
	class Assets:
		sprites = {
			'E-red': 'objects/car-e-red.png',
			'S-red': 'objects/car-s-red.png',
			'E-yellow': 'objects/car-e-yellow.png',
			'S-yellow': 'objects/car-s-yellow.png',
			'E-green': 'objects/car-e-green.png',
			'S-green': 'objects/car-s-green.png',
			'E-white': 'objects/car-e-white.png',
			'S-white': 'objects/car-s-white.png',
			'E-silver': 'objects/car-e-silver.png',
			'S-silver': 'objects/car-s-silver.png',
			'E-black': 'objects/car-e-black.png',
			'S-black': 'objects/car-s-black.png',
			'E-blue': 'objects/car-e-blue.png',
			'S-blue': 'objects/car-s-blue.png',
		}
	ORIENTATIONS = ['S', 'E']
	COLOURS = ['red', 'yellow', 'green', 'white', 'silver', 'black', 'blue']
	Y_OFF = -10

	def __init__(self, x, y, alt=0, description='', orient=None, colour=None):
		super(Car, self).__init__(x, y, alt, description)
		if orient in self.ORIENTATIONS:
			self.orient = orient
		else:
			self.orient = self.ORIENTATIONS[0]

		if colour in self.COLOURS:
			self.colour = colour
		else:
			self.reroll()

	def is_pushable(self, direction):
		if self.orient == 'S':
			return direction in [Compass.SOUTH, Compass.NORTH]
		else:
			return direction in [Compass.EAST, Compass.WEST]

	def fits_hole(self):
		return False

	def play(self, name):
		self.sprite = self.sprites['%s-%s' % (self.orient, self.colour)]

	def reroll(self):
		self.colour = random.choice(self.COLOURS)

	# for usability we only provide rotate_anticlockwise for objects with only two orientations
	def rotate_anticlockwise(self):
		i = self.ORIENTATIONS.index(self.orient)
		self.orient = self.ORIENTATIONS[(i - 1) % len(self.ORIENTATIONS)]
		self.play(None)


class Rig(Pushable):
	class Assets:
		sprites = {
			'rig': 'objects/rig.png',
		}

	Y_OFF = -16

	def play(self, name):
		self.sprite = self.sprites['rig']
	
	def fits_hole(self):
		return False

	def supports_object(self, object):
		return True


register(Box, ['description'])
register(Cow, ['description'])
register(Ice, ['description'])
register(Freezer, ['description', 'cube'])
register(Downlink, ['description', 'trigger'])
register(Bucket, ['description'])
register(RubberRing, ['description'])
register(Car, ['description', 'orient', 'colour'])
register(Rig, ['description'])
