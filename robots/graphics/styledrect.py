from pygame.rect import Rect

class StyledRect(object):
	def __init__(self, sprite, bw=10, bh=None):
		self.sprite = sprite
		self.bw = bw
		self.bh = bh

		self.src_pieces = self.split_rect(Rect((0, 0), sprite.get_size()), bw, bh)

	def split_rect(self, r, bw=10, bh=None):
		"""Splits a pygame rectangle r into 9 pieces such that
		- the corner pieces are bw x bh
		- the edge pieces are width bw or height bh
		- the interior is the rest"""

		if bh is None:
			bh = bw

		if r.w < 2 * bw:
			bw = r.w / 2
		if r.h < 2 * bh:
			bh = r.h / 2

		x2 = r.x + r.w - bw
		y2 = r.y + r.h - bh
		midh = r.h - 2 * bh
		midw = r.w - 2 * bw
		return [
			Rect(r.x, r.y, bw, bh),
			Rect(r.x + bw, r.y, midw, bh),
			Rect(x2, r.y, bw, bh),
			Rect(r.x, r.y + bh, bw, midh),
			Rect(r.x + bw, r.y + bh, midw, midh),
			Rect(x2, r.y + bh, bw, midh),
			Rect(r.x, y2, bw, bh),
			Rect(r.x + bw, y2, midw, bh),
			Rect(x2, y2, bw, bh),
		]

	def draw(self, screen, r):
		dest_pieces = self.split_rect(r, self.bw, self.bh)

		for i in range(9):
			screen.tile(self.sprite, self.src_pieces[i], dest_pieces[i])
