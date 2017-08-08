#!/usr/bin/env python
# -*- coding: utf-8 -*-

# commands:Array
commands_extra = [
    # manually added
    ['set %m.var to %s', ' ', 9, 'setVar:to:'],
    ['change %m.var by %n', ' ', 9, 'changeVar:by:'],
]

# extension:Array
extras = []

# robotics:ScratchExtension
extras += [
    # add extensions code if not auto-generated
    [' ', 'stop robot', 'Scratch2Robot/stop'],
    [' ', 'move robot %m.direction', 'Scratch2Robot/move', 'forward'],
    [' ', 'move robot %m.direction speed %n',
        'Scratch2Robot/move/speed', 'forward', 1],
    [' ', 'turn robot %m.turnDirection', 'Scratch2Robot/turn', 'left'],
    [' ', 'turn robot %m.turnDirection speed %n',
        'Scratch2Robot/turn/speed', 'left', 1],
    ['r', 'frontal laser distance', 'Scratch2Robot/laser/frontal']
]
