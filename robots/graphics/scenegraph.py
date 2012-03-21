import pygame
from pygame.rect import Rect

class SceneGraph(object):
	"""Base scenegraph that draws immediately. A subclass will be provided that optimises the
	scene to minimise drawing."""

	def __init__(self, screen):
		self.screen = screen

	def fill(self, color, rect=None, special_flags=0):
		self.screen.fill(color, rect, special_flags)

	def draw_center(self, sprite, pos):
		x, y = pos
		w, h = sprite.get_size()
		self.blit(sprite, (x - w/2, y - h/2))

	def blit(self, sprite, pos, cliprect=None):
		if cliprect is None:
			self.screen.blit(sprite, pos)
		else:
			self.screen.blit(sprite, pos, cliprect)

	def tile(self, src, srcrect, destrect):
		"""This is not a complete implementation of tiling - it doesn't clip in the y direction"""
		x, y, w, h = destrect
		r = x + w
		b = y + h
		while y < b:
			cx = x
			ch = min(b - y, srcrect.h)
			while cx < r:
				cliprect = pygame.Rect(srcrect.x, srcrect.y, min(r - cx, srcrect.w), ch)
				self.blit(src, (cx, y), cliprect)
				cx += srcrect.w
			y += srcrect.h

	def start(self, id):
		"""Start the rendering of this object"""

	def render(self):
		"""Complete rendering"""


OP_BLIT = 1
OP_BLIT_CLIPPED = 2
OP_FILL = 3

class OperationSet(object):
	def __init__(self):
		self.ops = []
		self.bounds_list = []
		self.hash = 0

	def __eq__(self, ano):
		e = hash(self) == hash(ano)
		if e:
			print "eq"
		else:
			print "ne"
		return e

	def simple_ops(self):
		ops = []

	def blit(self, sprite, pos):
		self.ops.append((OP_BLIT, sprite, pos))
		self.bounds_list.append(Rect(pos, sprite.get_size()))
		self.hash += hash((id(sprite), pos))

	def blit_clipped(self, sprite, pos, cliprect):
		self.ops.append((OP_BLIT_CLIPPED, sprite, pos, cliprect))
		self.bounds_list.append(Rect(pos, cliprect.size))
		self.hash += hash((id(sprite), pos, hash((cliprect.size, cliprect.w, cliprect.h))))

	def fill(self, color, rect, flags):
		self.ops.append((OP_FILL, color, rect, flags))
		self.bounds_list.append(rect)
		self.hash += hash((color, flags, hash((rect.size, rect.w, rect.h))))

	def bounds(self):
		try:
			return self._bounds
		except AttributeError:
			try:
				b = self.bounds_list.pop(0)
			except IndexError:
				b = Rect(0, 0, 0, 0)
			self._bounds = b.unionall(self.bounds_list)
			return self._bounds

	def play(self, screen):
		for o in self.ops:
			if o[0] == OP_BLIT:
				sprite, pos = o[1:]
				screen.blit(sprite, pos)
			elif o[0] == OP_BLIT_CLIPPED:
				sprite, pos, clip = o[1:]
				screen.blit(sprite, pos, clip)
			elif o[0] == OP_FILL:
				color, rect, flags = o[1:]
				if flags:
					pygame.draw.rect(screen, color, rect)
				else:
					screen.fill(color, rect, flags)


class OptimisingSceneGraph(SceneGraph):
	"""Scenegraph that computes dirty rectangles to minimise drawing."""

	def __init__(self, screen):
		self.screen = screen
		self.frame_ops = []
		self.next_frame()
	
	def next_frame(self):
		"""Stores the scenegraph"""
		self.last_frame_ops = self.frame_ops
		self.currentid = 0
		self.currentop = OperationSet()
		self.frame_ops = []

	def fill(self, color, rect=None, flags=0):
		if rect is None:
			rect = Rect((0, 0), self.screen.get_size())
		self.currentop.fill(color, rect, flags)

	def blit(self, sprite, pos, cliprect=None):
		if cliprect is None:
			self.currentop.blit(sprite, pos)
		else:
			self.currentop.blit_clipped(sprite, pos, cliprect)

	def tile(self, src, srcrect=None, destrect=None):
		if srcrect is None:
			srcrect = Rect((0, 0), src.get_size())
		if destrect is None:
			destrect = Rect((0, 0), self.screen.get_size())
		x, y, w, h = destrect
		r = x + w
		b = y + h
		while y < b:
			cx = x
			ch = min(b - y, srcrect.h)
			while cx < r:
				cliprect = Rect(srcrect.x, srcrect.y, min(r - cx, srcrect.w), ch)
				self.blit(src, (cx, y), cliprect)
				cx += srcrect.w
			y += srcrect.h

	def start(self, id):
		"""Start the rendering of this object"""
		self.frame_ops.append((self.currentid, self.currentop))
		self.currentid = id
		self.currentop = OperationSet()

	def build_rect_list(self, rs):
		"""rs is a list of potentially overlapping rects"""
		out = []
		for r in rs:
			overlaps = r.collidelistall(out)
			if overlaps:
				for i in overlaps:
					r = r.union(out[i])
					out[i] = None
				out = [outr for outr in out if outr is not None] + [r]
			else:
				out.append(r)
		return out

	def dirty_rects(self):
		rs = []

		lid_map = {}
		for lid, op in self.last_frame_ops:
			lid_map[op.hash] = op

		for cid, cop in self.frame_ops:
			h = cop.hash
			if h in lid_map:
				del(lid_map[h])
			else:
				rs.append(cop.bounds())

		for op in lid_map.values():
			rs.append(op.bounds())

		return self.build_rect_list(rs)

	def render(self):
		"""Complete rendering"""
		self.frame_ops.append((self.currentid, self.currentop))

		dirty_rects = self.dirty_rects()

		area = 0
		for r in dirty_rects:
			area += r.w * r.h
			self.screen.set_clip(r)

			for id, opset in self.frame_ops:
				if opset.bounds().colliderect(r):
					opset.play(self.screen)

#		print area

		self.screen.set_clip(None)

		for r in dirty_rects:
			pygame.draw.rect(self.screen, (255, 0, 0), r, 1)

		self.next_frame()
