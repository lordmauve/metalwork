class CompassDirection(object):
	def __init__(self, name, vector, frame):
		self.id = name[0]
		self.name = name
		self.vector = vector
		self.frame = frame

	def __str__(self):
		return self.id

	def __repr__(self):
		return 'Compass.%s' % self.name

	def opposite(self):
		return Compass.direction_for_frame((self.frame + 6) % 12)


class Compass(object):
	NORTH = CompassDirection('NORTH', (0, -1), 0)
	EAST = CompassDirection('EAST', (1, 0), 3)
	SOUTH = CompassDirection('SOUTH', (0, 1), 6)
	WEST = CompassDirection('WEST', (-1, 0), 9)

	directions = [NORTH, EAST, SOUTH, WEST]

	def __new__(cls, dict, base):
		raise NotImplementedError

	@staticmethod
	def direction_for_id(id):
		for d in Compass.directions:
			if d.id == id:
				return d
		raise KeyError('No such compass direction %s' % id)

	@staticmethod
	def direction_for_frame(frame):
		for d in Compass.directions:
			if d.frame == frame:
				return d
		raise KeyError('Frame %d does not correspond to a cardinal direction' % frame)
