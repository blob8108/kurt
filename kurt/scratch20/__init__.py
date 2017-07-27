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

"""A Kurt plugin for Scratch 2.0."""

import zipfile
import json
import time
import os
import hashlib
import struct

import kurt

from kurt.plugin import Kurt, KurtPlugin
from kurt.scratch20.blocks import make_block_types, custom_block, make_spec


SOUND_FORMATS = ['.wav']

WATCHER_MODES = [None,
                 'normal',
                 'large',
                 'slider',
                 ]

CATEGORY_COLORS = {
    'variables': kurt.Color('#ee7d16'),
    'motion': kurt.Color('#4a6cd4'),
    'looks': kurt.Color('#8a55d7'),
    'sound': kurt.Color('#bb42c3'),
    'sensing': kurt.Color('#2ca5e2'),
}


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


class ZipReader(object):

    def __init__(self, fp):
        self.zip_file = zipfile.ZipFile(fp, "r")
        self.json = json.load(self.zip_file.open("project.json"))
        self.project = kurt.Project()
        self.list_watchers = []
        self.loaded_images = {}
        self.loaded_sounds = {}
        self.custom_blocks = {}

        # files
        self.image_filenames = {}
        self.sound_filenames = {}

        for filename in self.zip_file.namelist():
            if filename == 'project.json':
                continue
            (name, extension) = os.path.splitext(filename)

            if extension in SOUND_FORMATS:
                self.sound_filenames[int(name)] = filename
            else:
                self.image_filenames[int(name)] = filename

        # info
        self.project.tempo = self.json['tempoBPM']
        self.project.notes = self.json['info'].get('comment', u"")
        self.project.author = self.json['info'].get('author', u"")

        # stage
        self.project.stage = self.load_scriptable(self.json, is_stage=True)

        # sprites
        actors = []
        for cd in self.json['children']:
            if 'objName' in cd:
                sprite = self.load_scriptable(cd)
                self.project.sprites.append(sprite)
                actors.append(sprite)
            else:
                actors.append(cd)

        # watchers
        for actor in actors:
            if not isinstance(actor, kurt.Sprite):
                if 'listName' in actor:
                    continue
                actor = self.load_watcher(actor)
            self.project.actors.append(actor)

        self.project.actors += self.list_watchers

    def read_image(self, file_id):
        if file_id not in self.loaded_images:
            if file_id not in self.image_filenames:
                return None

            filename = self.image_filenames[file_id]
            (_, extension) = os.path.splitext(filename)
            contents = self.zip_file.open(filename).read()
            _format = kurt.Image.image_format(extension)
            self.loaded_images[file_id] = kurt.Image(contents, _format)

        return self.loaded_images[file_id]

    def read_waveform(self, file_id, rate, sample_count):
        if file_id not in self.loaded_sounds:
            filename = self.sound_filenames[file_id]
            contents = self.zip_file.open(filename).read()
            self.loaded_sounds[file_id] = kurt.Waveform(contents, rate,
                                                        sample_count)
        return self.loaded_sounds[file_id]

    def finish(self):
        self.zip_file.close()

    def load_scriptable(self, sd, is_stage=False):
        if is_stage:
            scriptable = kurt.Stage(self.project)
        elif 'objName' in sd:
            scriptable = kurt.Sprite(self.project, sd["objName"])
        else:
            return self.load_watcher(sd)

        # costumes
        for cd in sd.get("costumes", []):
            image = self.read_image(cd['baseLayerID'])
            rotation_center = (cd['rotationCenterX'], cd['rotationCenterY'])

            if cd['bitmapResolution'] != 1:
                (w, h) = image.size
                w /= cd['bitmapResolution']
                h /= cd['bitmapResolution']
                image = image.resize((w, h))

                (x, y) = rotation_center
                x /= cd['bitmapResolution']
                y /= cd['bitmapResolution']
                rotation_center = (x, y)

            if 'text' in cd:
                text_layer = self.read_image(cd['textLayerID'])

                if text_layer:
                    image = image.paste(text_layer)

            scriptable.costumes.append(kurt.Costume(cd['costumeName'], image,
                                                    rotation_center))

        # sounds
        for snd in sd.get("sounds", []):
            scriptable.sounds.append(kurt.Sound(snd['soundName'],
                                                self.read_waveform(snd['soundID'], snd['rate'],
                                                                   snd['sampleCount'])
                                                )
                                     )

        # vars & lists
        target = self.project if is_stage else scriptable

        for vd in sd.get("variables", []):
            var = kurt.Variable(vd['value'], vd['isPersistent'])
            target.variables[vd['name']] = var

        for ld in sd.get("lists", []):
            name = ld['listName']
            target.lists[name] = kurt.List(ld['contents'],
                                           ld['isPersistent'])
            self.list_watchers.append(kurt.Watcher(target,
                                                   kurt.Block("contentsOfList:", name), is_visible=ld['visible'],
                                                   pos=(ld['x'], ld['y'])))

        # custom blocks first
        for script_array in sd.get("scripts", []):
            if script_array[2]:
                block_array = script_array[2][0]

                if block_array[0] == 'procDef':
                    (_, spec, input_names, defaults, is_atomic) = block_array
                    cb = custom_block(spec, input_names, defaults)
                    cb.is_atomic = is_atomic
                    self.custom_blocks[spec] = cb

        # scripts
        for script_array in sd.get("scripts", []):
            scriptable.scripts.append(self.load_script(script_array))

        # comments
        blocks_by_id = []
        for script in scriptable.scripts:
            for block in list(get_blocks_by_id(script)):
                blocks_by_id.append(block)

        for comment_array in sd.get("scriptComments", []):
            (x, y, w, h, expanded, block_id, text) = comment_array

            if block_id > -1:
                blocks_by_id[block_id].comment = text
            else:
                scriptable.scripts.append(kurt.Comment(text, (x, y)))

        # sprite only
        if not is_stage:
            scriptable.position = (sd['scratchX'], sd['scratchY'])
            scriptable.direction = sd['direction']
            scriptable.rotation_style = str(sd['rotationStyle'])
            scriptable.is_draggable = sd['isDraggable']
            scriptable.is_visible = sd['visible']
            scriptable.size = sd['scale'] * 100.0

        return scriptable

    def load_watcher(self, wd):
        command = 'readVariable' if wd['cmd'] == 'getVar:' else wd['cmd']
        if wd['target'] == self.json['objName']:  # Usually "Stage"
            target = self.project
        else:
            target = self.project.get_sprite(wd['target'])
            assert target

        watcher = kurt.Watcher(target,
                               kurt.Block(command, *(wd['param'].split(',') if wd['param']
                                                     else [])),
                               style=WATCHER_MODES[wd['mode']],
                               is_visible=wd['visible'],
                               pos=(wd['x'], wd['y']),
                               )
        watcher.slider_min = wd['sliderMin']
        watcher.slider_max = wd['sliderMax']

        return watcher

    def load_block(self, block_array):
        block_array = list(block_array)
        command = block_array.pop(0)

        if command == 'procDef':  # CustomBlockType definition
            spec = block_array[0]

            return kurt.Block('procDef', self.custom_blocks[spec])

        if command == 'call':  # CustomBlockType call
            block_type = self.custom_blocks[block_array.pop(0)]
        else:
            block_type = kurt.BlockType.get(command)

        inserts = list(block_type.inserts)
        args = []
        for arg in block_array:
            insert = inserts.pop(0) if inserts else None

            if isinstance(arg, list):
                if isinstance(arg[0], list):  # 'stack'-shaped Insert
                    arg = map(self.load_block, arg)
                else:  # Block
                    arg = self.load_block(arg)
            elif insert:
                if insert.shape == 'color':
                    arg = self.load_color(arg)
                elif insert.kind == 'spriteOrStage' and arg == '_stage_':
                    arg = 'Stage'
                elif (insert.kind in ('spriteOrMouse', 'touching')
                        and arg == '_mouse_'):
                    arg = 'mouse-pointer'
                elif insert.kind == 'touching' and arg == '_edge_':
                    arg = 'edge'
                elif insert.kind == 'spriteOnly' and arg == '_myself_':
                    arg = 'myself'
            args.append(arg)

        return kurt.Block(block_type, *args)

    def load_script(self, script_array):
        (x, y, blocks) = script_array
        blocks = map(self.load_block, blocks)

        return kurt.Script(blocks, pos=(x, y))

    def load_color(self, value):
        # convert signed to unsigned 32-bit int
        value = struct.unpack('=I', struct.pack('=i', value))[0]
        # throw away leading ff, if any
        value &= 0x00ffffff

        return kurt.Color((value & 0xff0000) >> 16,
                          (value & 0x00ff00) >> 8,
                          (value & 0x0000ff),
                          )


