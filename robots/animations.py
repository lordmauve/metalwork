import math
from .compass import *

"""This module contains "Animations", which are animated controllers for world state.

Each animation runs for a certain number of frames after which they will automatically be
removed from the animation queue. They should leave the world in a consistent state.
"""

def linear_interpolation(currentframe, frames):
	"""Returns a value between 0.0 and 1.0 that varies linearly with currentframe."""
	return float(currentframe) / float(frames)

def cosine_interpolation(currentframe, frames):
	"""Returns a value between 0.0 and 1.0 that varies in a cosine function with currentframe."""
	return math.sin(0.5 * math.pi * (float(currentframe) / frames)) ** 2


class Animation(object):
	def update(self):
		"""Update state for next frame of the animation"""

	def is_finished(self):
		return True


class Interpolation(Animation):
	def __init__(self, frames=30, interpolation=cosine_interpolation):
		self.currentframe = 0
		self.frames = frames
		self.interp = interpolation

	def is_finished(self):
		return self.currentframe >= self.frames

	def update(self):
		self.currentframe += 1
		if self.is_finished():
			self.finish()
		else:
			frac = self.interp(self.currentframe, self.frames)
			self.step(frac)

	def step(self, frac):
		"""Called each frame; update the animation for value frac."""

	def finish(self):
		"""Called when the animation finishes."""


class MoveAnimation(Interpolation):
	def __init__(self, actor, dx, dy, frames=50, interpolation=cosine_interpolation):
		super(MoveAnimation, self).__init__(frames, interpolation)
		self.dx = dx
		self.dy = dy
		self.actor = actor

	def finish(self):
		x, y = self.actor.pos	
		self.actor.pos = x + self.dx, y + self.dy
		self.actor.display_pos = None

	def step(self, frac):
		x, y = self.actor.pos	
		nx = x + frac * self.dx
		ny = y + frac * self.dy
		self.actor.display_pos = nx, ny


class Pause(Animation):
	def __init__(self, frames=30):
		self.currentframe = 0
		self.frames = frames

	def is_finished(self):
		return self.currentframe >= self.frames

	def update(self):
		self.currentframe += 1

class AnimationSequence(Animation):
	"""Plays the given animations in sequence"""
	def __init__(self, animations):
		self.animations = animations
		self.current_anim = animations.pop(0)

	def is_finished(self):
		return self.current_anim is None
	
	def finish(self):
		pass

	def update(self):
		if self.current_anim.is_finished():
			try:
				self.current_anim = self.animations.pop(0)
			except IndexError:
				self.current_anim = None
				self.finish()
				return
		self.current_anim.update()


class AnimationList(Animation):
	"""Plays the given animations in parallel"""
	def __init__(self, animations):
		self.animations = animations

	def is_finished(self):
		return not self.animations
	
	def finish(self):
		pass

	def update(self):
		for a in self.animations:
			a.update()
		self.animations = [a for a in self.animations if not a.is_finished()]


class TurnAnimation(Animation):
	"""Turns the robot then runs the next animation"""
	def __init__(self, actor, direction):
		self.actor = actor
		
		self.direction = direction
		current_orient = Compass.direction_for_id(actor.orient).frame
		target_orient = direction.frame

		fsp = []
		fsn = []
		for i in range(7):
			f = (current_orient + i) % 12
			fsp += [f]
			if f == target_orient:
				self.fs = fsp
				break
			f = (current_orient - i) % 12
			fsn += [f]
			if f == target_orient:
				self.fs = fsn
				break
		self.frame = 0
		self.framedelay = 4
		self.f = 0

	def is_finished(self):
		return self.frame >= len(self.fs)

	def finish(self):
		self.actor.display_orient = None
		self.actor.orient = self.direction.id

	def update(self):
		if self.f == self.framedelay:
			self.frame += 1
			self.f = 0
		else:
			self.f += 1
		if self.frame < len(self.fs):
			self.actor.display_orient = self.fs[self.frame]
		else:
			self.finish()


class PushAnimation(Animation):
	def __init__(self, actor, target, dx, dy, frames=90):
		self.actor_anim = MoveAnimation(actor, dx, dy, frames)
		self.target_anim = MoveAnimation(target, dx, dy, frames-30, interpolation=linear_interpolation)

	def update(self):
		if not self.actor_anim.is_finished():
			self.actor_anim.update()
		if self.actor_anim.currentframe >= 20 and not self.target_anim.is_finished():	
			self.target_anim.update()

	def finish(self):
		pass

	def is_finished(self):
		return self.actor_anim.is_finished() and self.target_anim.is_finished()


