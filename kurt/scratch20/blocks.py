#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import re

import kurt
from kurt.scratch20.commands_src import commands
from kurt.scratch20.commands_src_extras import commands_extra, extras


CATEGORY_IDS = {
    1:  "motion",
    2:  "looks",
    3:  "sound",
    4:  "pen",
    5:  "events",
    6:  "control",
    7:  "sensing",
    8:  "operators",
    9:  "variables",
    10: "more blocks",
    12: "list",
    20: "sensor",
    21: "wedo",
    30: "midi",
    91: "midi",
    98: "obsolete",  # --> we should use the 1.4 blockspecs for these instead
    99: "obsolete",  # scrolling

    # for stage?
    102: "looks",
    104: "pen",
    106: "control",
    107: "sensing",
}

SHAPE_FLAGS = {
    ' ':  'stack',
    'b':  'boolean',
    'c':  'stack',  # cblock
    'r':  'reporter',
    'e':  'stack',  # eblock
    'cf': 'cap',  # cblock
    'f':  'cap',
    'h':  'hat',
}

INSERT_SHAPES = {
    '%b': 'boolean',
    '%c': 'color',
    '%d': 'number-menu',
    '%m': 'readonly-menu',
    '%n': 'number',
    '%s': 'string',

    # special
    '%x': 'inline',
    '%Z': 'block',
}
SHAPE_INSERTS = dict(map(reversed, INSERT_SHAPES.items()))

INSERT_RE = re.compile(r'(%.(?:\.[A-z]+)?)')


def parse_spec(spec, defaults):
    for part in filter(None, INSERT_RE.split(spec)):
        if INSERT_RE.match(part):
            default = defaults.pop(0) if defaults else None
            part = kurt.Insert(INSERT_SHAPES[part[:2]], part[3:] or None,
                               default=default)

        yield part


def make_spec(parts):
    spec = ""
    for part in parts:
        if isinstance(part, kurt.Insert):
            insert = part
            part = SHAPE_INSERTS[insert.shape]

            if insert.kind:
                part += "." + insert.kind

        spec += part

    return spec


def blockify(blockspec):
    if len(blockspec) > 1:
        (spec, flag, category_id, command) = blockspec[:4]
        defaults = blockspec[4:]

        shape = SHAPE_FLAGS[flag]
        category = CATEGORY_IDS[category_id]

        parts = list(parse_spec(spec, defaults))

        if "c" in flag:
            parts += [kurt.Insert("stack")]
        elif "e" in flag:
            parts += [kurt.Insert("stack"), "else", kurt.Insert("stack")]

        pbt = kurt.PluginBlockType(category, shape, command, parts)
        if pbt.text in ("wait until %s", "repeat until %s%s",
                        "forever if %s%s"):
            pbt.inserts[0].unevaluated = True

        return pbt
    else:
        return None


def make_block_types():
    global commands

    # add extra general commands
    commands += commands_extra

    # add extras
    for block in extras:
        if len(block) > 1:
            (flag, spec, command) = block[:3]
            commands.append([spec, flag, 20, command] + block[3:])
        else:
            commands.append(block)

    # add not-actually-blocks
    commands += [
        ['%x.var', 'r', 9, 'readVariable', 'var'],
        ['%x.list', 'r', 12, "contentsOfList:", 'list'],
        ['%x', 'r', 10, 'getParam', 'param'],
        ['define %Z', 'h', 10, 'procDef'],
        ['%Z', ' ', 10, 'call'],
    ]

    # blockify
    return map(blockify, commands)


def custom_block(spec, input_names, defaults):
    input_names = list(input_names)
    parts = list(parse_spec(spec, defaults))

    for part in parts:
        if isinstance(part, kurt.Insert):
            part.name = input_names.pop(0)

    return kurt.CustomBlockType("stack", parts)
