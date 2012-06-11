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

"""Block plugin formatter: reads all the scripts in a Scratch project file and
outputs [scratchblocks] formatted code for Scratch forums/wiki.

    Usage: python block_plugin.py [path/to/project_file.sb]
"""

# Known block plugin bugs:
# - <(var) < (var)> gt & lt are really weird inside and, or, not, etc.
#     if <<<(x) > [-1]> and <(y) > [-1]>> and <<(x) < [20]> and <(y) < [14]>>>
#
# - Can't have empty dropdowns eg. broadcast [ v]

import sys

try:
    import kurt
except ImportError: # try and find kurt directory
    import os
    path_to_file = os.path.join(os.getcwd(), __file__)
    path_to_lib = os.path.split(os.path.split(path_to_file)[0])[0]
    sys.path.append(path_to_lib)

from kurt.files import *
from kurt import ScratchSpriteMorph


def block_plugin_format(project):
    string = ""
    
    for sprite in project.stage.sprites:
        if not isinstance(sprite, ScratchSpriteMorph):
            continue
            
        string += "=" * 60 + "\n"        
        string += sprite.objName + "\n\n"
        
        scripts = sorted(sprite.scripts, key=lambda script: script.pos.y)
        for script in scripts:            
            string += script.to_block_plugin()
            #string += "=" * 40 + "\n"
            string += "\n\n"
        
        string += "\n\n"
    
    return string


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        print __doc__
        exit()
    
    project = ScratchProjectFile(path)
    print block_plugin_format(project)


