import pygame
from robots.scene import Viewport

# Nicked from pyui
hand_strings = ( #sized 24x24
  "     XX                 ",
  "    X..X                ",
  "    X..X                ",
  "    X..X                ",
  "    X..X                ",
  "    X..XXX              ",
  "    X..X..XXX           ",
  "    X..X..X..XX         ",
  "    X..X..X..X.X        ",
  "XXX X..X..X..X..X       ",
  "X..XX........X..X       ",
  "X...X...........X       ",
  " X..X...........X       ",
  "  X.X...........X       ",
  "  X.............X       ",
  "   X............X       ",
  "   X...........X        ",
  "    X..........X        ",
  "    X..........X        ",
  "     X........X         ",
  "     X........X         ",
  "     XXXXXXXXXX         ",
  "                        ",
  "                        ",
)
hand = ((24,24),(5,0)) + pygame.cursors.compile(hand_strings,".","X")

class BaseGameState(object):
	NORMAL_CURSOR = pygame.cursors.arrow
	#HOVER_CURSOR = pygame.cursors.tri_left
	HOVER_CURSOR = hand
	DRAG_CURSOR = pygame.cursors.load_xbm('assets/cursors/move.xbm', 'assets/cursors/move-mask.xbm')

	def set_cursor(self, cursor):
		if pygame.display.get_driver() != 'dummy':
			pygame.mouse.set_cursor(*cursor)

	def onkey(self, key):
		try:
			binding = self.KEY_BINDINGS[key]
		except KeyError:
			return
		
		getattr(self, binding)()
		
	def get_huds(self):
		return []

	def draw(self, scenegraph):
		if hasattr(self, 'scene'):
			self.scene.draw(scenegraph)
		for h in self.get_huds():
			scenegraph.start(id(h))
			h.draw(scenegraph, self.viewport)

	def on_drag(self, draggesture):
		pass

	def on_drag_end(self, draggesture):
		pass

	def click(self, pos):
		pass
