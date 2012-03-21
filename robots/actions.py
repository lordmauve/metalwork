from pygame import Rect
from scene import Actor, load_sprite

from robots.graphics.animation import AnimatedSprite
from animations import *
from compass import *

from tiles import Tile

from robot_objects import TankerRobot


class Action(Actor):
	sprite = None

	def __init__(self, x, y, actor):
		super(Action, self).__init__(x, y, actor.alt)
		self.actor = actor

	def draw(self, screen, x, y):
		try:
			self.draw_center(screen, self.sprite, x, y)
		except AttributeError:
			self.anim.draw(screen, x, y)

	def bounds(self):
		try:
			w, h = self.sprite.get_size()
			return Rect(-w/2, -h/2, w, h)
		except AttributeError:
			return self.anim.bounds()


class MoveAction(Action):
	class Assets:
		sprites = {
			'move-N': 'actions/move-N.png',
			'move-S': 'actions/move-S.png',
			'move-E': 'actions/move-E.png',
			'move-W': 'actions/move-W.png',
		}

	ARROW_OFF = 0.7
	SPRITE_NAME = 'move-%s'

	def __init__(self, direction, actor):
		self.direction = direction

		x, y = actor.pos
		dx, dy = direction.vector
		self.dest = x + dx, y + dy
		super(MoveAction, self).__init__(x + self.ARROW_OFF * dx, y + self.ARROW_OFF * dy, actor)

	def play(self, name):
		self.sprite = self.sprites[self.SPRITE_NAME % self.direction.id]

	def tooltip(self):
		return "Move"

	def requires_turn(self, actor):
		mo = Compass.direction_for_id(actor.orient).vector
		return (bool(mo[0]) ^ bool(self.direction.vector[0])) or (bool(mo[1]) ^ bool(self.direction.vector[1]))

	def perform(self, actor, gamestate, scene):
		move = MoveAnimation(actor, *self.direction.vector)
		if self.requires_turn(actor):
			scene.add_animation(AnimationSequence([TurnAnimation(actor, self.direction), move]))
		else:
			scene.add_animation(move)


class PushAction(Action):
	class Assets:
		sprites = {
			'push-N': 'actions/push-N.png',
			'push-S': 'actions/push-S.png',
			'push-E': 'actions/push-E.png',
			'push-W': 'actions/push-W.png',
		}

	SPRITE_NAME = 'push-%s'
	ARROW_OFF = 1

	def __init__(self, direction, actor, target):
		self.direction = direction

		x, y = actor.pos
		dx, dy = direction.vector
		self.dest = x + dx, y + dy

		super(PushAction, self).__init__(self.dest[0], self.dest[1], actor=actor)

		tx, ty = target.pos
		self.target = target
		self.target_dest = tx + direction.vector[0], ty + direction.vector[1]
		self.alt = target.alt + 1

	def tooltip(self):
		return "Push " + self.target.tooltip()

	def play(self, name):
		self.sprite = self.sprites[self.SPRITE_NAME % self.direction.id]

	def perform(self, actor, gamestate, scene):
		from robots.objects import Ice

		world = scene.world
		target = self.target
		dx, dy = self.direction.vector
		dist = 1
		if target.friction_distance() > 1:
			dest = self.target_dest
			for i in xrange(1, target.friction_distance()):
				tile = world.get(*dest)
				try:
					acc = tile.accepts_object
				except AttributeError:
					pass
				else:
					if acc(self.target):
						break
				next_dest = dest[0] + dx, dest[1] + dy
				if not world.can_actor_enter(target, next_dest):
					break
				dist += 1
				dest = next_dest
			tdx = dx * dist
			tdy = dy * dist
		else:
			tdx, tdy = dx, dy

		mo = Compass.direction_for_id(actor.orient)
		push = AnimationList([MoveAnimation(actor, dx, dy, frames=90),
				AnimationSequence([Pause(20), MoveAnimation(target, tdx, tdy, 60 * dist, interpolation=linear_interpolation)])
			])
		if mo != self.direction:
			scene.add_animation(AnimationSequence([TurnAnimation(actor, self.direction), push]))
		else:
			scene.add_animation(push)


