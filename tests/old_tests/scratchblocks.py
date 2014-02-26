"""Currently broken. TODO: fix"""

from kurt import *
from kurt.scratchblocks.parser import math_functions

p = parse_scratchblocks

assert p("say (length of [hello])")[0].args[0].command == 'stringLength:' 
assert p("say (length of (var))")[0].args[0].command == 'stringLength:' 
assert p("say (length of [list v])")[0].args[0].command == 'lineCountOfList:'

assert p(u'[x position v] of [Sprite1]')[0].command == 'getAttribute:of:'
assert p(u'[x position v] of [Sprite1 v]')[0].command == 'getAttribute:of:'
assert p(u'[sqrt v] of (6)')[0].command == 'computeFunction:of:'
assert p(u'[sqrt v] of [6]')[0].command == 'computeFunction:of:'

assert p(u'[x position v] of (var)')[0].command == 'getAttribute:of:'
assert p(u'[sqrt v] of (var)')[0].command == 'computeFunction:of:'
for mf in math_functions:
    assert p(u'[%s v] of (var)' % mf)[0].command == 'computeFunction:of:'

assert p('set pen color to [#faa41a]')[0] == Block('penColor:', Color(1000, 656, 104))
assert p('set pen color to (0)')[0] == Block('setPenHueTo:', 0)

assert p("when I receive (cheese)")[0] == Block('EventHatMorph', 'cheese')
