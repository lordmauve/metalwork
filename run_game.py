import sys
import os.path
import math

from robots.game import Game

if __name__ == '__main__':
	if len(sys.argv) > 1:
		game = Game(sys.argv[1])
	else:
		game = Game()

	game.run()
