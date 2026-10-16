from copy import copy

import pygame
from pygame.locals import *

from pygame.rect import Rect

from robots.graphics.styledrect import StyledRect

from robots.gamestate import BaseGameState

from robots.scene import load_sprite, ALT_INCREMENT
from robots.robot_objects import Robot
from robots import tiles
from .worldloader import OBJECTS


class HUDButton(object):
	def __init__(self, name, pos, sprite=None):
		if sprite is None:
			sprite = name
		self.sprite = load_sprite('hud/%s.png' % sprite) 
		self.name = name
		self.pos = pos

	def draw(self, scenegraph, pos):
		x, y = pos
		x += self.pos[0]
		y += self.pos[1]
		scenegraph.blit(self.sprite, (x, y))

	def bounds(self, pos):
		x, y = pos
		x += self.pos[0]
		y += self.pos[1]
		size = self.sprite.get_size()
		return Rect((x, y), size)


class LevelEditorHUD(object):
	def __init__(self, world):
		self.tile = None
		self.world = world

		self.tiles_list = []
		self.robots_list = []
		self.objects_list = []

		for t, params in list(OBJECTS.values()):
			if issubclass(t, Robot):
				self.robots_list.append(t)
			elif issubclass(t, tiles.Tile):
				self.tiles_list.append(t)
			else:
				self.objects_list.append(t)

		self.selected_tile = 0
		self.selected_object = 0
		self.selected_robot = 0
		self.prototype_tile = self.tiles_list[self.selected_tile]()
		self.prototype_object = None

		self.load_sprites()

	def load_sprites(self):
		SPRITES = [
			'tile-select',
			'tile-select-bottom',
			'tile-shadow',
		]
		BUTTONS = [
			('down-arrow', (5, 22)),
			('up-arrow', (5, -8)),
			('objects-button', (194, 0)),
			('robots-button', (228, -3)),
			('tiles-button', (275, 5)),
			('next-arrow', (136, 35)),
			('prev-arrow', (29, -29)),
			('rotate-anticlockwise', (28, 30)),
			('rotate-clockwise', (48, 30)),
		]

		self.toolbar = StyledRect(load_sprite('hud/toolbar.png'), 22)
		self.sprites = {}
		for s in SPRITES:
			self.sprites[s] = load_sprite('hud/%s.png' % s)
	
		self.buttons = []
		for bsprite, pos in BUTTONS:
			self.buttons.append(HUDButton(bsprite, pos))

		for tcls in self.tiles_list:
			self.world.load(tcls)

	def rotate_clockwise(self):
		if self.prototype_object:
			if hasattr(self.prototype_object, 'rotate_clockwise'):
				self.prototype_object.rotate_clockwise()
		elif hasattr(self.prototype_tile, 'rotate_clockwise'):
			self.prototype_tile.rotate_clockwise()

	def rotate_anticlockwise(self):
		if self.prototype_object:
			if hasattr(self.prototype_object, 'rotate_anticlockwise'):
				self.prototype_object.rotate_anticlockwise()
		elif hasattr(self.prototype_tile, 'rotate_anticlockwise'):
			self.prototype_tile.rotate_anticlockwise()

	def set_selected_tile(self, x, y, alt=0):
		self.tile = x, y, alt

	def get_selected_tile(self):
		return self.tile[:2]

	def set_prototype_tile(self, t):
		self.prototype_tile = t

	def jump_items(self, i):
		if self.prototype_object:
			if isinstance(self.prototype_object, Robot):
				self.selected_robot = (self.selected_robot + i) % len(self.robots_list)
				next = self.robots_list[self.selected_robot](0, 0, alt=self.prototype_tile.alt)
				self.set_prototype_object(next)
			else:
				self.selected_object = (self.selected_object + i) % len(self.objects_list)
				next = self.objects_list[self.selected_object](0, 0, alt=self.prototype_tile.alt)
				self.set_prototype_object(next)
		else:
			self.selected_tile = (self.selected_tile + i) % len(self.tiles_list)
			next = self.tiles_list[self.selected_tile](alt=self.prototype_tile.alt)
			self.prototype_tile = next

	def next(self):
		self.jump_items(1)

	def prev(self):
		self.jump_items(-1)

	def set_prototype_object(self, obj):
		self.prototype_object = obj
		if obj is None:
			return
		self.world.load(obj.__class__)
		obj.play(None)

	def select_robots(self):
		self.set_prototype_object(self.robots_list[self.selected_robot](0, 0, alt=self.prototype_tile.alt))

	def select_objects(self):
		self.set_prototype_object(self.objects_list[self.selected_object](0, 0, alt=self.prototype_tile.alt))

	def select_tiles(self):
		self.set_prototype_object(None)
	
	def draw(self, scenegraph, viewport):
		if self.tile is not None:
			pos = viewport.screen_pos(*self.get_selected_tile())
			x, y = pos
			alt = self.tile[2]
			scenegraph.draw_center(self.sprites['tile-select-bottom'], (x, y + ALT_INCREMENT))
			if alt > 0:
				scenegraph.draw_center(self.sprites['tile-select'], (x, y - alt * ALT_INCREMENT))
			else:
				scenegraph.draw_center(self.sprites['tile-select'], pos)

		toolbar_pos = (10, viewport.h - 60)
		self.toolbar.draw(scenegraph, Rect(toolbar_pos, (340, 44)))
		scenegraph.blit(self.sprites['tile-shadow'], (toolbar_pos[0] + 39, toolbar_pos[1] - 2))
	
		for b in self.buttons:
			if b.name == 'down-arrow' and self.prototype_tile.alt == 0:
				continue
			if b.name == 'rotate-clockwise':
				if self.prototype_object:
					if not hasattr(self.prototype_object, 'rotate_clockwise'):
						continue
				elif not hasattr(self.prototype_tile, 'rotate_clockwise'):
					continue
			elif b.name == 'rotate-anticlockwise':
				if self.prototype_object:
					if not hasattr(self.prototype_object, 'rotate_anticlockwise'):
						continue
				elif not hasattr(self.prototype_tile, 'rotate_anticlockwise'):
					continue
			b.draw(scenegraph, toolbar_pos)	

		tx, ty = toolbar_pos
		tx += 100
		ty += 15
		alt = self.prototype_tile.alt
		self.prototype_tile.draw(scenegraph, tx, ty - ALT_INCREMENT * alt, alt, alt, 0, 0)
		if self.prototype_object:
			self.prototype_object.draw(scenegraph, tx, ty - ALT_INCREMENT * alt)

		self.toolbar_pos = toolbar_pos

	def click(self, pos):
		for b in self.buttons:
			if b.bounds(self.toolbar_pos).collidepoint(pos):
				return b.name


