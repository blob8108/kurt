#coding=utf8

# Copyright © 2012 Tim Radvan
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

"""Python library for reading/writing Scratch project (.sb) and sprite files.

DEPENDENCIES:
    construct - for defining the format. 
                Homepage: http://construct.wikispaces.com/
                ["construct" in the Python package index]

USAGE:
    You'll probably just want to use the provided ScratchProjectFile and 
    ScratchSpriteFile classes. Pass them the path to the file and use their 
    provided .save() methods. Access them using:
        from kurt.files import *
    
    Most of the objects you're interested in, like ScratchStageMorph and 
    ScratchSpriteMorph, inherit from UserObject. You can use .fields.keys() 
    to see the available fields on one of these objects.
    
    FixedObjects have a .value property to access their value. Inline objects, 
    such as int and bool, are converted to their Pythonic counterparts. Array 
    and Dictionary are converted to list and dict.
    
    Tested with Python 2.6. Works with Scratch 1.4; not tested with earlier 
    versions, but probably works.
    
    Scratch is created by the Lifelong Kindergarten Group at the MIT Media Lab. 
    See their website: http://scratch.mit.edu/
"""

from kurt.objtable import *
from kurt.files import *
from kurt.scripts import *
from kurt.scratchblocks import parse_scratchblocks, ParseError

__version__ = '1.2.2dev.bboe'