class ZipWriter(object):

    def __init__(self, fp, project):
        self.zip_file = zipfile.ZipFile(fp, "w")
        self.image_dicts = {}
        self.waveform_dicts = {}

        self.json = {
            "penLayerMD5": "279467d0d49e152706ed66539b577c00.png",
            "tempoBPM": project.tempo,
            "children": [],
            "info": {
                "comment": project.notes,
                "author": project.author,
                "scriptCount": sum(len(s.scripts)
                                   for s in [project.stage] + project.sprites),
                "spriteCount": len(project.sprites),
                "hasCloudData": False,  # TODO
                "videoOn": False,
                "userAgent": "",
                "flashVersion": "",
                "projectID": "",
            },
            "videoAlpha": 0.5,
        }

        self.json.update(self.save_scriptable(project.stage))
        sprites = {}
        for (i, sprite) in enumerate(project.sprites):
            sprites[sprite.name] = self.save_scriptable(sprite, i)

        for actor in project.actors:
            if isinstance(actor, kurt.Sprite):
                actor = sprites[actor.name]
            elif isinstance(actor, kurt.Watcher):
                actor = self.save_watcher(actor)

            if actor:
                self.json["children"].append(actor)

        self.write_file("project.json", json.dumps(self.json))

    def finish(self):
        self.zip_file.close()

    def write_file(self, name, contents):
        """Write file contents string into archive."""

        # TODO: find a way to make ZipFile accept a file object.
        zi = zipfile.ZipInfo(name)
        zi.date_time = time.localtime(time.time())[:6]
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0777 << 16L
        self.zip_file.writestr(zi, contents)

    def write_image(self, image):
        if image not in self.image_dicts:
            image_id = len(self.image_dicts)
            image = image.convert("SVG", "JPEG", "PNG")
            ext = (image.extension or ".png")
            filename = str(image_id) + ext
            self.write_file(filename, image.contents)

            self.image_dicts[image] = {
                "baseLayerID": image_id,  # -1 for download
                "bitmapResolution": 1,
                "baseLayerMD5": hashlib.md5(image.contents).hexdigest() + ext,
            }

        return self.image_dicts[image]

    def write_waveform(self, waveform):
        if waveform not in self.waveform_dicts:
            waveform_id = len(self.waveform_dicts)
            filename = str(waveform_id) + waveform.extension
            self.write_file(filename, waveform.contents)

            self.waveform_dicts[waveform] = {
                "soundID": waveform_id,  # -1 for download
                "md5": hashlib.md5(waveform.contents).hexdigest() + \
                waveform.extension,
                "rate": waveform.rate,
                "sampleCount": waveform.sample_count,
                "format": "",
            }

        return self.waveform_dicts[waveform]

    def save_watcher(self, watcher):
        if watcher.kind == 'list':
            return

        pbt = watcher.block.type.convert('scratch20')
        if pbt.command == 'senseVideoMotion':
            label = 'video ' + watcher.block.args[0]
        elif pbt.command == 'timeAndDate':
            label = watcher.block.args[0]
        else:
            label = pbt.text % tuple(watcher.block.args)

        if not isinstance(watcher.target, kurt.Project):
            label = watcher.target.name + ": " + label

        return {
            'cmd': 'getVar:' if pbt.command == 'readVariable' else pbt.command,
            'param': ",".join(map(unicode, watcher.block.args))
            if watcher.block.args else None,
            'label': label,
            'target': ('Stage' if isinstance(watcher.target, kurt.Project)
                       else watcher.target.name),
            'mode': WATCHER_MODES.index(watcher.style),
            'sliderMax': watcher.slider_max,
            'sliderMin': watcher.slider_min,
            'visible': watcher.is_visible,
            'x': watcher.pos[0] if watcher.pos else 10,
            'y': watcher.pos[1] if watcher.pos else 10,
            'color': self.save_color(CATEGORY_COLORS[pbt.category]),
            'isDiscrete': True,
        }

    def save_scriptable(self, scriptable, i=None):
        is_sprite = isinstance(scriptable, kurt.Sprite)

        sd = {
            "objName": scriptable.name,
            "currentCostumeIndex": scriptable.costume_index or 0,
            "scripts": filter(None, [self.save_script(s) for s in
                                     scriptable.scripts]),
            "scriptComments": [],
            "costumes": [self.save_costume(c) for c in scriptable.costumes],
            "sounds": [self.save_sound(c) for c in scriptable.sounds],
            "variables": [],
            "lists": [],
        }

        # comments
        blocks_by_id = []
        for script in scriptable.scripts:
            if isinstance(script, kurt.Comment):
                sd["scriptComments"].append(self.save_comment(script))

            for block in list(get_blocks_by_id(script)):
                blocks_by_id.append(block)

        def grab_comments(block):
            if block.comment:
                (x, y) = scriptable.scripts[-1].pos
                pos = (x, y + 29)
                array = self.save_comment(kurt.Comment(block.comment, pos))
                array[5] = blocks_by_id.index(block)
                sd["scriptComments"].append(array)

            for arg in block.args:
                if isinstance(arg, kurt.Block):
                    grab_comments(arg)
                elif isinstance(arg, list):
                    map(grab_comments, arg)

        for script in scriptable.scripts:
            if isinstance(script, kurt.Script):
                for block in script.blocks:
                    grab_comments(block)

        # sprite only
        if is_sprite:
            sd.update({
                "indexInLibrary": i + 1,
                "scratchX": scriptable.position[0],
                "scratchY": scriptable.position[1],
                "direction": scriptable.direction,
                "rotationStyle": scriptable.rotation_style,
                "isDraggable": scriptable.is_draggable,
                "visible": scriptable.is_visible,
                "scale": scriptable.size * 0.01,
                "spriteInfo": {},
            })

        # vars & lists
        target = scriptable if is_sprite else scriptable.project

        for (name, variable) in target.variables.items():
            sd["variables"].append({
                "name": name,
                "value": variable.value,
                "isPersistent": variable.is_cloud,
            })

        for (name, list_) in target.lists.items():
            sd["lists"].append({
                "listName": name,
                "contents": list_.items,
                "isPersistent": list_.is_cloud,
                "visible": list_.watcher.is_visible,
                "x": list_.watcher.pos[0] if list_.watcher.pos else 10,
                "y": list_.watcher.pos[1] if list_.watcher.pos else 10,
                "width": 120,
                "height": 117,
            })

        return sd

    def save_block(self, block):
        if isinstance(block.type, kurt.CustomBlockType):
            spec = make_spec(block.type.parts)
            prefix = ['call', spec]
            command = None
        else:
            command = block.type.convert("scratch20").command
            prefix = [command]

        if command == 'procDef':
            cb = block.args[0]
            spec = make_spec(cb.parts)
            input_names = [i.name for i in cb.inserts]

            return ['procDef', spec, input_names, cb.defaults, cb.is_atomic]

        args = []
        inserts = list(block.type.inserts)
        for arg in block.args:
            insert = inserts.pop(0) if inserts else None
            if isinstance(arg, kurt.Block):
                arg = self.save_block(arg)
            elif isinstance(arg, list):
                arg = map(self.save_block, arg)
            elif isinstance(arg, kurt.Color):
                arg = self.save_color(arg)
            elif insert:
                if insert.kind == 'spriteOrStage':
                    if arg == 'Stage':
                        arg = '_stage_'
                elif (insert.kind in ('spriteOrMouse', 'touching')
                        and arg == 'mouse-pointer'):
                    arg = '_mouse_'
                elif insert.kind == 'touching' and arg == 'edge':
                    arg = '_edge_'
                elif insert.kind == 'spriteOnly' and arg == 'myself':
                    arg = '_myself_'
            args.append(arg)

        return prefix + args

    def save_script(self, script):
        if isinstance(script, kurt.Script):
            (x, y) = script.pos or (10, 10)

            return [x, y, map(self.save_block, script.blocks)]

    def save_comment(self, comment):
        (x, y) = comment.pos
        expanded = True
        h = 200 if expanded else 19

        return [x, y, 150, h, expanded, -1, comment.text]

    def save_costume(self, costume):
        cd = self.write_image(costume.image)
        (rx, ry) = costume.rotation_center
        cd.update({
            "costumeName": costume.name,
            "rotationCenterX": rx,
            "rotationCenterY": ry,
        })

        return cd

    def save_sound(self, sound):
        snd = self.write_waveform(sound.waveform)
        snd.update({
            "soundName": sound.name,
        })

        return snd

    def save_color(self, color):
        # build RGB values
        value = (color.r << 16) + (color.g << 8) + color.b

        # convert unsigned to signed 32-bit int
        value = struct.unpack('=i', struct.pack('=I', value))[0]

        return value


class Scratch20Plugin(KurtPlugin):
    name = "scratch20"
    display_name = "Scratch 2.0"
    extension = ".sb2"
    features = [
        "Custom Blocks",
        "Vector Images",
    ]
    blocks = make_block_types()

    def load(self, fp):
        zl = ZipReader(fp)
        zl.project._original = zl.json
        zl.finish()

        return zl.project

    def save(self, fp, project):
        zw = ZipWriter(fp, project)
        zw.finish()

        return zw.json


Kurt.register(Scratch20Plugin())
