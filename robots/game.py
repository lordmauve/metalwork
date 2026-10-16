#coding: utf8
import sys
import pygame
from pygame.locals import *

from .actions import *
from .scene import *
from .robot_objects import *
from .objects import *
from .tiles import *

from .compass import *

from .world import World
from .worldloader import *
from robots.graphics.scenegraph import OptimisingSceneGraph
from robots.hud import *

from robots.gamestate import BaseGameState
from robots.menusystem import MenuSystemGameState



LEVEL_START_PHRASES = '__start__'

class GameState(BaseGameState):
	KEY_BINDINGS = {
		pygame.K_e: 'toggle_editor',
		pygame.K_ESCAPE: 'ingame_menu',
	}

	def __init__(self, game, scene, viewport):
		self.set_cursor(self.NORMAL_CURSOR)

		self.autoscroll = True # slide the display on drag, rather than dragging the world
		self.dragging = False
		self.game = game
		self.scene = scene
		self.viewport = viewport
		self.scene.world.save_state()
		
		pygame.display.set_caption(self.scene.world.title + ' - Robots', 'Robots')
		self.scene.gamestate = self

		self.active_robot = None
		self.actions = None
		self.triggered = {}
		self.hud = MessageHUD()
		self.tooltips = TooltipHUD()

		self.robots = []
		for a in self.scene.world.actors:
			if isinstance(a, Robot):
				self.robots.append(a) 

		self.play_phrase(LEVEL_START_PHRASES, warn_if_missing=False)

	def show_robot_actions(self, robot):
		self.hide_actions()

		x, y = robot.position()

		actions = []
		for dir in Compass.directions:
			action = MoveAction(dir, robot)
			try:
				dt = self.scene.world[action.dest]
			except IndexError:
				continue

			rel_alt = robot.alt - dt.alt
			occupying = self.scene.world.get_objects_above(action.dest, alt=robot.alt)

			if rel_alt == 0 and not occupying and isinstance(robot, TankerRobot):
				if robot.is_empty():
					try:
						if dt.fluid_available(dir.opposite()):
							actions.append(PumpAction(dir, robot, dt))
					except AttributeError:
						pass
				else:
					try:
						if dt.accepts_fluid(robot.get_fill(), dir.opposite()):
							actions.append(PumpAction(dir, robot, dt))
					except AttributeError:
						pass

			if not self.scene.world.can_actor_enter(robot, action.dest, check_empty=False):
				continue	
			if len(occupying) == 1:
				occupying = occupying[0]
				if isinstance(robot, Dozer) and occupying.is_pushable(dir):
					action = PushAction(dir, robot, occupying)
					if self.scene.world.can_actor_enter(occupying, action.target_dest):
						actions.append(action)
				elif isinstance(robot, TankerRobot):
					if hasattr(occupying, 'accepts_fluid') and occupying.accepts_fluid(robot.get_fill(), dir.opposite()):
						if isinstance(occupying, Freezer):
							actions.append(FreezerAction(dir, robot, occupying))
						else:
							actions.append(PumpAction(dir, robot, occupying))
					elif robot.is_empty() and hasattr(occupying, 'fluid_available') and occupying.fluid_available(dir.opposite()):
						actions.append(PumpAction(dir, robot, occupying))
				continue

			actions.append(action)

		if isinstance(robot, UplinkRobot):
			downlinks = self.scene.world.get_actors_by_class(Downlink)
			for d in downlinks:
				if robot.can_trigger(d):
					actions.append(DownlinkAction(robot, d))
		
		for a in actions:
			self.scene.add(a)
		self.actions = actions

	def hide_actions(self):
		if self.actions:
			for a in self.actions:
				self.scene.remove(a)
			self.actions = None

	def get_huds(self):
		return [self.hud, self.tooltips]

	def play_phrase(self, id, warn_if_missing=True):
		try:
			phrase = self.scene.world.phrases[id]
		except KeyError:
			if warn_if_missing:
				print("No such phrase '%s'" % id, file=sys.stderr)
		else:
			self.hud.show_messages(phrase)
	
	def click(self, pos):
		self.scene.onclick(pos)

	def onclick(self, actor, pos):
		if isinstance(actor, Robot):
			self.on_robot_click(actor, pos)
			return True
		elif isinstance(actor, Action):
			actor.perform(self.active_robot, self, self.scene)
			return True
		elif actor.description:
			self.play_phrase(actor.description)
			actor.description = None
			return True

	def toggle_editor(self):
		self.game.toggle_editor()

	def ingame_menu(self):
		self.game.ingame_menu()

	def activate(self, robot):
		self.active_robot = robot
		if robot.description:
			self.play_phrase(robot.description)
		robot.set_active(True)
		for r in self.robots:
			if r != robot:
				r.set_active(False)
		self.show_robot_actions(robot)

	def clickable(self, actor):
		return isinstance(actor, Action) or (isinstance(actor, Robot) and not actor.is_active())

	def onhover(self, actor):
		self.tooltips.show_for_actor(actor)
		if isinstance(actor, Action):
			actor.play('hover')
		if self.clickable(actor):
			self.set_cursor(self.HOVER_CURSOR)
		return True

	def onunhover(self, actor):
		if isinstance(actor, Action):
			actor.play(None)
		if self.tooltips.actor == actor:
			self.tooltips.hide()
			self.set_cursor(self.NORMAL_CURSOR)

	def on_robot_click(self, robot, pos):
		if not robot.is_active():
			self.activate(robot)

	def on_drag(self, draggesture):
		if not self.autoscroll:
			self.scene.viewport.translate(*draggesture.relative())
		self.set_cursor(self.DRAG_CURSOR)
		self.dragging = draggesture

	def on_drag_end(self, draggesture):
		if self.scene.hovered:
			self.set_cursor(self.HOVER_CURSOR)
		else:
			self.set_cursor(self.NORMAL_CURSOR)
		self.dragging = False

	def update(self):
		if self.dragging and self.autoscroll:
			x, y = self.dragging.absolute()
			SCROLL_RATE = 0.05
			self.scene.viewport.translate(x * SCROLL_RATE, y * SCROLL_RATE)
		self.scene.update()

		if self.scene.animation_playing():
			self.hide_actions()
		else:
			self.scene.world.update(self.scene, self.hud) # only update the world if we don't have animations to play

			if self.actions is None and self.active_robot and not self.scene.animation_playing():
				self.show_robot_actions(self.active_robot)

		if not self.dragging:
			self.scene.update_hover(pygame.mouse.get_pos())