class LiftAnimation(Interpolation):
	def __init__(self, tile, actors, target):
		super(LiftAnimation, self).__init__()
		self.tile = tile
		self.actors = actors
		self.target = target
		self.initial = tile.frac

	def step(self, frac):
		self.tile.frac = frac * self.target + (1 - frac) * self.initial
		for a in self.actors:
			a.display_alt = a.alt + (self.tile.frac - self.initial)

	def finish(self):
		self.tile.frac = self.target
		for a in self.actors:
			a.alt = a.alt + (self.target - self.initial)
			a.display_alt = None


class BoxSinkAnimation(Animation):
	def __init__(self, scene, box):
		self.box = box
		self.scene = scene
		self.box.play('drop')
		self.finished = False

	def is_finished(self):
		f = self.box.anim.is_finished()
		if f and not self.finished:
			self.finish()
		return f

	def finish(self):
		self.scene.world.remove(self.box)
		self.scene.world[self.box.pos].fill(self.box)


class AdjacentInteraction(AnimationSequence):
	"""This is an animation where a robot moves partway towards an adjacent tile to
	interact with it, pauses, then moves back."""
	MOVE_FRAC = 0.35  # The fraction of the way to the next tile to move

	def __init__(self, actor, direction, interaction_animation=None):
		x, y = direction.vector
		x *= self.MOVE_FRAC
		y *= self.MOVE_FRAC
		self.pos = actor.pos  # store pos to avoid slight errors from the MoveAnimations
		if interaction_animation is None:
			interaction_animation = Pause(45)
		anims = [MoveAnimation(actor, x, y), interaction_animation, MoveAnimation(actor, -x, -y)]
		super(AdjacentInteraction, self).__init__(anims)

	def update(self):
		super(AdjacentInteraction, self).update()
		if self.current_anim and self.current_anim.is_finished():
			if len(self.animations) == 2:
				self.on_interaction_start()
			elif len(self.animations) == 1:
				self.on_interaction_finish()

	def on_interaction_start(self):
		"""Subclasses may implement this method to specify what happens when the interaction starts"""

	def on_interaction_finish(self):
		"""Subclasses may implement this method to specify what happens when the interaction finishes"""

	def finish(self):
		self.actor.pos = self.pos # restore pos


class PumpAnimation(AdjacentInteraction):
	MOVE_FRAC = 0.35
	def __init__(self, actor, direction, target):
		self.actor = actor
		self.target = target
		super(PumpAnimation, self).__init__(actor, direction)

	def on_interaction_start(self):
		fill = self.actor.get_fill()
		if not fill and hasattr(self.target, 'start_draw_up_fluid'):
			self.target.start_draw_up_fluid()
		elif fill and hasattr(self.target, 'start_fill_fluid'):
			self.target.start_fill_fluid()

	def on_interaction_finish(self):
		fill = self.actor.get_fill()
		if fill:
			self.target.fill_fluid(fill)
			self.actor.set_fill(None)
		else:
			self.actor.set_fill(self.target.draw_up_fluid())


class FreezerAnimation(AdjacentInteraction):
	MOVE_FRAC = 0.2
	def __init__(self, actor, direction, freezer, world):
		self.actor = actor
		self.freezer = freezer
		self.world = world
		super(FreezerAnimation, self).__init__(actor, direction)

	def on_interaction_start(self):
		self.freezer.play('freeze')

	def on_interaction_finish(self):
		self.actor.set_fill(None)
		self.freezer.cube = True


class FreezerEjectAnimation(Animation):
	def __init__(self, scene, freezer):
		self.freezer = freezer
		self.scene = scene
		self.freezer.play('eject')
		self.finished = False

		# move the freezer south one unit until the animation finishes, to hack z-order
		# this is compensated for in the animation loading
		self.freezer.display_pos = self.freezer.eject_pos()[:2]

	def is_finished(self):
		f = self.freezer.anim.is_finished()
		if f and not self.finished:
			self.finish()
		return f

	def finish(self):
		from robots.objects import Ice
		self.freezer.display_pos = None
		ice = Ice(*self.freezer.eject_pos())
		self.scene.world.add(ice)
		ice.play(None)
		self.freezer.cube = False
