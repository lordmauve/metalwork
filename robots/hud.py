import math

import pygame
from pygame.rect import Rect

from robots.scene import load_sprite
from robots.graphics.styledrect import StyledRect

class MessageHUD(object):
	MESSAGE_DELAY = 200
	APPEAR_TIME = 15

	def __init__(self):
		self.sprites = {
			'dr': load_sprite('dr.png'),
			'bubble': load_sprite('bubble.png'),
		}
		self.message = ''
		self.message_queue = []
		self.dr_showing = False # if True, don't slide in the Dr.


		self.bubble = StyledRect(load_sprite('bubble.png'), 10)
		self.font = pygame.font.SysFont('bitsreamverasans,arial,system', 14)

	def tile(self, src, dest, srcrect, destrect):
		x, y, w, h = destrect
		r = x + w
		b = y + h
		while y < b:
			cx = x
			ch = min(b - y, srcrect.h)
			while cx < r:
				cliprect = Rect(srcrect.x, srcrect.y, min(r - cx, srcrect.w), ch)
				dest.blit(src, (cx, y), cliprect)
				cx += srcrect.w
			y += srcrect.h

	def show_messages(self, messages):
		self.show_message(messages[0])
		self.message_queue = messages[1:]

	def next_message(self):
		try:
			self.show_message(self.message_queue.pop(0))
		except IndexError:
			self.message = ''
			self.surfs = []
			self.dr_showing = False

	def show_message(self, message):
		self.message = message
		self.message_timer = 0
		self.surfs = [self.font.render(l, True, (50, 50, 50)) for l in message.split('\n')]

	def draw_bubble(self, screen, viewport, h, max_h):
		drw, drh = self.sprites['dr'].get_size()
		bubble = self.sprites['bubble']
		bw, bh = bubble.get_size()
		
		r = pygame.Rect(10 + drw, viewport.h - max_h/2 - h/2 - 5, viewport.w - drw - 15, h)
		self.bubble.draw(screen, r)

	def interp(self, start_frame, duration):
		return math.sin(math.pi/(2 * (duration)) * (self.message_timer - start_frame)) ** 2

	def draw(self, screen, viewport):
		if self.message:
			drw, drh = self.sprites['dr'].get_size()
			h = sum([surf.get_size()[1] for surf in self.surfs])
			h += 20
			if self.message_timer < self.APPEAR_TIME:
				if self.dr_showing:
					screen.blit(self.sprites['dr'], (5, viewport.h - drh - 5))
				else:
					screen.blit(self.sprites['dr'], ((self.interp(0, self.APPEAR_TIME) - 1) * drw + 5, viewport.h - drh - 5))
				self.draw_bubble(screen, viewport, h * self.interp(0, self.APPEAR_TIME) ** 2, h)
			elif self.message_timer < self.MESSAGE_DELAY + self.APPEAR_TIME:
				self.dr_showing = True
				screen.blit(self.sprites['dr'], (5, viewport.h - drh - 5))
				self.draw_bubble(screen, viewport, h, h)
				for i, s in enumerate(self.surfs):
					p = (20 + drw, viewport.h - h + 5 + i * self.font.get_linesize())
					screen.blit(s, p)
			else:
				if self.message_queue:
					screen.blit(self.sprites['dr'], (5, viewport.h - drh - 5))
				else:
					screen.blit(self.sprites['dr'], ((-self.interp(self.MESSAGE_DELAY + self.APPEAR_TIME, self.APPEAR_TIME)) * drw + 5, viewport.h - drh - 5))
				self.draw_bubble(screen, viewport, h * (1 - self.interp(self.MESSAGE_DELAY + self.APPEAR_TIME, self.APPEAR_TIME)), h)
			
				if self.message_timer == (self.MESSAGE_DELAY + 2 * self.APPEAR_TIME):
					self.next_message()

			self.message_timer += 1


class TooltipHUD(object):
	APPEAR_DELAY = 2
	RESET_DELAY = 1

	def __init__(self):
		self.font = pygame.font.SysFont('bitsreamverasans,arial,system', 10)
		self.bubble = StyledRect(load_sprite('hud/tooltip.png'), 13, 25)
		self.surf = None
		self.pos = None
		self.actor = None
		self.appear_timer = 0
		self.reset_timer = 0

	def show(self, message, pos):
		self.surf = self.font.render(message, True, (50, 50, 50))
		self.pos = pos
		self.start_timer()

	def show_for_actor(self, actor):
		message = actor.tooltip()
		if not message:
			return
		self.start_timer()
		self.surf = self.font.render(message, True, (50, 50, 50))
		self.actor = actor

	def is_showing(self):
		return self.surf is not None and pygame.time.get_ticks() - self.appear_timer > self.APPEAR_DELAY * 1000

	def start_timer(self):
		t = pygame.time.get_ticks()
		if not self.is_showing() and (t - self.reset_timer) > self.RESET_DELAY * 1000:
			self.appear_timer = t 
		else:
			self.appear_timer = 0

	def get_position(self, viewport):
		if self.pos:
			return self.pos
		bounds = viewport.screen_bounds(self.actor)
		return int(bounds.x + bounds.w * 0.5), int(bounds.y + bounds.h - 3)

	def hide(self):
		if self.is_showing():
			self.reset_timer = pygame.time.get_ticks()
		else:
			self.reset_timer = 0

		self.surf = None
		self.pos = None
		self.actor = None

	def draw(self, screen, viewport):
		if self.is_showing():
			x, y = self.get_position(viewport)
			tw, th = self.surf.get_size()
			r = Rect(x - 13, y, tw + 16, 26)
			self.bubble.draw(screen, r)
			screen.blit(self.surf, (x - 7, y + 10))
