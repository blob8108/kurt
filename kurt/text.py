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

"""Experimental text parser for scripts.

The original parser used block plugin syntax, the same as the ``scratchblocks``
tag used on the Scratch Forums and Wiki. See:
http://wiki.scratch.mit.edu/wiki/Block_Plugin

This parser supports most of the block plugin syntax. Most notably, using < >
for boolean shaped blocks is not supported.

"""

from collections import OrderedDict

import kurt
import re

#-- Tokens --#


class Token(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.value)


class symbol(Token):
    lbp = 0


class literal(Token):

    def nud(self):
        return self.value


class number(Token):

    def __init__(self, value):
        value = float(value)

        if int(value) == value:
            value = int(value)

        self.value = value

    def nud(self):
        return self


class string(Token):
    lbp = 0

    def nud(self):
        return self


class color(Token):

    def nud(self):
        self.value = kurt.Color(self.value)

        return self


class lparen(Token):
    lbp = 0

    def nud(self):
        global token
        contents = expression()

        if isinstance(contents, rparen):  # empty brackets
            return

        if not isinstance(token, rparen):
            raise SyntaxError("Expected bracket to match %s" % self.value)

        token = next()

        return contents


class rparen(Token):
    lbp = 0

    def nud(self):
        return self


class newline(symbol):
    name = "EOL"
    lbp = 3

    def nud(self):
        return []

    def led(self, left):
        if isinstance(left, kurt.Block):
            left = [left]

        return left


class end_token(Token):
    name = "EOF"
    lbp = 0

    def __init__(self):
        self.value = None

    def __repr__(self):
        return "%s()" % self.__class__.__name__


#-- Identity Token --#

# block kinds:
# - infix
# - postfix ("_ sensor value")
# - insert transformations ("var", "list", "param", "{}")

def inline_blocks():
    for block in kurt.plugin.Kurt.blocks:
        if len(block.inserts) == 1 and block.inserts[0].shape == "inline":
            yield block


def all_the_blocks():
    for block in kurt.plugin.Kurt.blocks:
        done_text = set()

        for block in block.conversions:
            if block.text in done_text:
                continue

            yield block

            done_text.add(block.text)


def match_part(part, block_part):
    if isinstance(block_part, kurt.Insert):
        return (isinstance(part, (Token, kurt.Block, list)))
    else:
        return (block_part.strip() == part)


def blocks_starting_with(parts):
    suppress_blocks = set(suppress_block_names())

    for block in all_the_blocks():
        if len(parts) > len(block.parts):
            continue

        if (isinstance(block.parts[0], basestring)
                and block.parts[0].strip() in suppress_blocks):
            continue

        for (p, bp) in zip(parts, block.parts):
            if not match_part(p, bp):
                break
        else:
            yield block


def next_block_part(parts):
    for block in blocks_starting_with(parts):
        next_part = (block.parts[len(parts)]
                     if len(block.parts) > len(parts)
                     else None)

        if isinstance(next_part, basestring):
            next_part = next_part.strip()

        yield next_part


def blocks_by_parts(parts):
    for block in all_the_blocks():
        if len(parts) != len(block.parts):
            continue

        for (p, bp) in zip(parts, block.parts):
            if not match_part(p, bp):
                break
        else:
            yield block


