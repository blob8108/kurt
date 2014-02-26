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

"""A Kurt plugin for Scratch 1.4."""

import re
import wave
from copy import copy

import PIL
from construct.lib.container import Container, recursion_lock

import kurt
from kurt import StringIO
from kurt.plugin import Kurt, KurtPlugin, block_workaround

from kurt.scratch14.objtable import *
from kurt.scratch14.blocks import block_list
from kurt.scratch14.heights import clean_up
from kurt.scratch14.user_objects import make_user_objects, user_objects_by_name

# :class:`FixedObjects` have a ``.value`` property to access their value.
# Inline objects, such as int and bool, are converted to their Pythonic
# counterparts.  Array and Dictionary are converted to list and dict.



#-- Hack Container repr to be pretty --#

@recursion_lock("<...>")
def container_repr(self):
    d = dict((k, self[k]) for k in self if not k.startswith("_"))
    r = "\n"
    for (k, v) in d.items():
        r += "    %r: %s,\n" % (k, repr(v).replace("\n", "\n    "))
    return "%s(%s)" % (self.__class__.__name__, r)
Container.__repr__ = container_repr



#-- Utils --#

def get_blocks_by_id(this_block):
    if isinstance(this_block, kurt.Script):
        for block in this_block.blocks:
            for b in get_blocks_by_id(block):
                yield b
    elif isinstance(this_block, kurt.Block):
        yield this_block
        for arg in this_block.args:
            if isinstance(arg, kurt.Block):
                for block in get_blocks_by_id(arg):
                    yield block
            elif isinstance(arg, list):
                for block in arg:
                    for b in get_blocks_by_id(block):
                        yield b

def swap_byte_pairs(data):
    swapped_bytes = ""
    for i in range(0, len(data), 2):
        a = data[i:i+1]
        b = data[i+1:i+2]
        swapped_bytes += b + a
    return swapped_bytes



#-- Main class --#

# kurt_* -- objects from kurt 2.0 api
# v14_*  -- objects from this module, kurt.scratch14

