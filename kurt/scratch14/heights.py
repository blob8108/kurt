# Copyright (C) 2012 Tim Radvan
#
# This file is part of Kurt.
#
# Kurt is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Kurt is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Kurt. If not, see <http://www.gnu.org/licenses/>.

"""Functions for calculating the height of a script."""

import os
import sys

# try and find kurt directory
path_to_file = os.path.join(os.getcwd(), __file__)
path_to_lib = os.path.split(os.path.split(path_to_file)[0])[0]
sys.path.insert(0, path_to_lib)
import kurt


def block_height(block):
    command = block.type.convert("scratch14").command

    FIXED = {
        'KeyEventHatMorph': 41,
        'whenGreenFlag': 43,
        'whenIReceive': 39,
        'whenClicked': 38,  # MouseClickEventHatMorph
        'stopAll': 22,
    }

    if command in FIXED:
        return FIXED[command]
    elif block.type.shape in ('reporter', 'boolean'):
        height = 17

        for arg in block.args:
            if isinstance(arg, kurt.Block):
                height = max(height, block_height(arg) + 3)

        if block.type.has_insert('readonly-menu'):
            height += 2
        elif block.type.has_insert('number') or \
                block.type.has_insert('string'):
            height += 1

        return height
    else:
        height = 24

        has_menu = False

        args = list(block.args)
        for insert in block.type.inserts:
            arg = args.pop(0) if args else None
            if isinstance(arg, kurt.Block):
                if block.type.has_insert('stack'):
                    d = 11
                else:
                    d = 10
                height = max(height, block_height(arg) + d)

            elif insert.shape == 'readonly-menu' and arg:
                has_menu = True

        if has_menu:
            height += 1

        if block.type.shape == 'cap':
            height -= 5

        if block.type.has_insert('stack'):
            done_one_mouth = False

            args = list(block.args)
            for insert in block.type.inserts:
                arg = args.pop(0) if args else []
                if insert.shape == 'stack':
                    height += 9
                    height += stack_height(arg) - 1 if arg else 14

                    if done_one_mouth:
                        height += 5
                    done_one_mouth = True

            if command in ('doForeverIf', 'doRepeat'):
                height += 1

        return height


def stack_height(blocks):
    return sum(map(block_height, blocks)) - (len(blocks) - 1) * 4


def clean_up(scripts):
    """Clean up the given list of scripts in-place so none of the scripts
    overlap.

    """
    scripts_with_pos = [s for s in scripts if s.pos]
    scripts_with_pos.sort(key=lambda s: (s.pos[1], s.pos[0]))
    scripts = scripts_with_pos + [s for s in scripts if not s.pos]

    y = 20
    for script in scripts:
        script.pos = (20, y)
        if isinstance(script, kurt.Script):
            y += stack_height(script.blocks)
        elif isinstance(script, kurt.Comment):
            y += 14
        y += 15
