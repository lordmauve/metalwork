import os
import os.path
import re

from xml.sax.saxutils import unescape

import pygame
from pygame.rect import Rect

from robots.scene import load_sprite
from robots.game import BaseGameState

from robots.world import GraphicsLoader
from robots.robot_objects import TrackDozer


class Menu(object):
	"""A menu is a list of text strings of which one is selected.
	
	A menu manages the selection and can return a key corresponding to
	the item that is selected.

	Menus render their text strings to surfs on demand and cache them.
	"""

	ALIGN_RIGHT = 0
	ALIGN_LEFT = 1

	LINE_HEIGHT = 30
	SELECTED_COLOUR = (255, 255, 255)
	COLOUR = (128, 128, 128)

	def __init__(self, align):
		self.align = align
		self.items = []
		self.surfs = [] # the surfaces cache: None indicates an invalid surface
		self.font = None

		self.selected = 0

	def add_item(self, key, message):
		"""Add a menu item, which will appear as 'message' and will
		return 'key' when selected

		"""
		self.items.append((key, message))
		self.surfs.append(None)

	def add_space(self):
		"""Add a blank line to the menu"""
		self.items.append((None, None))
		self.surfs.append(None)

	def set_font(self, font):
		"""Sets the pygame font object to use to render the text"""
		if font != self.font:
			self.surfs = {}
		self.font = font

	def set_selected(self, sel):
		"""Sets the selected menu item"""
		# chuck out invalidated surfs
		if self.selected is not None:
			self.surfs[self.selected] = None
		self.surfs[sel] = None
		self.selected = sel

	def next(self):
		"""Select the next selectable menu item."""
		for i in range(1, len(self.items)):
			ik = (self.selected + i) % len(self.items)
			k, m = self.items[ik]
			if k:
				self.set_selected(ik)
				break

	def prev(self):
		"""Select the previous selectable menu item"""
		for i in range(1, len(self.items)):
			ik = (self.selected - i) % len(self.items)
			k, m = self.items[ik]
			if k:
				self.set_selected(ik)
				break

	def rebuild_surfs(self):
		"""Rebuilds any surfaces which are invalid."""
		for i, p in enumerate(self.items):
			key, message = p
			if self.surfs[i] or message is None:
				# if we already have a surf, skip
				continue

			if i == self.selected:
				colour = Menu.SELECTED_COLOUR
			else:
				colour = Menu.COLOUR
			surf = self.font.render(message, True, colour)
			self.surfs[i] = surf

	def hit_test(self, pos, x, y):
		y -= Menu.LINE_HEIGHT * len(self.items)
		self.rebuild_surfs()
		top = y
		for i in range(len(self.items)):
			key, message = self.items[i]
			surf = self.surfs[i]
			if surf:
				dims = surf.get_size()
				if self.align == Menu.ALIGN_RIGHT:
					r = Rect((x - dims[0], top), dims)
				else:
					r = Rect((x, top), dims)
				if r.collidepoint(pos):
					return i
			top += Menu.LINE_HEIGHT

	def draw(self, screen, x, y):
		"""Draws the menu to the screen at (x, y), where y is the top
		of the menu and text is aligned horizontally from x.

		"""
		y -= Menu.LINE_HEIGHT * len(self.items)
		self.rebuild_surfs()
		for i in range(len(self.items)):
			key, message = self.items[i]
			surf = self.surfs[i]
			if surf:
				if self.align == Menu.ALIGN_RIGHT:
					screen.blit(surf, (x - surf.get_width(), y + i * Menu.LINE_HEIGHT))
				else:
					screen.blit(surf, (x, y + i * Menu.LINE_HEIGHT))

	def get_selected_key(self):
		"""Returns the key of the currently selected menu item."""
		if self.selected is not None:
			return self.items[self.selected][0]


