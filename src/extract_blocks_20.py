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

"""Builds kurt/scratch20/commands_src.py.

Uses decompiled Scratch 2.0 SWF source from showmycode.com.

"""

import os


def relpath(path):
    return os.path.join(os.path.dirname(__file__), path)


# Strip weird chars
f = open(relpath("showmycode.com.txt"))
contents = f.read()
f.close()

contents = contents.replace("\r\n", "\n").replace("\xef\xbb\xbf", "")

f = open(relpath("showmycode.com.txt"), "w")
f.write(contents)
f.close()

# Split lines
lines = contents.split("\n")

out = "# Generated from Scratch SWF source by src/extract_blocks.py\n"


def add_line_at_index(list_name, i, comment=None):
    global out
    line = lines[i]
    out += "\n"

    # Comment with function definition
    if not comment:
        defun = "public static function"
        while i > 0 and not lines[i].lstrip().startswith(defun):
            i -= 1
        comment = lines[i].lstrip()
        comment = comment[len(defun):].strip().rstrip("{")
    out += "# %s\n" % comment

    # Strip array code
    line = line[line.index("["):]
    line = line.strip().rstrip(";")

    # Write commands array
    if "%s = [" % list_name in out:
        out += "%s += [\n" % list_name
    else:
        out += "%s = [\n" % list_name
    for cmd in eval(line):
        out += " %r,\n" % cmd
    out += "]\n"


for (i, line) in enumerate(lines):
    if "commands:Array" in line:
        add_line_at_index("commands", i, "commands:Array")
    if "_local1.blockSpecs" in line:
        add_line_at_index("extras", i)

f = open(relpath("../kurt/scratch20/commands_src.py"), "w")
f.write(out)
f.close()
