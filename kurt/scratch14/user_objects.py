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

"""User-class objects with variable numbers of fields.
Most of the objects you're interested in live here.

They support dot notation for accessing fields. Use .fields.keys() to see
available fields [dir() won't show them.]

"""

from collections import OrderedDict
from pprint import pformat

from construct import Container

from kurt.scratch14.fixed_objects import *


#-- Class IDs --#

user_object_class_ids = {
    9:   'String',
    10:  'Symbol',
    11:  'ByteArray',
    12:  'SoundBuffer',
    13:  'Bitmap',
    14:  'UTF8',

    20:  'Array',
    21:  'OrderedCollection',
    22:  'Set',
    23:  'IdentitySet',
    24:  'Dictionary',
    25:  'IdentityDictionary',

    30:  'Color',
    31:  'TranslucentColor',
    32:  'Point',
    33:  'Rectangle',
    34:  'Form',
    35:  'ColorForm',

    100: 'Morph',
    101: 'BorderedMorph',
    102: 'RectangleMorph',
    103: 'EllipseMorph',
    104: 'AlignmentMorph',
    105: 'StringMorph',
    106: 'UpdatingStringMorph',
    107: 'SimpleSliderMorph',
    108: 'SimpleButtonMorph',
    109: 'SampledSound',
    110: 'ImageMorph',
    111: 'SketchMorph',

    123: 'SensorBoardMorph',
    124: 'ScratchSpriteMorph',
    125: 'ScratchStageMorph',

    140: 'ChoiceArgMorph',
    141: 'ColorArgMorph',
    142: 'ExpressionArgMorph',
    145: 'SpriteArgMorph',
    147: 'BlockMorph',
    148: 'CommandBlockMorph',
    149: 'CBlockMorph',
    151: 'HatBlockMorph',
    153: 'ScratchScriptsMorph',
    154: 'ScratchSliderMorph',
    155: 'WatcherMorph',
    157: 'SetterBlockMorph',
    158: 'EventHatMorph',
    160: 'VariableBlockMorph',
    162: 'ImageMedia',
    163: 'MovieMedia',
    164: 'SoundMedia',
    165: 'KeyEventHatMorph',
    166: 'BooleanArgMorph',
    167: 'EventTitleMorph',
    168: 'MouseClickEventHatMorph',
    169: 'ExpressionArgMorphWithMenu',
    170: 'ReporterBlockMorph',
    171: 'MultilineStringMorph',
    172: 'ToggleButton',
    173: 'WatcherReadoutFrameMorph',
    174: 'WatcherSliderMorph',
    175: 'ScratchListMorph',
    176: 'ScrollingStringMorph',
}


#-- UserObject definition class --#

class UserObjectDef(Container):

    def __init__(self, version, inherits, defaults=[]):
        self.version = int(version) if version else None
        self.inherits = str(inherits) if inherits else None
        self.defaults = OrderedDict(defaults)


def make_user_objects(definitions):
    for obj in definitions.values():
        all_parents = [obj]
        parent = obj
        while parent.inherits:
            parent = definitions[parent.inherits]
            all_parents.append(parent)
        attrs = OrderedDict()
        for parent in reversed(all_parents):
            attrs.update(parent.defaults)
        obj.defaults = attrs
    return definitions


#-- UserObject definitions --#