class LevelEditorGameState(BaseGameState):
	KEY_BINDINGS = {
		pygame.K_e: 'toggle_editor',
		pygame.K_ESCAPE: 'ingame_menu',
		pygame.K_w: 'save_level',
	}

	def __init__(self, game, scene, viewport):
		self.set_cursor(self.NORMAL_CURSOR)

		self.game = game
		self.scene = scene
		self.viewport = viewport

		self.scene.animations = []
		self.scene.gamestate = self
		scene.world.restart()
		
		pygame.display.set_caption('Editing %s - Robots' % self.scene.world.title, 'Robots')

		self.hud = LevelEditorHUD(scene.world)

	def get_huds(self):
		return [self.hud]

	def toggle_editor(self):
		self.game.toggle_editor()

	def ingame_menu(self):
		self.game.ingame_menu()

	def click(self, pos):
		button_clicked = self.hud.click(pos)
		
		if button_clicked == 'next-arrow':
			self.hud.next()
		elif button_clicked == 'prev-arrow':
			self.hud.prev()
		elif button_clicked == 'up-arrow':
			self.hud.prototype_tile.alt += 1
		elif button_clicked == 'down-arrow':
			self.hud.prototype_tile.alt = max(0, self.hud.prototype_tile.alt - 1)
		elif button_clicked == 'objects-button':
			self.hud.select_objects()
		elif button_clicked == 'robots-button':
			self.hud.select_robots()
		elif button_clicked == 'tiles-button':
			self.hud.select_tiles()
		elif button_clicked == 'rotate-clockwise':
			self.hud.rotate_clockwise()
		elif button_clicked == 'rotate-anticlockwise':
			self.hud.rotate_anticlockwise()
		if not button_clicked:
			tx, ty = self.hud.get_selected_tile()
			world = self.scene.world
			if self.hud.prototype_object:
				tile = world.get(tx, ty)
				if tile.can_actor_enter(self.hud.prototype_object, 0):
					obj = copy(self.hud.prototype_object)
					if hasattr(obj, 'reroll'):
						obj.reroll()
					alt = world[tx, ty].alt
					obj.pos = tx, ty
					obj.alt = alt
					for occupying in world.get_objects((tx, ty), alt=alt):
						world.remove(occupying)
					world.add(obj)
					obj.play(None)
			else:
				tile = copy(self.hud.prototype_tile)
				tile.reroll()
				world[tx, ty] = tile
				self.scene.tilecache = None
				self.scene.viewport.translate_tiles(min(0, tx), min(0, ty))
	
	def onclick(self, actor, pos):
		pass

	def hoverable(self, actor):
		return False

	def onhover(self, actor):
		pass

	def onunhover(self, actor):
		pass

	def on_drag(self, draggesture):
		self.scene.viewport.translate(*draggesture.relative())
		self.set_cursor(self.DRAG_CURSOR)
		self.dragging = True

	def on_drag_end(self, draggesture):
		if self.scene.hovered:
			self.set_cursor(self.HOVER_CURSOR)
		else:
			self.set_cursor(self.NORMAL_CURSOR)
		self.dragging = False

	def update(self):
		pos = pygame.mouse.get_pos()
		tx, ty = self.scene.viewport.tile_for_pos(*pos)
		world = self.scene.world
		tile = world.get(tx, ty)
		alt = tile.alt
		self.hud.set_selected_tile(tx, ty, alt)

	def save_level(self):
		from robots.worldloader import WorldSaver
		ws = WorldSaver(self.scene.world)
		from pathlib import Path
		Path('user-levels').mkdir(exist_ok=True)
		ws.save('user-levels/test.xml')
