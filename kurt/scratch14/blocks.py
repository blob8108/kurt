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

"""Load blocks list by parsing blockspecs from Scratch's Squeak source code."""

import re

from construct import *

import kurt
from kurt.scratch14.fixed_objects import Symbol
from kurt.scratch14.blockspecs_src import *


#-- Squeak blockspecs parser --#

TOKENS = map(re.compile, [
    r"'()'",
    r"'(.*?[^\\])?'",
    r'#[~-]',
    r'#([A-Za-z+*/\\<>=&|~:-]+)',  # _=@%?!`^$
    r'(-?[0-9]+(\.[0-9]+)?)',
    r'\(',
    r'\)',
])


def tokenize(squeak_code):
    remain = str(squeak_code)
    while remain:
        remain = remain.lstrip()
        for pat in TOKENS:
            m = pat.match(remain)
            if m:
                if m.groups():
                    token = m.group(1)
                else:
                    token = m.group()
                token = token.replace("\\'", "'")
                yield token
                remain = remain[m.end():]
                break
        else:
            raise SyntaxError, "Unknown token at %r" % remain


def parse(squeak_code):
    tokens = tokenize(squeak_code)
    for token in tokens:
        if token == "(":
            blockspec = []
            token = tokens.next()
            while token != ")":
                token = token.replace("#-", "-")
                if token.lstrip("-").isdigit():
                    token = int(token)
                elif token.lstrip("-").replace(".", "").isdigit():
                    token = float(token)
                blockspec.append(token)
                token = tokens.next()
            yield blockspec
        elif token in ("#-", "#~"):
            yield None
        else:
            yield token


def make_blocks(squeak_code):
    category = None
    for thing in parse(squeak_code):
        if isinstance(thing, basestring):
            category = thing
            continue
        else:
            block = thing
            if block:
                (text, flag, command) = block[:3]
                block = blockify(category, text, flag, command, block[3:])
            yield block


#-- convert to kurt blocks --#

CATEGORIES = set([
    'motion',
    'looks',
    'sound',
    'pen',
    'control',
    'sensing',
    'operators',
    'variables',
    'list',
    'motor',

    'obsolete number blocks',
    'obsolete sound blocks',
    'obsolete sprite looks blocks',
    'obsolete sprite motion blocks',
    'obsolete image effects'
])

SHAPE_FLAGS = {
    '-': 'stack',
    'b': 'boolean',
    'c': 'stack',
    'r': 'reporter',
    'E': 'hat',
    'K': 'hat',
    'M': 'hat',
    'S': 'hat',
    's': 'stack',
    't': 'stack',  # timed blocks, all stack
}

INSERT_SHAPES = {
    '%b': 'boolean',
    '%n': 'number',
    '%d': 'number-menu',   # direction ( v)
    '%s': 'string',        # string [ ]
    '%c': 'color',         # color picker with menu [#hexcode]
    '%C': 'color',         # color [#hexcode]

    '%m': 'readonly-menu',  # morph reference [Sprite1 v]
    '%a': 'readonly-menu',  # attribute of sprite [x position v]
    '%e': 'readonly-menu',  # broadcast message [Play v]
    '%k': 'readonly-menu',  # key [space v]

    '%v': 'readonly-menu',  # variable [var v]
    '%L': 'readonly-menu',  # list name [list v]
    '%i': 'number-menu',   # item ( ) 1/last/any
    '%y': 'number-menu',   # delete line %y of list ( ) 1/last/all

    '%f': 'readonly-menu',  # math function [sqrt v]

    '%l': 'readonly-menu',  # costume name [Costume1 v]
    '%g': 'readonly-menu',  # graphic effect menu [ghost v]

    '%S': 'readonly-menu',  # sound selector [meow v]
    '%D': 'number-menu',   # MIDI drum (48 v)
    '%N': 'number-menu',   # MIDI note (60 v)
    '%I': 'number-menu',   # MIDI instrument (1 v)

    '%h': 'readonly-menu',  # Boolean sensor board selector menu
    '%H': 'readonly-menu',  # Numerical sensor board selector menu
    '%W': 'readonly-menu',  # motor direction
}