class PumpAction(Action):
	class Assets:
		anims = {
			'pump-up-water': 'actions/pump-up-water',
			'pump-down-water': 'actions/pump-down-water',
			'pump-up-sea-water': 'actions/pump-up-sea-water',
			'pump-down-sea-water': 'actions/pump-down-sea-water',
			'pump-up-milk': 'actions/pump-up-milk',
			'pump-down-milk': 'actions/pump-down-milk'
		}

	ARROW_OFF = 1

	def __init__(self, direction, actor, target):
		"""Target can be a tile or an object, so long as it provides the
		right interface."""

		self.direction = direction
		self.target = target

		if actor.get_fill():
			self.anim = self.anims['pump-down-' + actor.get_fill()].new(framedelay=4, start_paused=True)
		else:
			self.anim = self.anims['pump-up-' + target.fluid_available(direction.opposite())].new(framedelay=4, start_paused=True)

		x, y = actor.pos
		dx, dy = direction.vector
		self.dest = x + dx, y + dy

		super(PumpAction, self).__init__(self.dest[0], self.dest[1], actor=actor)
		if isinstance(target, Tile):
			self.alt = actor.alt + 0.5
		else:
			self.alt = target.alt + 1

	def tooltip(self):
		afill = self.actor.get_fill()
		if afill:
			return 'Empty ' + afill
		else:
			return 'Fill up with ' + self.target.fluid_available(self.direction.opposite())

	def play(self, name):
		if name == 'hover':
			self.anim.play()
		else:
			self.anim.pause()
			self.anim.go(0)

	def perform(self, actor, gamestate, scene):
		mo = Compass.direction_for_id(actor.orient)
		pump = PumpAnimation(actor, self.direction, self.target)
		opp = self.direction.opposite()
		if mo != opp:
			scene.add_animation(AnimationSequence([TurnAnimation(actor, opp), pump]))
		else:
			scene.add_animation(pump)


class FreezerAction(Action):
	class Assets:
		anims = {
			'pump-down-water': 'actions/pump-down-water'
		}

	def __init__(self, direction, actor, freezer):
		self.direction = direction

		self.anim = self.anims['pump-down-water'].new(framedelay=4, start_paused=True)
		self.freezer = freezer
	
		super(FreezerAction, self).__init__(freezer.pos[0], freezer.pos[1], actor=actor)
		self.alt = freezer.alt + 1

	def tooltip(self):
		return "Fill freezer"

	def play(self, name):
		if name == 'hover':
			self.anim.play()
		else:
			self.anim.pause()
			self.anim.go(0)

	def perform(self, actor, gamestate, scene):
		mo = Compass.direction_for_id(actor.orient)
		freeze = FreezerAnimation(actor, self.direction, self.freezer, scene.world)
		opp = self.direction.opposite()
		if mo != opp:
			scene.add_animation(AnimationSequence([TurnAnimation(actor, opp), freeze]))
		else:
			scene.add_animation(freeze)


class DownlinkAction(Action):
	class Assets:
		anims = {
			'downlink': 'actions/downlink'
		}

	ARROW_OFF = 1

	def __init__(self, actor, target):
		self.target = target
		x, y = target.pos

		super(DownlinkAction, self).__init__(x, y, actor=actor)
		self.alt = target.alt + 1.5

	def tooltip(self):
		return "Activate this downlink"

	def play(self, name):
		if name == 'hover':
			self.anim.play()
		else:
			self.anim = self.anims['downlink'].new(framedelay=4, start_paused=True)

	def perform(self, actor, gamestate, scene):
		if self.actor.triggering is not None:
			self.target.play('default')
		self.actor.triggering = self.target
		self.target.play('link')