class MenuHUD(object):
	def __init__(self, menu):
		self.font = pygame.font.SysFont('bitsreamverasans,arial,system', 24)
		self.logo = load_sprite('metalwork.png')

		GraphicsLoader().load(TrackDozer)
		self.robot = TrackDozer(0, 0, alt=0, orient='S')
		self.robot.play(None)
		self.robot.set_active(True)
		self.set_menu(menu)

	def set_menu(self, menu):
		self.menu = menu
		self.menu.font = self.font

	def draw(self, screen, viewport):
		self.robot.draw(screen, 80, viewport.h - 50)
		screen.blit(self.logo, (110, viewport.h - 85))
		if self.menu:
			self.menu.draw(screen, viewport.w - 15, viewport.h - 150)

	def update_hover(self, pos, viewport):
		if self.menu:
			hit = self.menu.hit_test(pos, viewport.w - 15, viewport.h - 150)
			if hit is not None:
				self.menu.set_selected(hit)
				return self.menu.items[hit][0]
		

class RootMenu(Menu):
	def __init__(self, game):
		super(RootMenu, self).__init__(align=Menu.ALIGN_RIGHT)
		self.game = game

		self.add_item('start', 'start new game')
		self.add_item('load', 'load level')
		self.add_item('create', 'create a new level')
		self.add_space()
		self.add_item('exit', 'exit')

	def on_select(self, key):
		if key == 'start':
			self.game.play_level('level1.xml')
		elif key == 'load':
			self.game.show_menu(LevelsMenu(self.game))
		elif key == 'create':
			self.game.create_level()
		elif key == 'exit':
			self.game.quit()


class InGameMenu(Menu):
	def __init__(self, game):
		super(InGameMenu, self).__init__(align=Menu.ALIGN_RIGHT)
		self.game = game

		self.add_item('continue', 'continue')
		self.add_item('return', 'return to main menu')

	def on_select(self, key):
		if key == 'continue':
			self.game.gamestate = self.game.gamestate.above
		elif key == 'return':
			self.game.main_menu()


class LevelsMenu(Menu):
	def __init__(self, game):
		super(LevelsMenu, self).__init__(align=Menu.ALIGN_RIGHT)
		self.game = game
		for file, name in self.available_levels():
			self.add_item(file, name)

		self.add_space()
		self.add_item('return', 'return to main menu')

	def available_levels(self, path='assets/levels'):
		for f in os.listdir(path):
			if f.startswith('.') or not f.endswith('.xml'):
				continue
			ff = open(os.path.join(path, f), 'r').read()
			mo = re.search(r'<Title>(.*)</Title>', ff, re.DOTALL)
			if mo:
				name = unescape(mo.group(1))
			else:
				name = f
			yield f, name

	def on_select(self, key):
		if key.endswith('.xml'):
			self.game.play_level(key)
		elif key == 'return':
			self.game.main_menu()


class MenuSystemGameState(BaseGameState):
	KEY_BINDINGS = {
		pygame.K_RETURN: 'select_menu_item',
		pygame.K_UP: 'prev_menu_item',
		pygame.K_DOWN: 'next_menu_item',
	}
	def __init__(self, game, viewport, above=None, menu=None):
		self.game = game
		self.viewport = viewport
		self.above = above
		self.trans = load_sprite('menu_transparency.png')
		if menu is None:
			if above:
				menu = InGameMenu(game)
			else:
				pygame.display.set_caption('Robots', 'Robots')
				menu = RootMenu(game)
		self.menus = MenuHUD(menu)

	def show_menu(self, menu):
		self.menus.set_menu(menu)

	def get_huds(self):
		return [self.menus]

	def select_menu_item(self):
		item = self.menus.menu.get_selected_key()
		self.menus.menu.on_select(item)

	def prev_menu_item(self):
		self.menus.menu.prev()

	def next_menu_item(self):
		self.menus.menu.next()

	def draw(self, scenegraph):
		if self.above:
			self.above.draw(scenegraph)
			scenegraph.start(hash('overlay'))
			scenegraph.tile(self.trans)
		else:
			scenegraph.fill(0)
		super(MenuSystemGameState, self).draw(scenegraph)

	def update(self):
		"""Update the menu hover"""
		self.menus.update_hover(pygame.mouse.get_pos(), self.viewport)

	def click(self, pos):
		item = self.menus.update_hover(pos, self.viewport)
		if item:
			self.menus.menu.on_select(item)