INSERT_KINDS = {
    '%d': 'direction',

    '%m': 'spriteOrMouse',  # most of the time
    '%a': 'attribute',
    '%e': 'broadcast',
    '%k': 'key',

    '%v': 'var',
    '%L': 'list',
    '%i': 'listItem',
    '%y': 'listDeleteItem',

    '%f': 'mathOp',

    '%l': 'costume',
    '%g': 'effect',

    '%S': 'sound',
    '%D': 'drum',
    '%N': 'note',
    '%I': 'instrument',

    '%h': 'booleanSensor',
    '%H': 'sensor',
    '%W': 'motorDirection',
}

IGNORE_COMMANDS = [
    'EventHatMorph',
    'MouseClickEventHatMorph',
]

OVERRIDE_DEFAULTS = {
    'KeyEventHatMorph': ['space'],
    'doIfElse': [False],
}

MATCH_COMMANDS = {
    'KeyEventHatMorph': 'whenKeyPressed',
    'drum:duration:elapsed:from:': 'playDrum',
    '\\\\': '%',  # modulo
    'midiInstrument:': 'instrument:',
    'nextBackground': 'nextScene',
    'showBackground:': 'startScene',
}

INSERT_RE = re.compile(r'(%.(?:\.[A-z]+)?)')


def blockify(category, text, flag, command, defaults):
    if command in IGNORE_COMMANDS:
        return

    shape = SHAPE_FLAGS[flag]
    if text in ('stop script', 'stop all', 'forever', 'forever if %b'):
        shape = 'cap'

    defaults = OVERRIDE_DEFAULTS.get(command, defaults)

    parts = []
    for part in filter(None, INSERT_RE.split(text)):
        if INSERT_RE.match(part):
            default = defaults.pop(0) if defaults else None
            if isinstance(default, Symbol):
                default = default.value
            kind = INSERT_KINDS.get(part)
            part = kurt.Insert(INSERT_SHAPES[part], kind, default=default)
        parts.append(part)

    match = MATCH_COMMANDS.get(command)

    # c & e blocks
    if command == "doIfElse":
        parts += [kurt.Insert("stack"), "else", kurt.Insert("stack")]
    elif flag == "c":
        parts += [kurt.Insert("stack")]

    pbt = kurt.PluginBlockType(category, shape, command, parts,
                               match=match)

    # fix insert kinds
    if command == 'getAttribute:of:':
        pbt.inserts[1].kind = 'spriteOrStage'
    elif command == 'touching:':
        pbt.inserts[0].kind = 'touching'
    elif command == 'showBackground:':
        pbt.inserts[0].kind = 'backdrop'

    # fix unevaluated inserts
    if pbt.text in ("wait until %s", "repeat until %s%s", "forever if %s%s"):
        pbt.inserts[0].unevaluated = True

    return pbt


#-- build lists --#

block_list = (list(make_blocks(squeak_blockspecs)) +
              list(make_blocks(squeak_stage_blockspecs)) +
              list(make_blocks(squeak_sprite_blockspecs)) +
              list(make_blocks(squeak_obsolete_blockspecs)))

block_list += [
    # variable reporters
    kurt.PluginBlockType('variables', 'reporter', 'readVariable',
                         [kurt.Insert('inline', 'var', default='var')]),
    kurt.PluginBlockType('variables', 'reporter', 'contentsOfList:',
                         [kurt.Insert('inline', 'list', default='list')]),

    # Blocks with different meaning depending on arguments are special-cased
    # inside load_block/save_block.
    kurt.PluginBlockType('control', 'hat', 'whenGreenFlag',
                         ['when green flag clicked']),
    kurt.PluginBlockType('control', 'hat', 'whenIReceive',
                         ['when I receive ', kurt.Insert('readonly-menu', 'broadcast')]),

    # changeVariable is special-cased (and isn't in blockspecs)
    kurt.PluginBlockType('variables', 'stack', 'changeVar:by:', ['change ',
                                                                 kurt.Insert('readonly-menu', 'var'), ' by ', kurt.Insert('number')]),
    kurt.PluginBlockType('variables', 'stack', 'setVar:to:', ['set ',
                                                              kurt.Insert('readonly-menu', 'var'), ' to ', kurt.Insert('string')]),

    # MouseClickEventHatMorph is special-cased as it has an extra argument:
    # 'when %m clicked'
    kurt.PluginBlockType('control', 'hat', 'whenClicked',
                         ['when clicked']),
]