user_objects_by_name = OrderedDict({
    'BaseMorph': UserObjectDef(None, None, [
        ('bounds', Rectangle([0, 0, 1, 1])),
        ('owner', None),
        ('submorphs', []),
        ('color', Color((1023, 1023, 1023))),
        ('flags', 0),
        ('properties', None),
    ]),

    'Morph': UserObjectDef(1, 'BaseMorph'),

    'BorderedMorph': UserObjectDef(1, 'BaseMorph', [
        ('borderWidth', 1),
        ('borderColor', Color((0, 0, 0))),
    ]),

    'RectangleMorph': UserObjectDef(1, 'BorderedMorph'),

    'EllipseMorph': UserObjectDef(1, 'BorderedMorph'),

    'AlignmentMorph': UserObjectDef(1, 'RectangleMorph', [
        ('orientation', None),
        ('centering', None),
        ('hResizing', None),
        ('vResizing', None),
        ('inset', 0),
    ]),

    'StringMorph': UserObjectDef(1, 'BaseMorph', [
        ('font_with_size', None),
        ('emphasis', None),
        ('contents', None),
    ]),

    'UpdatingStringMorph': UserObjectDef(1, 'StringMorph', [
        ('format', None),
        ('target', None),
        ('getSelector', None),
        ('putSelector', None),
        ('parameter', None),
        ('floatPrecision', None),
        ('growable', None),
        ('stepTime', None),
    ]),

    'SimpleSliderMorph': UserObjectDef(1, 'BorderedMorph', [
        ('slider', None),
        ('value', None),
        ('setValueSelector', None),
        ('sliderShadow', None),
        ('sliderColor', None),
        ('descending', None),
        ('model', None),
        ('target', None),
        ('arguments', None),
        ('minVal', None),
        ('maxVal', None),
        ('truncate', None),
        ('sliderThickness', None),
    ]),

    'SimpleButtonMorph': UserObjectDef(1, 'RectangleMorph', [
        ('target', None),
        ('actionSelector', None),
        ('arguments', None),
        ('actWhen', None),
    ]),

    'SampledSound': UserObjectDef(1, None, [
        ('envelopes', []),
        ('scaledVol', 32768),
        ('initialCount', None),
        ('samples', None),
        ('originalSamplingRate', None),
        ('samplesSize', None),
        ('scaledIncrement', None),
        ('scaledInitialIndex', None),
    ]),

    'ImageMorph': UserObjectDef(1, 'BaseMorph', [
        ('form', None),
        ('transparency', None),
    ]),

    'SketchMorph': UserObjectDef(1, 'BaseMorph', [
        ('originalForm', None),
        ('rotationCenter', None),
        ('rotationDegrees', None),
        ('rotationStyle', None),
        ('scalePoint', None),
        ('offsetWhenRotated', None),
    ]),

    'SensorBoardMorph': UserObjectDef(1, 'BaseMorph', [
        ('unknown', None),
    ]),

    'ScriptableScratchMorph': UserObjectDef(1, 'BaseMorph', [
        ('name', None),
        ('variables', {}),
        ('scripts', []),
        ('isClone', False),
        ('media', []),
        ('costume', None),
    ]),

    'ScratchSpriteMorph': UserObjectDef(3, 'ScriptableScratchMorph', [
        ('visibility', 100),
        ('scalePoint', Point(1.0, 1.0)),
        ('rotationDegrees', 0.0),
        ('rotationStyle', Symbol('normal')),
        ('volume', 100),
        ('tempoBPM', 60),
        ('draggable', False),
        ('sceneStates', {}),
        ('lists', {}),
    ]),

    'ScratchStageMorph': UserObjectDef(5, 'ScriptableScratchMorph', [
        ('zoom', 1.0),
        ('hPan', 0),
        ('vPan', 0),
        ('obsoleteSavedState', None),
        ('sprites', OrderedCollection([])),
        ('volume', 100),
        ('tempoBPM', 60),
        ('sceneStates', {}),
        ('lists', {}),
    ]),

    'ChoiceArgMorph': UserObjectDef(1, 'BaseMorph'),

    'ColorArgMorph': UserObjectDef(1, 'BaseMorph'),

    'ExpressionArgMorph': UserObjectDef(1, 'BaseMorph'),

    'SpriteArgMorph': UserObjectDef(1, 'BaseMorph'),

    'BlockMorph': UserObjectDef(1, 'BaseMorph', [
        ('isSpecialForm', None),
        ('oldColor', None),
    ]),

    'CommandBlockMorph': UserObjectDef(1, 'BlockMorph', [
        ('commandSpec', None),
        ('argMorphs', None),
        ('titleMorph', None),
        ('receiver', None),
        ('selector', None),
        ('isReporter', None),
        ('isTimed', None),
        ('wantsName', None),
        ('wantsPossession', None),
    ]),

    'CBlockMorph': UserObjectDef(1, 'BaseMorph'),

    'HatBlockMorph': UserObjectDef(1, 'BaseMorph'),

    'ScratchScriptsMorph': UserObjectDef(1, 'BorderedMorph'),

    'ScratchSliderMorph': UserObjectDef(1, 'BaseMorph'),

    'WatcherMorph': UserObjectDef(5, 'AlignmentMorph', [
        ('titleMorph', None),
        ('readout', None),
        ('readoutFrame', None),
        ('scratchSlider', None),
        ('watcher', None),
        ('isSpriteSpecific', False),
        ('unused', None),
        ('sliderMin', None),
        ('sliderMax', None),
        ('isLarge', False),
    ]),

    'SetterBlockMorph': UserObjectDef(1, 'BaseMorph'),

    'EventHatMorph': UserObjectDef(1, 'BaseMorph'),

    'VariableBlockMorph': UserObjectDef(1, 'CommandBlockMorph', [
        ('isBoolean', None),
    ]),

    'ScratchMedia': UserObjectDef(None, None, [
        ('name', ''),
    ]),

    'ImageMedia': UserObjectDef(4, 'ScratchMedia', [
        ('form', None),
        ('rotationCenter', Point(0, 0)),
        ('textBox', None),
        ('jpegBytes', None),
        ('compositeForm', None),
    ]),

    'MovieMedia': UserObjectDef(1, 'ScratchMedia', [
        ('fileName', None),
        ('fade', None),
        ('fadeColor', None),
        ('zoom', None),
        ('hPan', None),
        ('vPan', None),
        ('msecsPerFrame', None),
        ('currentFrame', None),
        ('moviePlaying', None),
    ]),

    'SoundMedia': UserObjectDef(2, 'ScratchMedia', [
        ('originalSound', None),
        ('volume', 100),
        ('balance', 50),
        ('compressedSampleRate', None),
        ('compressedBitsPerSample', None),
        ('compressedData', None),
    ]),

    'KeyEventHatMorph': UserObjectDef(1, 'BaseMorph'),

    'BooleanArgMorph': UserObjectDef(1, 'BaseMorph'),

    'EventTitleMorph': UserObjectDef(1, 'BaseMorph'),

    'MouseClickEventHatMorph': UserObjectDef(1, 'BaseMorph'),

    'ExpressionArgMorphWithMenu': UserObjectDef(1, 'BaseMorph'),

    'ReporterBlockMorph': UserObjectDef(1, 'BaseMorph'),

    'MultilineStringMorph': UserObjectDef(1, 'BorderedMorph', [
        ('font', None),
        ('textColor', None),
        ('selectionColor', None),
        ('lines', None),
    ]),

    'ToggleButton': UserObjectDef(1, 'SimpleButtonMorph'),

    'WatcherReadoutFrameMorph': UserObjectDef(1, 'BorderedMorph'),

    'WatcherSliderMorph': UserObjectDef(1, 'SimpleSliderMorph'),

    'ScratchListMorph': UserObjectDef(2, 'BorderedMorph', [
        ('borderColor', Color((594, 582, 582))),
        ('color', Color((774, 786, 798))),
        ('borderWidth', 2),

        ('name', None),
        ('list_items', []),
        ('target', None),
    ]),

    'ScrollingStringMorph': UserObjectDef(1, 'BaseMorph'),
})

#ScratchSpriteMorph.color = Color((0, 0, 1023))
#WatcherMorph.centering = Symbol('center')
