import sys
import os.path
import re
from io import StringIO

import pygame
from pygame.locals import *

from robots.graphics.animation import AnimatedSprite, ANIMATIONS_ROOT

class EditableAnimatedSprite(AnimatedSprite):
	def __init__(self, fname, layers=[], layer_names={}):
		super(EditableAnimatedSprite, self).__init__(layers, layer_names)
		self.fname = os.path.join(ANIMATIONS_ROOT, fname)
		self.currentlayer = 0
		self.frame = 0
		self.layer_name_reverse = dict([(l, name) for name, l in list(self.layer_names.items())])

	def change_frame(self, dr):
		self.frame = self.frame + dr

	def draw(self, screen, pos):
		super(EditableAnimatedSprite, self).draw(screen, self.frame, pos)

	def name_for_layer(self, id):
		try:
			return self.layer_name_reverse[id]
		except KeyError:
			return str(id)

	def translate(self, dx, dy):
		if self.currentlayer < 0:
			for l in self.layers:
				l.translate(self.frame, dx, dy)
		else:
			l = self.layers[self.currentlayer]
			l.translate(self.frame, dx, dy)

	def toggle_visibility(self):
		l = self.layers[self.currentlayer]
		i = self.frame % len(l.sprites)
		x, y, s = l.sprites[i]
		if s is None:
			l.sprites[i] = x, y, l.load_frame(i)
		else:
			l.sprites[i] = x, y, None

	@staticmethod
	def load(fname):
		a = AnimatedSprite.load(fname)
		a = EditableAnimatedSprite(fname, a.layers, a.layer_names)
		return a

	def save(self):
		f = StringIO()
		for i, l in enumerate(self.layers):
			print('base:', l.base, file=f)
			if i in self.layer_name_reverse:
				print('name:', self.layer_name_reverse[i], file=f)
			print('frames:', l.num_sprites, file=f)

			offs = []
			for x, y, s in l.sprites:
				if s is None:
					offs.append('-')
				else:
					offs.append('%d,%d' % (x, y))
			print('offsets:', ' '.join(offs), file=f)

			
			print(file=f)
		out = open(self.fname, 'w')
		out.write(f.getvalue())
		out.close()


class Status(object):
	def __init__(self, duration=5000):
		self.font = pygame.font.SysFont('bitsreamverasans,arial,system', 14)
		self.status = ''
		self.surf = None
		self.end_time = None
		self.duration = duration

	def set(self, status):
		if not status:
			self.clear()
		else:
			self.end_time = pygame.time.get_ticks() + self.duration
			self.status = status
			self.surf = self.font.render(self.status, True, (255, 255, 255))
	
	def clear(self):
		self.status = ''
		self.surf = None

	def draw(self, screen):
		if not self.surf:
			return
		if pygame.time.get_ticks() > self.end_time:
			self.clear()
		else:
			screen.blit(self.surf, (5, 5))


class Editor(object):
	def __init__(self, filename):
		pygame.init()
		self.screen = pygame.display.set_mode((640, 480))
		pygame.display.set_caption('Robots! Animation Editor')
		self.dirty = True
		self.status = Status()
		self.origin = 320, 300
		self.load(filename)

	def load(self, filename):
		self.anim = EditableAnimatedSprite.load(filename)
		self.filename = filename
		self.set_status("Loaded %s" % filename)

	def draw(self):
		ox, oy = self.origin
		w, h = self.screen.get_size()
		self.screen.fill((0,0,0))
		line_colour = (255, 255, 255)
		
		pygame.draw.line(self.screen, line_colour, (0, oy), (w, oy))
		pygame.draw.line(self.screen, line_colour, (ox, 0), (ox, h))
		self.anim.draw(self.screen, self.origin)
		self.status.draw(self.screen)
		pygame.display.update()
		self.dirty = False

	def translate(self, dx, dy):
		self.anim.translate(dx, dy)
		self.dirty = True

	def rotate(self, dr):
		self.anim.change_frame(dr)
		self.dirty = True

	def next_layer(self):
		clayer = (self.anim.currentlayer + 1) % len(self.anim.layers)
		self.anim.currentlayer = clayer 
		self.set_status('Editing sprite %s on layer %s' % (self.anim.layers[clayer].base, self.anim.name_for_layer(clayer)))

	def all_layers(self):
		self.anim.currentlayer = -1
		self.set_status('Editing all layers')

	def toggle_visibility(self):
		if self.anim.currentlayer < 0:
			self.set_status('Select a layer to toggle visibility')
		else:
			self.anim.toggle_visibility()
			self.dirty = True

	def set_status(self, status):
		self.status.set(status)
		self.dirty = True

	def run(self):
		while True:
			for event in pygame.event.get():
				if event.type in (QUIT,):
					sys.exit()
				if event.type == KEYDOWN:
					key = event.key
					if key == K_UP:
						self.translate(0, -1)
					elif key == K_DOWN:
						self.translate(0, 1)
					elif key == K_LEFT:
						self.translate(-1, 0)
					elif key == K_RIGHT:
						self.translate(1, 0)
					elif event.str == 'z':
						self.rotate(-1)
					elif event.str == 'x':
						self.rotate(1)
					elif key == K_TAB:
						self.next_layer()
					elif key == K_a:
						self.all_layers()
					elif key == K_SPACE:
						self.toggle_visibility()
					elif key == K_s and event.mod & KMOD_CTRL:
						self.anim.save()
						self.set_status('%s saved.' % self.filename)
				if event.type == MOUSEMOTION:
					if event.buttons == (1, 0, 0):
						self.translate(*event.rel)

			if self.dirty:
				self.draw()
			pygame.time.delay(30)


if __name__ == '__main__':
	if len(sys.argv) < 2:
		print("Usage: python editor.py <animation definition file>", file=sys.stderr)
	else:
		e = Editor(sys.argv[1])
		e.run()