class DragGesture(object):
	DRAG_THRESHOLD = 16	# The minimum movement required to be considered a drag: 4px ^ 2

	def __init__(self, pos):
		self.initial = pos
		self.current = pos
		self.triggered = False
		self.rel = (0, 0)

	def update(self, event):
		self.current = event.pos
		if not self:
			# if we're still not a valid drag, accumulate the relative drag
			self.rel = self.absolute()
		else:
			self.rel = event.rel
			

	def absolute(self):
		return self.current[0] - self.initial[0], self.current[1] - self.initial[1]

	def relative(self):
		return self.rel

	def __bool__(self):
		"""Returns True if this gesture is large enough to be considered
		as a drag movement.
		"""
		if self.triggered:
			return True
		dvx, dvy = self.absolute()
		self.triggered = dvx ** 2 + dvy ** 2 > self.DRAG_THRESHOLD
		return self.triggered
		

		
class Game(object):
	"""Initialises and de-initialises the game engine, delegating to a gamestate
	for most of the activity.

	Gamestates can be swapped out to change the mode of interaction.

	"""

	def __init__(self, level=None):
		"""Initialise the game and display, load the root menu."""
		pygame.init()
		pygame.display.set_icon(pygame.image.load('assets/images/robots-icon.png'))
		self.screen = pygame.display.set_mode((640, 480))
		self.viewport = Viewport()
		pygame.display.set_caption('Robots')
		self.scenegraph = OptimisingSceneGraph(self.screen)
		if level:
			self.play_level(level)
		else:
			self.main_menu()

	def play_level(self, level):
		"""Start a new gamestate for playing the given level."""
		scene = Scene(WorldLoader('assets/levels/' + level).get_world(), self.viewport)
		self.gamestate = GameState(self, scene, self.viewport)

	def create_level(self):
		from robots.level_editor import LevelEditorGameState
		scene = Scene(World.create_blank(), self.viewport)
		self.gamestate = LevelEditorGameState(self, scene, self.viewport)

	def show_menu(self, menu):
		if isinstance(self.gamestate, MenuSystemGameState):
			self.gamestate.show_menu(menu)
		else:
			self.gamestate = MenuSystemGameState(self, self.viewport, above=self.gamestate, menu=menu)

	def ingame_menu(self):
		"""Show the in-game menu."""
		self.gamestate = MenuSystemGameState(self, self.viewport, above=self.gamestate)

	def main_menu(self):
		"""Show the main menu."""
		self.gamestate = MenuSystemGameState(self, self.viewport)

	def toggle_editor(self):
		"""Swap in and out of the level editor."""
		from robots.level_editor import LevelEditorGameState
		self.gamestate.scene.remove_all()
		if isinstance(self.gamestate, LevelEditorGameState):
			self.gamestate = GameState(self, self.gamestate.scene, self.viewport)
		else:
			self.gamestate = LevelEditorGameState(self, self.gamestate.scene, self.viewport)
		self.gamestate.scene.tilecache = None

	def quit(self):
		"""Exit the game."""
		sys.exit()

	def run(self):
		"""The main game loop. This performs some high-level processing of input
		and then delegates to the gamestate for further processing."""

		drag = False
		dv = (0,0)
		clock = pygame.time.Clock()
		while True:
			for event in pygame.event.get():
				if event.type in (QUIT,):
					self.quit()
				if event.type == KEYDOWN:
					self.gamestate.onkey(event.key)
				if event.type == MOUSEBUTTONDOWN:
					drag = DragGesture(event.pos)
					dv = (0,0)
				if event.type == MOUSEBUTTONUP:
					if drag:
						self.gamestate.on_drag_end(drag)
					else:
						self.gamestate.click(event.pos)
					drag = None
				if event.type == MOUSEMOTION:
					if event.buttons == (1, 0, 0):
						drag.update(event)
						if drag:
							self.gamestate.on_drag(drag)

			self.gamestate.update()
			self.gamestate.draw(self.scenegraph)
			self.scenegraph.render()
			pygame.display.update()
			clock.tick(45) # lock framerate to 45fps
