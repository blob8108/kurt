#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script for extracting block heights from Scratch 1.4.

Requires the following change to the Scratch source code:

	scriptsPane cleanUp.
	self saveScratchProjectNoDialog
Added to the end of Scratch-UI-Panes -> ScratchFrameMorph -> file read/write -> installNewProject:

"""

import os
import sys

import PIL

# try and find kurt directory
path_to_file = os.path.join(os.getcwd(), __file__)
path_to_lib = os.path.split(os.path.split(path_to_file)[0])[0]
sys.path.insert(0, path_to_lib)
import kurt

from heights import bheights


def measure_height(blocks):
    PATH = "tests/measure.sb"

    if isinstance(blocks, kurt.Block):
        blocks = [blocks]

    p = kurt.Project()
    #s = kurt.Sprite(p, "measure")
    #s.costume = kurt.Costume("b", kurt.Image(PIL.Image.new("RGB", (1, 1))))
    s = p.stage
    s.scripts.append(kurt.Script(blocks))
    s.scripts.append(kurt.Script([kurt.Block("say")]))
    # p.sprites.append(s)
    p.convert("scratch14")
    p.save(PATH)

    mtime = os.stat(PATH).st_mtime
    os.system("open %s" % PATH)

    while 1:
        try:
            if os.stat(PATH).st_mtime != mtime:
                break
        except OSError:
            pass

    cp = kurt.Project.load(PATH)
    #scripts = sorted(cp.sprites[0].scripts, key=lambda s: s.pos[1])
    scripts = sorted(cp.stage.scripts, key=lambda s: s.pos[1])
    (x1, y1) = scripts[0].pos
    (x2, y2) = scripts[1].pos
    height = y2 - y1 - 15

    return height


blacklist = set([
    'setSizeTo:',
    'penColor:',
    'touchingColor:',
    'color:sees:',
])


# for bt in kurt.plugin.Kurt.blocks:
#    if "scratch14" in bt.conversions:
#        command = bt.convert("scratch14").command
#        if command in bheights or command in blacklist:
#            continue
#        print repr(command)+":",
#        height = measure_height(kurt.Block(bt))
#        height = int(height)
#        bheights[command] = height
#        print repr(height)+","
