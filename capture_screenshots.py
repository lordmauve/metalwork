"""Capture the real Pygame renderer without a desktop.

Run: python capture_screenshots.py [output-directory]
The gallery distinguishes original levels, scripted gameplay and asset sheets.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import base64
import html
import json
import random
import sys
from pathlib import Path

import pygame
from robots.game import Game, GameState
from robots.actions import MoveAction, PushAction, PumpAction, FreezerAction, DownlinkAction
from robots.menusystem import LevelsMenu
from robots.robot_objects import Robot, TrackDozer, TankerRobot, HoverRobot, UplinkRobot
from robots.objects import Box, Car, Cow, Ice, Bucket, RubberRing, Freezer, Rig
from robots.tiles import DefaultTile, WaterTile, OceanTile, HoleTile, Tile
from robots.world import World, GraphicsLoader
from robots.worldloader import OBJECTS, WorldSaver, WorldLoader
from robots.scene import Scene
from robots.graphics.animation import AnimatedSprite
from editor import Editor

ROOT = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'screenshots'
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)
random.seed(42)
# Synthetic pointer input for deterministic headless editor selections.
pygame.mouse.get_pos = lambda: (400, 300)
entries = []


def frame(g, count=1):
    for _ in range(count):
        pygame.event.pump()
        g.gamestate.update()
        g.gamestate.draw(g.scenegraph)
        g.scenegraph.render()
        pygame.display.flip()


def save(g, name, title, note='', category='Gameplay'):
    frame(g)
    path = OUT / (name + '.png')
    pygame.image.save(g.screen, str(path))
    entries.append(dict(file=path.name, title=title, note=note, category=category))
    print(path.name, flush=True)


def game(level=None):
    g = Game(level)
    g.screen = pygame.display.set_mode((800, 600))
    g.scenegraph.screen = g.screen
    g.viewport.w, g.viewport.h = g.screen.get_size()
    if level:
        g.viewport.move_to((g.gamestate.scene.world.w-1)/2, (g.gamestate.scene.world.h-1)/2)
    return g


def clear_messages(g):
    g.gamestate.hud.message = ''
    g.gamestate.hud.message_queue = []


def actor(g, cls):
    return next(a for a in g.gamestate.scene.world.actors if isinstance(a, cls))


def activate(g, robot):
    g.gamestate.activate(robot)
    clear_messages(g)
    frame(g)


def perform(g, cls, dest=None, finish=True):
    state = g.gamestate
    action = next(a for a in state.actions if isinstance(a, cls) and (dest is None or getattr(a, 'dest', None) == dest))
    action.perform(state.active_robot, state, state.scene)
    if finish:
        settle(g)
    return action


def settle(g):
    for i in range(1500):
        frame(g)
        if not g.gamestate.scene.animation_playing():
            frame(g, 2)
            return
    raise AssertionError('Animation did not settle')


def staged(tiles, actors, w=4, h=3):
    g = game()
    world = World(w, h, [DefaultTile() for _ in range(w*h)], actors, {}, 'Feature capture')
    for pos, tile in tiles.items():
        world[pos] = tile
    scene = Scene(world, g.viewport)
    g.gamestate = GameState(g, scene, g.viewport)
    g.viewport.move_to((w-1)/2, (h-1)/2)
    frame(g)
    return g


# Menus and every saved level, untouched except camera framing.
g = game()
save(g, '01-main-menu', 'Main menu', category='Menus')
g.show_menu(LevelsMenu(g))
save(g, '02-level-menu', 'Level browser', category='Menus')
for p in sorted((ROOT / 'assets/levels').glob('*.xml')):
    g = game(p.name)
    frame(g, 25)
    save(g, 'level-' + p.stem, g.gamestate.scene.world.title,
         'Original saved level; 800 × 600 viewport for full-board framing.', 'Original levels')
    if p.name == 'level1.xml':
        clear_messages(g)
        save(g, '03-demo-board', 'Demo/testbed — all four specialised robots')
        g.ingame_menu()
        save(g, '04-pause-menu', 'Pause menu over the game', category='Menus')

# Box pushing, pressure button and lift, using actual offered actions.
g = game('level1.xml')
r = actor(g, TrackDozer)
activate(g, r)
save(g, '05-dozer-actions', 'Dozer — movement and push actions')
perform(g, PushAction, (1, 2), finish=False)
frame(g, 55)
save(g, '06-box-push', 'Pushing the box — animation in progress')
settle(g)
assert actor(g, Box).pos == (1, 1)
assert g.gamestate.scene.world[1, 1].triggered
save(g, '07-button-lift', 'Box on the button — lift raised')

# Amphibious robot crossing water.
g = game('level1.xml')
activate(g, actor(g, HoverRobot))
save(g, '08-hover-actions', 'Hover robot — water crossing available')
# Uplink robot reaches the link tile and triggers the remote downlink.
g = game('level1.xml')
activate(g, actor(g, UplinkRobot))
perform(g, MoveAction, (5, 3))
save(g, '10-uplink-actions', 'Uplink robot — remote activation available')
perform(g, DownlinkAction)
assert actor(g, UplinkRobot).triggering is not None
save(g, '11-downlink-triggered', 'Downlink activated — remote lift lowered')

# Water collection, freezing, automatic ejection and sliding ice.
g = game('tankertest.xml')
r = actor(g, TankerRobot)
activate(g, r)
perform(g, MoveAction, (2, 0))
save(g, '12-pump-water-action', 'Tanker — collect water')
perform(g, PumpAction)
assert r.get_fill() == 'water'
save(g, '13-tanker-filled', 'Tanker filled with water — blue gauge')
perform(g, MoveAction, (2, 1))
save(g, '14-freezer-action', 'Tanker — fill the freezer')
perform(g, FreezerAction, finish=False)
frame(g, 90)
save(g, '15-freezing', 'Freezer cycle — animation in progress')
settle(g)
assert any(isinstance(a, Ice) for a in g.gamestate.scene.world.actors)
save(g, '16-ice-ejected', 'Freezer automatically ejects an ice cube')
activate(g, actor(g, TrackDozer))
perform(g, PushAction, (1, 2), finish=False)
frame(g, 90)
save(g, '17-ice-sliding', 'Ice slides across several tiles')
settle(g)
assert isinstance(g.gamestate.scene.world[3, 2].filled, Ice)
save(g, '18-ice-hole', 'Ice fills the hole')

# Features present in code but absent or awkwardly placed in saved levels.
g = staged({(1, 1): WaterTile()}, [HoverRobot(0, 1)])
activate(g, actor(g, HoverRobot))
perform(g, MoveAction, (1, 1))
save(g, '19-hover-crossing', 'Hover robot crosses water', 'Staged board using existing objects and actions.')
for fluid, tile, source in [('sea-water', OceanTile(), None), ('milk', DefaultTile(), Cow(1, 1))]:
    actors = [TankerRobot(2, 1)] + ([source] if source else [])
    g = staged({(1, 1): tile}, actors)
    r = actor(g, TankerRobot)
    activate(g, r)
    save(g, '20-' + fluid + '-action', 'Tanker — collect ' + fluid,
         'Staged board using the existing fluid system.')
    perform(g, PumpAction)
    assert r.get_fill() == fluid
    save(g, '21-' + fluid + '-filled', 'Tanker filled with ' + fluid,
         'Staged board; existing gauge and source animations.')

# Filling and draining a hole through the same offered pump actions.
g = staged({(1, 1): HoleTile()}, [TankerRobot(2, 1)])
r = actor(g, TankerRobot)
r.set_fill('water')
activate(g, r)
save(g, '21-hole-fill-action', 'Tanker — fill a hole with water', 'Staged board with a prefilled tanker.')
perform(g, PumpAction)
assert g.gamestate.scene.world[1, 1].filled == 'water'
save(g, '21-hole-filled', 'Hole filled with water', 'Staged board; existing fill and drain mechanic.')
perform(g, PumpAction)
assert r.get_fill() == 'water' and g.gamestate.scene.world[1, 1].filled is None
save(g, '21-hole-drained', 'Tanker drains the hole again', 'Staged board; existing fill and drain mechanic.')

for objcls in [Box, Ice, Bucket]:
    g = staged({(2, 1): WaterTile()}, [TrackDozer(0, 1, orient='E'), objcls(1, 1)], w=3)
    activate(g, actor(g, TrackDozer))
    perform(g, PushAction, (1, 1))
    assert g.gamestate.scene.world[2, 1].filled is not None
    save(g, '22-water-' + objcls.__name__.lower(), objcls.__name__ + ' in water',
         'Staged board; real push, drop and floating/sinking behaviour.')

g = game('cars.xml')
world = g.gamestate.scene.world
world.add(Car(2, 1, orient='E', colour='red'))
world.actors[-1].play(None)
activate(g, actor(g, TrackDozer))
save(g, '23-car-push-action', 'Car — push along its orientation', 'A car added to the original Car Test board.')
perform(g, PushAction, (2, 1))
save(g, '24-car-pushed', 'Car pushed along the road', 'A car added to the original Car Test board.')

g = game('rig.xml')
r = next(a for a in g.gamestate.scene.world.actors if isinstance(a, TrackDozer) and a.pos == (1, 0))
activate(g, r)
perform(g, PushAction, (1, 1))
r = next(a for a in g.gamestate.scene.world.actors if isinstance(a, TrackDozer) and a.pos == (0, 2))
activate(g, r)
perform(g, MoveAction, (1, 2))
assert r.alt == 1
save(g, '25-rig-bridge', 'Movable rig supports a robot above ground level')

# Level editor: actual toolbar, palettes, selection, altitude and rotation.
g = game('garden.xml')
g.toggle_editor()
h = g.gamestate.hud
frame(g)
save(g, '26-editor-tiles', 'Level editor — terrain palette', category='Editors')
h.select_robots()
save(g, '27-editor-robots', 'Level editor — robot palette', category='Editors')
h.select_objects()
save(g, '28-editor-objects', 'Level editor — object palette', category='Editors')
h.select_tiles()
h.prototype_tile.alt = 2
save(g, '29-editor-altitude', 'Level editor — raised terrain', category='Editors')
g.toggle_editor()
frame(g)
g.create_level()
save(g, '30-editor-new-level', 'Create a new level', category='Editors')

# Save/load smoke check on an editor-created level.
g.gamestate.save_level()
assert WorldLoader('user-levels/test.xml').get_world().w == 1

# Animation editor: actual native editor screen with its status and crosshairs.
for name in ['robot-base', 'robot-dozer', 'robot-hover', 'robot-tanker', 'robot-uplink']:
    e = Editor('robots/' + name + '.txt')
    e.anim.frame = 6
    e.draw()
    path = OUT / ('editor-' + name + '.png')
    pygame.image.save(e.screen, str(path))
    entries.append(dict(file=path.name, title='Animation editor — ' + name,
                        note='Original editor at 640 × 480, south-facing frame.', category='Editors'))

# Contact sheets use real engine draw methods, not replacement artwork.
pygame.display.set_mode((800, 600))
loader = GraphicsLoader()
font = pygame.font.SysFont('dejavusans', 14)
titlefont = pygame.font.SysFont('dejavusans', 25)


def sheet(name, title, items, draw, columns=4, cell=(200, 170), category='Rendered catalogues'):
    rows = (len(items) + columns - 1) // columns
    surf = pygame.Surface((columns*cell[0], rows*cell[1]+65))
    surf.fill((24, 27, 33))
    surf.blit(titlefont.render(title, True, (245, 245, 245)), (18, 18))
    for i, (label, item) in enumerate(items):
        x, y = (i % columns)*cell[0], 65+(i//columns)*cell[1]
        pygame.draw.rect(surf, (36, 40, 48), (x+5, y+5, cell[0]-10, cell[1]-10))
        rendered = pygame.Surface((600, 600), pygame.SRCALPHA)
        draw(rendered, item, 300, 300)
        bounds = rendered.get_bounding_rect()
        if bounds.width and bounds.height:
            art = rendered.subsurface(bounds)
            area = pygame.Rect(x+10, y+10, cell[0]-20, cell[1]-48)
            target = art.get_rect().fit(area)
            if target.size != art.get_size():
                art = pygame.transform.smoothscale(art, target.size)
            surf.blit(art, target)
        text = font.render(label, True, (220, 225, 230))
        surf.blit(text, (x+(cell[0]-text.get_width())//2, y+cell[1]-26))
    path = OUT / (name + '.png')
    pygame.image.save(surf, str(path))
    entries.append(dict(file=path.name, title=title, note='Contact sheet rendered from original assets.', category=category))


robots = []
objects = []
tiles = []
for name, (cls, attrs) in OBJECTS.items():
    loader.load(cls)
    if issubclass(cls, Robot):
        for direction in ['N', 'E', 'S', 'W']:
            a = cls(0, 0, orient=direction)
            a.play(None)
            robots.append((name + ' ' + direction, a))
    elif issubclass(cls, Tile):
        if name == 'EmptyTile':
            continue
        t = cls(alt=1)
        tiles.append((name, t))
    else:
        a = cls(0, 0)
        a.play(None)
        objects.append((name, a))
sheet('catalogue-robots', 'All five implemented robot types — four directions', robots,
      lambda s, a, x, y: a.draw(s, x, y), cell=(200, 145))
sheet('catalogue-objects', 'All registered objects and scenery', objects,
      lambda s, a, x, y: a.draw(s, x, y))
sheet('catalogue-terrain', 'All registered visible terrain types', tiles,
      lambda s, t, x, y: t.draw(s, x, y, 2, 2, 0, 0))
cars = []
for colour in Car.COLOURS:
    for direction in Car.ORIENTATIONS:
        a = Car(0, 0, colour=colour, orient=direction)
        a.play(None)
        cars.append((colour + ' / ' + direction, a))
sheet('catalogue-cars', 'Cars — all seven colours and both orientations', cars,
      lambda s, a, x, y: a.draw(s, x, y), columns=4, cell=(200, 145))

# Every animation definition, including dormant artwork, with every frame shown.
for p in sorted((ROOT / 'assets/anims').rglob('*.txt')):
    rel = p.relative_to(ROOT / 'assets/anims').as_posix()
    a = AnimatedSprite.load(rel)
    label = rel.removesuffix('.txt').replace('/', '-')
    sheet('animation-' + label, rel,
          [('Frame ' + str(i), (a, i)) for i in range(a.frames)],
          lambda s, item, x, y: item[0].draw(s, item[1], (x, y)),
          columns=4, cell=(200, 160), category='Animation archive')

# Every image file, including unused/dormant sprites, at original scale where possible.
images = sorted((ROOT / 'assets/images').rglob('*.png'))
for start in range(0, len(images), 24):
    group = images[start:start+24]
    def draw_image(s, p, x, y):
        a = pygame.image.load(str(p))
        if a.get_width() > 205 or a.get_height() > 110:
            a = pygame.transform.smoothscale(a, a.get_rect().fit((0, 0, 205, 110)).size)
        s.blit(a, (x-a.get_width()//2, y-a.get_height()))
    sheet('assets-%02d' % (start//24+1), 'Original image assets %d–%d' % (start+1, start+len(group)),
          [(p.relative_to(ROOT / 'assets/images').as_posix(), p) for p in group],
          draw_image, columns=4, cell=(240, 155), category='Complete asset archive')

(OUT / 'manifest.json').write_text(json.dumps(entries, indent=2))
intro = ('Screens captured directly from the restored Python/Pygame application. '
         'Original levels use an 800 × 600 viewport to include the full board. '
         'Staged feature boards are explicitly labelled. Contact sheets expose original '
         'art and animation frames; their presence does not imply a completed gameplay feature.')
parts = ['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Metalwork — screenshot archive</title>',
         '<style>body{font:16px system-ui;background:#15181e;color:#e5e8ed;margin:32px auto;max-width:1400px;padding:0 20px}'
         'h1{font-size:38px}h2{margin-top:48px}p{color:#adb6c4;line-height:1.6}'
         '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px}'
         'figure{margin:0;background:#242a34;padding:12px;border-radius:8px}img{width:100%;height:auto;display:block;background:#000}'
         'figcaption{font-weight:600;margin-top:12px}small{display:block;color:#aeb8c6;font-weight:400;line-height:1.5;margin-top:6px}'
         'a{color:#9ad2ff}nav a{display:inline-block;margin:6px 18px 6px 0}</style>',
         '<h1>Metalwork</h1><p>' + intro + '</p><nav>']
categories = list(dict.fromkeys(e['category'] for e in entries))
for i, cat in enumerate(categories):
    parts.append('<a href="#c%d">%s</a>' % (i, html.escape(cat)))
parts.append('</nav>')
for i, cat in enumerate(categories):
    parts.append('<h2 id="c%d">%s</h2><div class="grid">' % (i, html.escape(cat)))
    for e in entries:
        if e['category'] != cat:
            continue
        data = base64.b64encode((OUT / e['file']).read_bytes()).decode()
        parts.append('<figure><img loading="lazy" src="data:image/png;base64,%s" alt="%s"><figcaption>%s<small>%s</small></figcaption></figure>' %
                     (data, html.escape(e['title']), html.escape(e['title']), html.escape(e['note'])))
    parts.append('</div>')
(OUT / 'metalwork-gallery.html').write_text('\n'.join(parts))
print('CAPTURED', len(entries), 'screenshots and contact sheets')