def block_from_parts(parts):
    args = []
    for part in parts:
        if isinstance(part, (Token, kurt.Block, list)):
            args.append(part)

    failure = ""
    for block in blocks_by_parts(parts):
        block_args = []
        for (arg, insert) in zip(args, block.inserts):
            if isinstance(arg, Token):
                if (isinstance(arg, iden) and
                        not insert.shape in ("number-menu", "readonly-menu")):
                    arg = kurt.Block(arg.value)
                elif (isinstance(arg, iden) and
                        insert.shape in ("number-menu", "readonly-menu") and
                        arg not in insert.options()):
                    try:
                        arg = kurt.Block(arg.value)
                    except kurt.UnknownBlock:
                        arg = arg.value
                else:
                    arg = arg.value
            elif (isinstance(arg, kurt.Block) and
                    arg.type.text in insert.options(context)):
                arg = arg.type.text

            ok = False
            if insert.shape == "string" or insert.kind == "broadcast":
                if isinstance(arg, (int, long, float, complex, str)):
                    arg = unicode(arg)
                ok = isinstance(arg, (unicode, kurt.Block))
            elif insert.shape == "color":
                ok = isinstance(arg, kurt.Color)
            elif insert.shape == "boolean":
                ok = arg is None or (isinstance(arg, kurt.Block)
                                     and arg.type.shape == "boolean")
            elif insert.shape == "stack":
                ok = isinstance(arg, list)
            elif insert.shape in ("number", "number-menu", "readonly-menu"):
                if insert.shape in ("number", "number-menu"):
                    if isinstance(arg, basestring):
                        try:
                            arg = float(arg)
                            arg = int(arg) if int(arg) == arg else arg
                        except ValueError:
                            pass

                    if isinstance(arg, (int, long, float, complex,
                                        kurt.Block)):
                        ok = True

                if insert.shape in ("readonly-menu", "number-menu"):
                    if (str(arg) in insert.options(context)
                            or isinstance(arg, kurt.Block)):
                        ok = True

            if not ok:
                failure = "%r doesn't fit %s" % (arg, insert.shape)

                if insert.kind:
                    failure += " " + insert.kind

                break
            block_args.append(arg)
        else:
            return kurt.Block(block, *block_args)
    else:
        throw("Wrong type of arguments to block: %s" % failure, repr(parts))


class iden(Token):

    @property
    def lbp(self):
        return PRECEDENCE.get(self.value, 100)

    def nud(self):
        try:
            return self.parse_block([self.value])
        except SyntaxError:
            for block in inline_blocks():
                if self.value in block.inserts[0].options(context):
                    return kurt.Block(block, self.value)

            if len(self.parts) == 1 and self.value in set(make_menu_tokens()):
                return iden(self.value)
            else:
                raise

    def led(self, left):
        if isinstance(left, list):
            return left + [self.parse_block([self.value])]
        else:
            return self.parse_block([left, self.value])

    def parse_block(self, parts):
        global token

        self.parts = parts

        while 1:
            part = self.parse_one_part(parts)
            if part is not None:
                if isinstance(part, rparen):
                    part = False
                parts.append(part)
            else:
                block = block_from_parts(parts)

                if isinstance(token, end_token):
                    return block

                if block.type.has_insert("stack"):
                    if not token.value == "end":
                        throw("Expected 'end' after C mouth")
                    token = next()

                return block

    def parse_one_part(self, parts):
        global token, next

        expect = set(next_block_part(parts))

        if not expect:
            self.parts = parts
            throw("Can't find block %r" % parts)

        if expect == set(['']):
            return ''

        all_inserts = filter(lambda p: isinstance(p, kurt.Insert), expect)

        if isinstance(token, iden):
            text_segments = filter(lambda p: isinstance(p, basestring), expect)
            menu_inserts = filter(lambda i: i.options(context), all_inserts)

            if token.value in text_segments:
                part = token.value
                token = next()

                return part

            for insert in menu_inserts:
                if token.value in insert.options(context):
                    part = token
                    token = next()

                    return part

        if None in expect:
            return None

        stack_inserts = filter(lambda i: i.shape == 'stack', all_inserts)
        if stack_inserts:
            if isinstance(token, end_token):
                part = []
            else:
                part = expression(1)

            assert isinstance(part, list)

            return part

        if isinstance(token, (newline, end_token)):
            throw("Unexpected EOL", expected=expect)

        if all_inserts:
            return expression(self.lbp)

        throw("Wrong argument", expected=expect)


#-- Tokenizer --#

PRECEDENCE = {
    "*": 130,
    "/": 130,
    "+": 120,
    "-": 120,
    "<": 110,
    "=": 110,
    ">": 110,
    "else": 0,
}

