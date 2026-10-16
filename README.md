# Metalwork — capture-focused Python 3 restoration

This restores the original Python 2/Pygame prototype sufficiently to run its
saved levels, editors and a reproducible screenshot tour. It preserves the
original artwork and gameplay code. It is not a completed game or a full bug-fix
pass.

## Run

From this directory, with Python 3.12:

```sh
python -m pip install -r requirements.txt
python run_game.py
python run_game.py level1.xml
python editor.py robots/robot-tanker.txt
```

Click robots and then their displayed actions. Drag to pan. Press **E** to toggle
the level editor and **Escape** for the pause menu. The level editor's original
**W** shortcut saves to `user-levels/test.xml`. In the animation editor, arrows
move a layer, Z/X change frame, Tab changes layer, A selects all layers, Space
toggles layer visibility, and Ctrl+S saves the animation definition.

## Reproduce the screenshots

```sh
python capture_screenshots.py
```

The script uses Pygame's SDL dummy display and captures the application's actual
rendered surfaces. It generates PNGs, `manifest.json` and a self-contained
`metalwork-gallery.html`. Original saved levels are framed at 800 × 600;
animation-editor screenshots remain 640 × 480. No game art was redrawn.

The tour covers every saved level, menus, the level editor's three palettes,
the animation editor, robot movement, box pushing, buttons and lifts, uplink
activation, collecting water/sea water/milk, freezing and ejecting ice, sliding
ice into a hole, filling/draining a hole, floating/sinking objects, cars and the
movable rig. Additional boards are explicitly labelled as staged. The asset
archive includes unused and legacy artwork; this does not imply those features
are wired into gameplay.

## Restoration changes

* Python 3 syntax, relative imports, text/binary XML streams and metaclass syntax.
* Copy gameplay state without trying to pickle Pygame surfaces; retain shared
  animation definitions and independent playback state.
* Stable depth sorting without comparing unrelated Python objects.
* Suppress the original red dirty-rectangle debugging overlay.
* Fix palette switching back to terrain, loading new terrain classes and creating
  the level-save directory.
* Normalise legacy `filled="None"` and render water-filled holes.
* Accept the legacy `angles:` spelling in the old animation definition.
* Permit headless captures without attempting unsupported mouse cursors.

Validation: all seven levels and every registered editor palette item rendered;
scripted gameplay assertions pass; an editor-created level saves and reloads;
all 25 animation definitions and all original PNGs load. Python compilation and
`git diff --check` pass. Captures use synthetic input and scripted actions; this
does not constitute a complete interactive playthrough. Complex level-save
round trips and unfinished original behaviours have not been comprehensively
repaired.
