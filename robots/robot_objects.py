import random
from pygame import Rect
from worldloader import register

from scene import Actor, load_sprite

from graphics.animation import AnimatedSprite
from compass import *

class Robot(Actor):
	class Assets:
		anims = {
			'bulb-flare': 'bulb-on'
		}

	SPRITE = 'robot-base'
	def __init__(self, x, y, alt=0, orient='E', description=None):
		super(Robot, self).__init__(x, y, alt)
		self.orient = orient
		self.display_orient = None
		self.active = False
		self.description = description

	def rotate_clockwise(self):
		"""Rotates the robot instantly clockwise by 90 degrees"""
		# For editor, mainly
		rots = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}
		self.orient = rots[self.orient]

	def rotate_anticlockwise(self):
		"""Rotates the robot instantly anticlockwise by 90 degrees"""
		rots = {'N': 'W', 'E': 'N', 'S': 'E', 'W': 'S'}
		self.orient = rots[self.orient]

	def play(self, name):
		if not name:
			self.anim = self.anims[self.SPRITE].new(start_paused=True)
			self.anim.set_layer_visible('headlamp1', False)
			self.anim.set_layer_visible('headlamp2', False)
	
	def set_active(self, a):
		self.active = a

		self.anim.set_layer_visible('bulb', not a)
		self.anim.set_layer_visible('headlamp1', a)
		self.anim.set_layer_visible('headlamp2', a)

		if a:
			self.description = None

	def is_active(self):
		return self.active

	def get_bulb(self):
		try:
			return self.bulb
		except AttributeError:
			self.bulb = self.anims['bulb-flare'].new(framedelay=4)
			return self.bulb

	def draw(self, screen, x, y):
		if self.display_orient is not None:
			f = self.display_orient
		else:
			f = {'N': 0, 'E': 3, 'S': 6, 'W': 9}[self.orient]
		anim = self.anim
		anim.go(f)
		anim.draw(screen, x, y)
		if self.is_active():
			bx, by = anim.get_layer_offset('bulb')
			self.get_bulb().draw(screen, x + bx + 8, y + by + 12)

	def bounds(self):
		return self.anim.bounds(0)


class TrackRobot(Robot):
	class Assets:
		anims = {
			'robot-base': 'robots/robot-base'
		}


class HoverRobot(Robot):
	class Assets:
		anims = {
			'robot-hover': 'robots/robot-hover'
		}

	SPRITE = 'robot-hover'
	HOVER_ANIM = [0] * 8 + [1] * 4 + [2] * 8 + [1] * 4

	def __init__(self, *args, **kwargs):
		super(HoverRobot, self).__init__(*args, **kwargs)
		self.phase = random.randint(0, len(self.HOVER_ANIM))

	def draw(self, screen, x, y):
		self.phase = (self.phase + 1) % len(self.HOVER_ANIM)
		yoff = self.HOVER_ANIM[self.phase]
		super(HoverRobot, self).draw(screen, x, y - yoff)

	def hovers(self):
		return True

	def is_pushable(self):
		return True


class Dozer(object):
	pass


class TrackDozer(Dozer, TrackRobot):
	class Assets:
		anims = {
			'robot-dozer': 'robots/robot-dozer'
		}

	SPRITE = 'robot-dozer'


class HoverDozer(Dozer, HoverRobot):
	class Assets:
		anims = {
			'robot-hoverdozer': 'robots/robot-hoverdozer'
		}

	SPRITE = 'robot-hoverdozer'


class TankerRobot(TrackRobot):
	class Assets:
		anims = {
			'robot-tanker': 'robots/robot-tanker'
		}

	SPRITE = 'robot-tanker'
	filled = None
	gauge_layers = ['water', 'sea-water', 'milk']

	def is_empty(self):
		return self.filled is None

	def set_fill(self, fill):
		if fill:
			self.play('filled-' + fill)
			self.filled = fill
		else:
			self.play('empty')
			self.filled = None

	def get_fill(self):
		return self.filled

	def play(self, name):
		super(TankerRobot, self).play(name)
		if not name or name == 'empty':
			for l in self.gauge_layers:
				self.anim.set_layer_visible('gauge-%s' % l, False)
		else:
			for l in self.gauge_layers:
				vis = name == ('filled-%s' % l)
				self.anim.set_layer_visible('gauge-%s' % l, vis)

	def accepts_fluid(self, fluid, direction):
		return self.is_empty() and direction == Compass.direction_for_id(self.orient).opposite()

	def fill_fluid(self, fluid):
		self.set_fill(fluid)


class UplinkRobot(TrackRobot):
	class Assets:
		anims = {
			'robot-uplink': 'robots/robot-uplink'
		}

	SPRITE = 'robot-uplink'
	link = False
	triggering = None

	def set_link(self, link):
		self.link = link
		self.anim.set_layer_visible('bulb', self.active and not link)
		self.anim.set_layer_visible('bulb-green', self.active and link)

		if not link and self.triggering is not None:
			self.triggering.play('default')
			self.triggering = None

	def can_trigger(self, target):
		"""Can the robot trigger this target?"""
		return self.link and self.triggering != target
	
	def get_link(self):	
		return self.link	

	def draw(self, screen, x, y):
		if self.display_orient is not None:
			f = self.display_orient
		else:
			f = {'N': 0, 'E': 3, 'S': 6, 'W': 9}[self.orient]
		anim = self.anim
		anim.go(f)
		if self.active and self.link:
			anim.set_layer_visible('bulb-green', random.randint(0,6) != 0)
		anim.draw(screen, x, y)

	def play(self, name):
		super(UplinkRobot, self).play(name)
		if not name:
			self.anim.set_layer_visible('bulb', False)
			self.anim.set_layer_visible('bulb-green', False)

	def set_active(self, a):
		self.active = a

		self.anim.set_layer_visible('bulb', a and not self.link)
		self.anim.set_layer_visible('bulb-green', False)
		self.anim.set_layer_visible('headlamp1', a)
		self.anim.set_layer_visible('headlamp2', a)

		if a:
			self.description = None

register(TrackRobot, ['description', 'orient'])
register(HoverRobot, ['description', 'orient'])
register(TrackDozer, ['description', 'orient'])
#register(HoverDozer, ['description', 'orient'])
register(TankerRobot, ['description', 'orient'])
register(UplinkRobot, ['description', 'orient'])