class Serializer(object):
    """Use one instance of Serializer for each load/save operation."""

    def __init__(self, plugin):
        self.plugin = plugin

    def UserObject(self, class_name, **attrs):
        defaults = self.plugin.user_objects[class_name].defaults.copy()
        defaults = dict((k, copy(v)) for (k, v) in defaults.items())
        defaults.update(attrs)
        return Container(class_name=class_name, **defaults)

    def load(self, fp):
        self.project = kurt.Project()

        # parse object table
        v14_project = scratch_file.parse_stream(fp)
        self.info = decode_obj_table(v14_project.info, self.plugin)
        self.stage = decode_obj_table(v14_project.stage, self.plugin)

        # project info
        self.project.notes = self.info.get('comment', '')
        self.project.author = self.info.get('author', '')

        thumbnail = self.info['thumbnail']
        if thumbnail and isinstance(thumbnail, Form):
            thumbnail = self.UserObject('ImageMedia',
                name = 'thumbnail',
                form = thumbnail,
            )
        self.project.thumbnail = self.load_image(thumbnail).image

        # stage
        self.load_scriptable(self.project.stage, self.stage)
        self.load_lists(self.stage.lists, self.project)

        # global vars
        self.project.variables = self.project.stage.variables
        self.project.stage.variables = {}

        # sprites
        for v14_sprite in self.stage.sprites:
            kurt_sprite = kurt.Sprite(self.project, v14_sprite.name)
            self.load_scriptable(kurt_sprite, v14_sprite)
            self.load_lists(v14_sprite.lists, kurt_sprite)
            self.project.sprites.append(kurt_sprite)

        # variable watchers
        for v14_morph in self.stage.submorphs:
            if v14_morph.class_name == 'WatcherMorph':
                self.project.actors.append(self.load_watcher(v14_morph))

        # TODO: stacking order of actors.

        self.project._original = (self.info, self.stage) # DEBUG

        return self.project

    def save(self, fp, project):
        self.project = project

        self.stage = self.UserObject("ScratchStageMorph")

        # project info
        thumbnail = self.save_image(kurt.Costume("thumbnail", (
                self.project.thumbnail or kurt.Image.new((160, 120), (1, 1, 1))
            ))).form

        self.info = {
            'author': self.project.author,
            'comment': self.project.notes.replace("\n", "\r"),
            'thumbnail': thumbnail,
            'history': '',
            'language': 'en',
            'os-version': '',
            'platform': '',
            'scratch-version': '1.4 of 30-Jun-09',
        }

        # make all sprites (need to do before we save scripts)
        for kurt_sprite in self.project.sprites:
            v14_sprite = self.UserObject("ScratchSpriteMorph",
                                         name=kurt_sprite.name)
            v14_sprite._original = kurt_sprite
            self.stage.sprites.append(v14_sprite)

        # stage
        self.save_scriptable(self.project.stage, self.stage)
        self.save_lists(self.project, self.stage)
        for (name, variable) in self.project.variables.items():
            self.stage.variables[name] = variable.value
        self.stage.tempoBPM = self.project.tempo

        # sprites
        for v14_sprite in self.stage.sprites:
            kurt_sprite = v14_sprite._original
            self.save_scriptable(kurt_sprite, v14_sprite)
            self.save_lists(kurt_sprite, v14_sprite)
            del v14_sprite._original

        # variable watchers
        for kurt_actor in self.project.actors:
            if kurt_actor in self.project.sprites:
                self.stage.submorphs.append(
                    self.get_sprite(kurt_actor.name)
                )
                continue

            if isinstance(kurt_actor, kurt.Watcher):
                if kurt_actor.kind == 'list' or not kurt_actor.is_visible:
                    continue
                self.stage.submorphs.append(
                    self.save_watcher(kurt_actor))

        v14_project = Container(
            info = encode_obj_table(self.info, self.plugin),
            stage = encode_obj_table(self.stage, self.plugin),
        )
        scratch_file.build_stream(v14_project, fp)

        return v14_project

    def get_sprite(self, name):
        for sprite in self.stage.sprites:
            if sprite.name == name:
                return sprite

    def get_media(self, v14_scriptable):
        """Return (images, sounds)"""
        images = []
        sounds = []
        for media in v14_scriptable.media:
            if media.class_name == 'SoundMedia':
                sounds.append(media)
            elif media.class_name == 'ImageMedia':
                images.append(media)
        return (images, sounds)

    def load_image(self, v14_image):
        if v14_image:
            if v14_image.jpegBytes:
                image = kurt.Image(v14_image.jpegBytes.value, "JPEG")
                if hasattr(v14_image, 'size'):
                    image._size = v14_image.size
            else:
                form = v14_image.compositeForm or v14_image.form
                (width, height, rgba_array) = form.to_array()
                size = (width, height)
                pil_image = PIL.Image.frombytes("RGBA", size, rgba_array)
                image = kurt.Image(pil_image)
            return kurt.Costume(v14_image.name, image,
                                v14_image.rotationCenter)

    def save_image(self, kurt_costume):
        if kurt_costume:
            image = kurt_costume.image.convert("JPEG", "bitmap")

            if image.format == "JPEG":
                v14_image = self.UserObject("ImageMedia",
                    name = unicode(kurt_costume.name),
                    jpegBytes = ByteArray(kurt_costume.image.contents),
                )
            else:
                pil_image = kurt_costume.image.pil_image
                pil_image = pil_image.convert("RGBA")
                (width, height) = pil_image.size
                rgba_string = pil_image.tobytes()

                v14_image = self.UserObject("ImageMedia",
                    name = unicode(kurt_costume.name),
                    form = Form.from_string(width, height, rgba_string),
                )

            v14_image.size = kurt_costume.image.size
            v14_image.rotationCenter = Point(kurt_costume.rotation_center)
            return v14_image

    def load_sound(self, v14_sound):
        contents = StringIO()
        f = wave.open(contents, 'w')
        f.setnframes(v14_sound.originalSound.samplesSize)
        f.setframerate(v14_sound.originalSound.originalSamplingRate)
        f.setnchannels(1)
        f.setsampwidth(2) # bytes?
        f.writeframes(swap_byte_pairs(v14_sound.originalSound.samples.value))
        f.close()
        return kurt.Sound(v14_sound.name, kurt.Waveform(contents.getvalue()))

    def save_sound(self, kurt_sound):
        switch_with_unknown_purpose = False

        ss = self.UserObject("SampledSound")
        ss.samplesSize = ss.initialCount = kurt_sound.waveform.sample_count
        ss.originalSamplingRate = ss.scaledIncrement = kurt_sound.waveform.rate
        if switch_with_unknown_purpose:
            ss.scaledIncrement *= 2
        else:
            ss.initialCount *= 2

        try:
            f = wave.open(StringIO(kurt_sound.waveform.contents))
        except wave.Error, err:
            err.message += "\nInvalid wave file: %s" % kurt_sound
            err.args = (err.message,)
            raise
        data = swap_byte_pairs(f.readframes(kurt_sound.waveform.sample_count))
        f.close()
        ss.samples = SoundBuffer(data)

        v14_sound = self.UserObject("SoundMedia")
        v14_sound.name = kurt_sound.name
        v14_sound.originalSound = ss
        return v14_sound

    def load_block(self, block_array):
        args = list(block_array)
        command = args.pop(0)
        assert isinstance(command, Symbol)
        command = command.value

        # special-case blocks with weird arguments
        if command == 'EventHatMorph':
            if args[0] == 'Scratch-StartClicked':
                return kurt.Block('whenGreenFlag')
            else:
                return kurt.Block('whenIreceive', args[0])
        elif command == 'MouseClickEventHatMorph':
            return kurt.Block('whenClicked')
        elif command == 'changeVariable':
            command = args.pop(1).value
        else:
            command = command

        # recursively load args
        new_args = []
        for arg in args:
            if isinstance(arg, list):
                if arg and isinstance(arg[0], Symbol):
                    arg = self.load_block(arg)
                else:
                    arg = map(self.load_block, arg)
            elif isinstance(arg, Color):
                arg = kurt.Color(arg.to_8bit())
            elif isinstance(arg, Symbol):
                if arg.value == 'mouse':
                    arg = 'mouse-pointer'
                elif arg.value == 'edge':
                    arg = 'edge'
                elif arg.value in ('all', 'last', 'any'):
                    arg = 'random' if arg.value == 'any' else arg.value
                else:
                    raise ValueError(arg)
            elif getattr(arg, 'class_name', None) == 'ScratchStageMorph':
                arg = "Stage"
            elif getattr(arg, 'class_name', None) == 'ScratchSpriteMorph':
                arg = arg.name
            new_args.append(arg)
        return kurt.Block(command, *new_args)

    def load_script(self, script_array):
        (pos, blocks) = script_array

        # comment?
        if len(blocks) == 1:
            block = blocks[0]
            if block:
                if (isinstance(block[0], Symbol) and
                        block[0].value == 'scratchComment'):
                    text = block[1].replace("\r", "\n")
                    comment = kurt.Comment(text, pos)
                    if len(block) > 4:
                        comment._anchor = block[4]
                    return comment

        # script
        return kurt.Script(map(self.load_block, blocks), pos)

    def save_block(self, kurt_block):
        command = kurt_block.type.convert('scratch14').command

        inserts = list(kurt_block.type.inserts)
        args = []
        for arg in kurt_block.args:
            insert = inserts.pop(0) if inserts else None
            if isinstance(arg, kurt.Block):
                arg = self.save_block(arg)
            elif isinstance(arg, list):
                arg = map(self.save_block, arg)
            elif isinstance(arg, kurt.Color):
                arg = Color.from_8bit(arg)
            elif insert:
                if insert.kind in ('mathOp', 'effect', 'key'):
                    arg = str(arg) # Won't accept unicode

                elif insert.kind in ('spriteOrMouse', 'spriteOrStage',
                        'touching'):
                    if arg == 'mouse-pointer':
                        arg = Symbol('mouse')
                    elif arg == 'edge':
                        arg = Symbol('edge')
                    elif arg == "Stage":
                        arg = self.stage
                    else:
                        arg = self.get_sprite(arg)

                elif isinstance(arg, basestring):
                    if insert.kind in ('listItem', 'listDeleteItem'):
                        if arg in ('last', 'all', 'random'):
                            arg = Symbol('any' if arg == 'random' else arg)
            args.append(arg)

        # special-case blocks with weird arguments
        if command == 'whenGreenFlag':
            command = 'EventHatMorph'
            args = ['Scratch-StartClicked']
        elif command == 'whenIReceive':
            command = 'EventHatMorph'
            args = [args[0]]
        elif command == 'whenClicked':
            command = 'MouseClickEventHatMorph'
            args = ['Scratch-MouseClickEvent']
        elif command in ('changeVar:by:', 'setVar:to:'):
            args = [args[0], Symbol(command), args[1]]
            command = 'changeVariable'

        return [Symbol(command)] + args

    def save_script(self, kurt_script):
        if isinstance(kurt_script, kurt.Script):
            pos = kurt_script.pos or (10, 10)
            blocks = map(self.save_block, kurt_script.blocks)
            return [Point(pos), blocks]
        elif isinstance(kurt_script, kurt.Comment):
            comment = kurt_script
            array = [Symbol('scratchComment'), comment.text, True, 112]
            return [Point(comment.pos), [array]]

    def load_lists(self, v14_lists, kurt_target):
        for v14_list in v14_lists.values():
            kurt_list = kurt.List(map(unicode, v14_list.list_items))
            kurt_target.lists[v14_list.name] = kurt_list

            kurt_watcher = kurt.Watcher(kurt_target,
                    kurt.Block("contentsOfList:", v14_list.name))
            kurt_watcher.is_visible = bool(v14_list.owner)

            (x, y, w, h) = v14_list.bounds.value
            if not kurt_watcher.is_visible:
                x -= 534
                y -= 71
            kurt_watcher.pos = (x, y)
            self.project.actors.append(kurt_watcher)

    def save_lists(self, kurt_target, v14_morph):
        for (name, kurt_list) in kurt_target.lists.items():
            name = unicode(name)
            v14_list = self.UserObject("ScratchListMorph",
                name = name,
                list_items = map(unicode, kurt_list.items),
            )

            pos = kurt_list.watcher.pos
            if pos:
                (x, y) = pos
            else:
                (x, y) = (375, 10)
                # TODO: stack them properly

            if not kurt_list.watcher.is_visible:
                x += 534
                y += 71
            v14_list.bounds = Rectangle([x, y, x+95, y+115])

            v14_list.target = v14_morph
            if kurt_list.watcher.is_visible:
                v14_list.owner = self.stage
                self.stage.submorphs.append(v14_list)

            v14_morph.lists[name] = v14_list

    def load_watcher(self, v14_watcher):
        v14_sprite = v14_watcher.readout.target
        if v14_sprite == self.stage:
            kurt_target = self.project
        else:
            kurt_target = self.project.get_sprite(v14_sprite.name)

        command = v14_watcher.readout.getSelector.value
        command = 'readVariable' if command == 'getVar:' else command
        if v14_watcher.readout.parameter:
            kurt_block = kurt.Block(command, v14_watcher.readout.parameter)
        else:
            kurt_block = kurt.Block(command)

        kurt_watcher = kurt.Watcher(kurt_target, kurt_block)

        (x, y, right, bottom) = v14_watcher.bounds.value
        kurt_watcher.pos = (x, y)

        if v14_watcher.isLarge:
            kurt_watcher.style = "large"
        elif v14_watcher.scratchSlider:
            kurt_watcher.style = "slider"

        kurt_watcher.slider_min = v14_watcher.sliderMin
        kurt_watcher.slider_max = v14_watcher.sliderMax

        return kurt_watcher

    def save_watcher(self, kurt_watcher):
        v14_watcher = self.UserObject("WatcherMorph")
        readout = v14_watcher.readout = self.UserObject("UpdatingStringMorph",
            font_with_size = [Symbol('VerdanaBold'), 10],
        )
        v14_watcher.readoutFrame = self.UserObject("WatcherReadoutFrameMorph",
            submorphs = [v14_watcher.readout]
        )

        if kurt_watcher.pos:
            (x, y) = kurt_watcher.pos
        else:
            (x, y) = (10, 10)

        v14_watcher.name = kurt_watcher.block.type.convert('scratch14').text

        if kurt_watcher.target == self.project:
            v14_morph = self.stage
            v14_watcher.isSpriteSpecfic = False
        else:
            v14_morph = self.get_sprite(kurt_watcher.target.name)
            v14_watcher.name = v14_morph.name + " " + v14_watcher.name

        readout.target = v14_morph
        v14_watcher.owner = self.stage

        selector = kurt_watcher.block.type.convert('scratch14').command
        command = 'getVar:' if selector == 'readVariable' else selector
        readout.getSelector = Symbol(command)

        if kurt_watcher.block.args:
            readout.parameter = kurt_watcher.block.args[0]

        if kurt_watcher.style == "large":
            v14_watcher.isLarge = True
            readout.font_with_size[1] = 14
        elif kurt_watcher.style == "slider":
            v14_watcher.scratchSlider = self.UserObject("WatcherSliderMorph")

        v14_watcher.sliderMin = kurt_watcher.slider_min
        v14_watcher.sliderMax = kurt_watcher.slider_max

        v14_watcher.bounds = Rectangle([x, y, x+1, x+1])

        return v14_watcher

    def load_scriptable(self, kurt_scriptable, v14_scriptable):
        # scripts
        kurt_scriptable.scripts = map(self.load_script, v14_scriptable.scripts)

        # fix comments
        comments = []

        blocks_by_id = []
        # A list of all the blocks in script order but reverse script
        # blocks order.
        # Used to determine which block a Comment is anchored to.
        #
        # Note that Squeak arrays are 1-based, so index with:
        #     blocks_by_id[index - 1]

        for script in kurt_scriptable.scripts:
            if isinstance(script, kurt.Comment):
                comments.append(script)
            elif isinstance(script, kurt.Script):
                for block in reversed(list(get_blocks_by_id(script))):
                    blocks_by_id.append(block)

        attached_comments = []
        for comment in comments:
            if hasattr(comment, '_anchor'):
                # Attach the comment to the right block from the given scripts.
                block = blocks_by_id[comment._anchor - 1]
                block.comment = comment.text
                attached_comments.append(comment)

        for comment in attached_comments:
            kurt_scriptable.scripts.remove(comment)

        # media
        for (name, value) in v14_scriptable.variables.items():
            kurt_scriptable.variables[name] = kurt.Variable(value)

        (images, sounds) = self.get_media(v14_scriptable)
        kurt_scriptable.costumes = map(self.load_image, images)
        kurt_scriptable.sounds = map(self.load_sound, sounds)

        # costume
        if kurt_scriptable.costumes:
            index = images.index(v14_scriptable.costume)
            kurt_scriptable.costume_index = index

        # attributes
        kurt_scriptable.volume = v14_scriptable.volume
        kurt_scriptable.tempo = v14_scriptable.tempoBPM

        # for sprites:
        if isinstance(kurt_scriptable, kurt.Sprite):
            kurt_scriptable.name = v14_scriptable.name
            kurt_scriptable.direction = v14_scriptable.rotationDegrees + 90
            kurt_scriptable.rotation_style = v14_scriptable.rotationStyle.value
            kurt_scriptable.size = v14_scriptable.scalePoint.x * 100.0
            kurt_scriptable.is_draggable = v14_scriptable.draggable
            kurt_scriptable.is_visible = (v14_scriptable.flags == 0)

            # bounds
            (x, y, right, bottom) = v14_scriptable.bounds.value
            (rx, ry) = v14_scriptable.costume.rotationCenter
            x = x + rx - 240
            y = 180 - y - ry
            kurt_scriptable.position = (x, y)

    def save_scriptable(self, kurt_scriptable, v14_scriptable):
        clean_up(kurt_scriptable.scripts)

        v14_scriptable.scripts = map(self.save_script, kurt_scriptable.scripts)

        blocks_by_id = []
        for script in kurt_scriptable.scripts:
            if isinstance(script, kurt.Script):
                for block in reversed(list(get_blocks_by_id(script))):
                    blocks_by_id.append(block)

        def grab_comments(block):
            if block.comment:
                (x, y) = v14_scriptable.scripts[-1][0]
                pos = (x, y + 29)
                array = save_script(kurt.Comment(block.comment, pos),
                                    self.v14_project)
                for i in xrange(len(blocks_by_id)):
                    if blocks_by_id[i] is block:
                        array[1][0].append(i + 1)
                        break
                v14_scriptable.scripts.append(array)

            for arg in block.args:
                if isinstance(arg, kurt.Block):
                    grab_comments(arg)
                elif isinstance(arg, list):
                    map(grab_comments, arg)

        for script in kurt_scriptable.scripts:
            if isinstance(script, kurt.Script):
                for block in script.blocks:
                    grab_comments(block)

        for (name, variable) in kurt_scriptable.variables.items():
            v14_scriptable.variables[name] = variable.value

        images = map(self.save_image, kurt_scriptable.costumes)
        v14_scriptable.media = OrderedCollection(
                images + map(self.save_sound, kurt_scriptable.sounds))

        v14_scriptable.costume = images[kurt_scriptable.costume_index]

        v14_scriptable.volume = kurt_scriptable.volume

        # sprite
        if isinstance(kurt_scriptable, kurt.Sprite):
            v14_scriptable.owner = self.stage

            v14_scriptable.name = kurt_scriptable.name
            v14_scriptable.rotationDegrees = kurt_scriptable.direction - 90
            v14_scriptable.rotationStyle = Symbol(
                    kurt_scriptable.rotation_style)
            v14_scriptable.draggable = kurt_scriptable.is_draggable
            v14_scriptable.flags = 0 if kurt_scriptable.is_visible else 1

            # bounds
            (x, y) = kurt_scriptable.position
            (rx, ry) = kurt_scriptable.costume.rotation_center
            x = x + 240 - rx
            y = 180 - y - ry
            (w, h) = kurt_scriptable.costume.image.size
            v14_scriptable.bounds = Rectangle([x, y, x+w, y+h])


class Scratch14Plugin(KurtPlugin):
    name = "scratch14"
    display_name = "Scratch 1.4"
    extension = ".sb"
    blocks = block_list
    features = []

    serializer_cls = Serializer
    user_objects = make_user_objects(user_objects_by_name)

    def load(self, fp):
        return self.serializer_cls(self).load(fp)

    def save(self, fp, project):
        return self.serializer_cls(self).save(fp, project)


Kurt.register(Scratch14Plugin())



#-- Block workarounds --#

# 1.4 -> 2.0
block_workaround('stop script', kurt.Block('stop', 'this script'))
block_workaround('stop all', kurt.Block('stop', 'all'))
block_workaround('forever if',
    lambda block: kurt.Block('forever', [kurt.Block('if', *block.args)]))
block_workaround('loud?', kurt.Block('>', kurt.Block('loudness'), 30))

# 2.0 -> 1.4
block_workaround('stop', lambda block: {
    'this script': kurt.Block('stop script'),
    'all': kurt.Block('stop all'),
}.get(block.args[0], None))

