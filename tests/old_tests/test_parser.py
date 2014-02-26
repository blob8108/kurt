import os
import sys

# try and find kurt directory
path_to_file = os.path.join(os.getcwd(), __file__)
path_to_lib = os.path.split(os.path.split(path_to_file)[0])[0]
sys.path.append(path_to_lib)
import kurt



project = kurt.Project()
testcontext = project.stage
testcontext.variables['foo'] = kurt.Variable()
testcontext.lists['positions'] = kurt.List()
project.sprites.append(kurt.Sprite(project, 'Sprite1'))

p = lambda x: kurt.text.parse(x+"\n", testcontext)
pb = lambda x: kurt.text.parse(x, testcontext)[0]

try:
    pb("a")
except SyntaxError:
    pass
else:
    raise

print pb("set foo to 4")

assert pb("set foo to 10") == kurt.Block("setVar:to:", "foo", u'10')
assert pb("set x to 4") == kurt.Block("xpos:", u'4')
assert pb("set foo to 10") == kurt.Block("setVar:to:", "foo", u'10')
assert pb("set foo to 1 * 2") == kurt.Block("setVar:to:", "foo",
                                              kurt.Block("*", 1, 2))
assert pb("set size to 10%") == kurt.Block('setSizeTo:', 10)

testf = "set foo to item 2 + 3 * 4 of positions + 10"
out = "set [foo v] to ((item ((2) + ((3) * (4))) of [positions v]) + (10))"
assert pb(testf).stringify(True) == out



# scratchblocks

def command_getter(self):
    return self.type.convert('scratch14').command
kurt.Block.command = property(command_getter)


assert p("say (length of [hello])")[0].args[0].command == 'stringLength:'
assert p("say (length of (foo))")[0].args[0].command == 'stringLength:'
#assert p("say (length of [positions v])")[0].args[0].command == 'lineCountOfList:'

assert p(u'[x position v] of [Sprite1]')[0].command == 'getAttribute:of:'
assert p(u'[x position v] of [Sprite1 v]')[0].command == 'getAttribute:of:'
assert p(u'[sqrt v] of (6)')[0].command == 'computeFunction:of:'
assert p(u'[sqrt v] of [6]')[0].command == 'computeFunction:of:'

assert p(u'[x position v] of (foo)')[0].command == 'getAttribute:of:'
assert p(u'[sqrt v] of (foo)')[0].command == 'computeFunction:of:'
for mf in kurt.Insert('number', 'mathOp').options():
    assert p(u'[%s v] of (foo)' % mf)[0].command == 'computeFunction:of:'

assert p('set pen color to [#faa41a]')[0] == kurt.Block('penColor:',
        kurt.Color('#faa41a'))
assert p('set pen color to (0)')[0] == kurt.Block('setPenHueTo:', 0)



def check(x):
    b = p(x)
    assert p(b.stringify()) == b

check("""
if <>
say [hi]
else
play sound [pop v]
end
""")

check("""
if <>
move (10) steps
end
""")

check("""
repeat(10)
  turn cw (4) degrees
end
""")


assert p("when I receive (cheese)")[0] == kurt.Block('whenIreceive', 'cheese')