TOKENS = [(re.compile(r), cls) for (r, cls) in [
    (r'end', symbol),
    (r'(-?[0-9]+(\.[0-9]+)?)', number),
    (r'\[(#[A-Fa-f0-9]{3,6})\]', color),
    (r'\[([^\]]+?)( v)?\]', string),
    (r'\"([^"]+)\"', string),
    (r"\'([^']+)\'", string),
    (r'\(', lparen),
    (r'\)', rparen),
    #    (r'\<', lparen),
    #    (r'\>', rparen),
    (r'\n|\r|\r\n', newline),
]]

NEWLINE_PAT = re.compile(r'\n|\r|\r\n')
SEPARATOR_PAT = re.compile(r'[^A-Za-z:#%+*-,=<?>]')
WHITESPACE_PAT = re.compile(r'[ \t]+')

SEGMENT_ALIASES = {
    "when green flag clicked": "when @greenFlag clicked",
    "when gf clicked": "when @greenFlag clicked",
    "turn left": "turn @turnLeft",
    "turn right": "turn @turnRight",
    "turn ccw": "turn @turnRight",
    "turn cw": "turn @turnRight",
}


def make_block_tokens():
    for block in kurt.plugin.Kurt.blocks:
        for part in block.parts:
            if isinstance(part, basestring):
                yield part.strip()

    for alias in SEGMENT_ALIASES:
        yield alias


def make_menu_tokens():
    global context

    for kind in kurt.Insert.KIND_OPTIONS:
        if kind == "broadcast":
            continue

        for o in kurt.Insert(None, kind).options(context):
            yield str(o)


def suppress_block_names():
    for block in kurt.plugin.Kurt.blocks:
        if isinstance(block.parts[0], kurt.Insert):
            for o in block.parts[0].options(context):
                yield o


def tokenize(program):
    block_tokens = sorted(set(make_block_tokens()) | set(make_menu_tokens()))
    block_tokens.sort(key=len, reverse=True)
    block_tokens = filter(lambda x: not x.isdigit(), block_tokens)
    block_tokens = filter(None, block_tokens)

    global remain, lineno

    remain = program
    lineno = 1

    while remain:
        m = WHITESPACE_PAT.match(remain)
        if m:
            remain = remain[m.end():]
            if not remain:
                break

        for (pat, cls) in TOKENS:
            m = pat.match(remain)
            if m:
                if m.groups():
                    contents = m.group(1)
                else:
                    contents = m.group(0).strip()

                yield cls(contents)

                remain = remain[m.end():]

                if cls == newline:
                    lineno += 1

                break
        else:
            for value in block_tokens:
                if remain.startswith(value):
                    after_value = remain[len(value):]

                    if not after_value or SEPARATOR_PAT.match(after_value[0]):
                        value = SEGMENT_ALIASES.get(value, value)

                        yield iden(value)

                        remain = after_value

                        break
            else:
                throw("Unknown token at %r" % remain.split("\n")[0])

    yield end_token()


#-- Parser --#

p_input = ""


def expression(rbp=0):
    global token

    t = token
    token = next()
    left = t.nud()

    if not hasattr(token, "lbp"):
        throw("Not an operator: %r" % token)

    while rbp < token.lbp:
        t = token
        token = next()
        left = t.led(left)

        if not hasattr(token, "lbp"):
            throw("Not an operator: %r" % token)

    return left


def parse(program, scriptable):
    global token, next, context, p_input

    # for errors
    p_input = program

    context = scriptable
    next = tokenize(program).next
    token = next()
    result = expression()

    if not isinstance(token, end_token):
        throw("Expected end of input")

    if isinstance(result, kurt.Block):
        result = [result]

    if not isinstance(result, list):
        throw("Result does not evaluate to a block")

    return kurt.Script(result)


def throw(msg, hint=None, expected=None):
    global remain

    if expected:
        repr_expected = map(repr, expected)
        hint = "Expected %s" % (repr_expected[0] if len(repr_expected) == 1
                                else "one of " + ", ".join(repr_expected))

    if hint:
        msg += ". " + hint

    line = NEWLINE_PAT.split(p_input)[lineno - 1]
    offset = len(p_input) - len(remain)  # - len(token.value)
    err = SyntaxError(msg, ('<string>', lineno, offset, line))
    err.expected = expected

    raise err
