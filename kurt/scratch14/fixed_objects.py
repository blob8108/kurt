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

"""Primitive fixed-format objects - eg String, Dictionary."""

from array import array # used by Form
from copy import copy

from construct import Container, Struct, Embed, Rename
from construct import PascalString, UBInt32, SBInt32, UBInt16, UBInt8, Bytes
from construct import BitStruct, Padding, Bits
from construct import Value, Switch, If, IfThenElse, OptionalGreedyRepeater
from construct import Array as StrictRepeater, Array as MetaRepeater
# We can't import the name Array, as we use it. -_-
import construct

from inline_objects import field


def default_colormap():
    # This generation comes from the squeak source under initializeIndexColors
    colormap = []
    # 1-bit colors
    colormap.append((255, 255, 255, 255))
    colormap.append((0, 0, 0, 255))
    # additional 2-bit colors
    colormap.append((255, 255, 255, 255))
    colormap.append((127, 127, 127, 255))
    # additional 4-bit colors
    colormap.append((255, 0, 0, 255))
    colormap.append((0, 255, 0, 255))
    colormap.append((0, 0, 255, 255))
    colormap.append((0, 255, 255, 255))
    colormap.append((255, 255, 0, 255))
    colormap.append((255, 0, 255, 255))
    colormap.append((31, 31, 31, 255))
    colormap.append((63, 63, 63, 255))
    colormap.append((95, 95, 95, 255))
    colormap.append((159, 159, 159, 255))
    colormap.append((191, 191, 191, 255))
    colormap.append((223, 223, 223, 255))
    # additional 8-bit colors
    for i in range(32):  # 24 more shades of gray
        if i % 4 == 0:
            continue
        value = 255 * i / 32
        colormap.append((value, value, value, 255))
    for red in range(6):  # Color "cube" with six steps for each primary color
        for blue in range(6):
            for green in range(6):
                colormap.append((255 * red / 5,
                                 255 * green / 5,
                                 255 * blue / 5,
                                 255))
    return colormap


class FixedObject(object):
    """A primitive fixed-format object - eg String, Dictionary.
    value property - contains the object's value."""
    def __init__(self, value):
        if isinstance(value, FixedObject):
            value = value.value
        self.value = value

    def to_construct(self, context):
        return Container(
            classID = self.__class__.__name__,
            value = self.to_value(),
        )

    @classmethod
    def from_construct(cls, obj, context):
        fixed_obj = cls.from_value(obj.value)
        return fixed_obj

    def to_value(self):
        return self.value

    @classmethod
    def from_value(cls, value):
        return cls(value)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.value == other.value

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.value)

    def copy(self):
        return self.__class__(copy(self.value))

    __copy__ = copy


class ContainsRefs: pass

class FixedObjectWithRepeater(FixedObject):
    """Used internally to handle things like
        Struct("",
            UBInt32("length"),
            MetaRepeater(lambda ctx: ctx.length, UBInt32("items")),
        )
    """
    def to_value(self):
        return Container(items = self.value, length = len(self.value))

    @classmethod
    def from_value(cls, obj):
        assert len(obj.items) == obj.length, "File corrupt?"
        return cls(obj.items)


class FixedObjectByteArray(FixedObject):
    def __repr__(self):
        name = self.__class__.__name__
        value = repr(self.value)
        if len(value) > 60:
            value = value[:97] + '...'
            return "<%s(%s)>" % (name, value)
        else:
            return "%s(%s)" % (name, value)

# Bytes

class String(FixedObjectByteArray):
    classID = 9
    _construct = PascalString("value", length_field=UBInt32("length"))


class Symbol(FixedObjectByteArray):
    classID = 10
    _construct = PascalString("value", length_field=UBInt32("length"))
    def __repr__(self):
        return "Symbol(%r)" % self.value


class ByteArray(FixedObjectByteArray):
    classID = 11
    _construct = PascalString("value", length_field=UBInt32("length"))

    def __repr__(self):
        return '<%s(%i bytes)>' % (self.__class__.__name__, len(self.value))


class SoundBuffer(FixedObjectByteArray):
    classID = 12
    _construct = Struct("",
        UBInt32("length"),
        construct.String("items", lambda ctx: ctx.length * 2),
    )

    @classmethod
    def from_value(cls, obj):
        return cls(obj.items)

    def to_value(self):
        value = self.value
        length = (len(value) + 3) / 2
        value += "\x00" *  (length * 2  -  len(value)) # padding
        return Container(items = value, length = length)


# Bitmap 13 - found later in file

class UTF8(FixedObjectByteArray):
    classID = 14
    _construct = PascalString("value", length_field=UBInt32("length"),
                              encoding="utf8")




# Collections

class Collection(FixedObjectWithRepeater, ContainsRefs):
    _construct = Struct("",
        UBInt32("length"),
        MetaRepeater(lambda ctx: ctx.length, Rename("items", field)),
    )

    def __init__(self, value=None):
        if value == None:
            value = []
        FixedObject.__init__(self, value)

    def __iter__(self):
        return iter(self.value)

    def __getattr__(self, name):
        if name in ('append', 'count', 'extend', 'index', 'insert', 'pop',
                    'remove', 'reverse', 'sort'):
            return getattr(self.value, name)
        return super(Collection, self).__getattr__(name)

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __delitem__(self, index):
        del self.value[index]

    def __len__(self):
        return len(self.value)

    def copy(self):
        return self.__class__(list(self.value.copy))

class Array(Collection):
    classID = 20
class OrderedCollection(Collection):
    classID = 21
class Set(Collection):
    classID = 22
class IdentitySet(Collection):
    classID = 23



# Dictionary

class Dictionary(Collection):
    classID = 24
    _construct = Struct("dictionary",
        UBInt32("length"),
        MetaRepeater(lambda ctx: ctx.length, Struct("items",
            Rename("key", field),
            Rename("value", field),
        )),
    )

    def __init__(self, value=None):
        if value == None: value = {}
        Collection.__init__(self, value)

    def to_value(self):
        items = [Container(key=key, value=value)
                 for (key, value) in dict(self.value).items()]
        return Container(items=items, length=len(items))

    @classmethod
    def from_value(cls, obj):
        value = dict([(item.key, item.value) for item in obj.items])
        return cls(value)

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            return super(Dictionary, self).__getattr__(name)
        return getattr(self.value, name)

    def copy(self):
        return self.__class__(self.value.copy())

class IdentityDictionary(Dictionary):
    classID = 25



# Color

class Color(FixedObject):
    """A 32-bit RGB color value.
    Each component r, g, b has a value between 0 and 1023.

    However, Colors are considered equal if they have the same 8-bit value.
    """
    classID = 30
    _construct = BitStruct("value",
        Padding(2),
        Bits("r", 10),
        Bits("g", 10),
        Bits("b", 10),
    )

    _construct_32_rgba = Struct("",
        UBInt8("r"),
        UBInt8("g"),
        UBInt8("b"),
        UBInt8("alpha"),
    )

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return (
            isinstance(other, Color) and
            self.to_8bit() == other.to_8bit()
        )

    def __ne__(self, other):
        return not self == other

    @classmethod
    def from_value(cls, value):
        return cls((value.r, value.g, value.b))

    def to_value(self):
        (r, g, b) = self.value
        return Container(r=r, g=g, b=b)

    @classmethod
    def from_8bit(self, r, g=None, b=None):
        if g is None and b is None:
            rgb = r
        else:
            rgb = (r, g, b)

        return Color((x << 2 for x in rgb))

    def to_8bit(self):
        """Returns value with components between 0-255."""
        return tuple(x >> 2 for x in self.value)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            repr(self.value).strip("()"),
        )

    def to_rgba_array(self):
        (r, g, b) = self.to_8bit()
        return array('B', (r, g, b, 255))



class TranslucentColor(Color):
    classID = 31
    _construct = Struct("",
        Embed(Color._construct),
        UBInt8("alpha"), # I think.
    )
    _construct_32 = Struct("",
        UBInt8("alpha"),
        UBInt8("r"),
        UBInt8("g"),
        UBInt8("b"),
    )

    def __init__(self, value):
        self.value = value

    def to_value(self):
        (r, g, b, alpha) = self.value
        return Container(r=r, g=g, b=b, alpha=alpha)

    @classmethod
    def from_value(cls, value):
        return cls((value.r, value.g, value.b, value.alpha))

    @classmethod
    def from_32bit_raw_argb(cls, raw):
        container = cls._construct_32.parse(raw)
        parts = cls.from_value(container)
        color = cls(*(x << 2 for x in parts.value))
        if color.alpha == 0 and (color.r > 0 or color.g > 0 or color.b > 0):
            color.alpha = 1023
        return color

    def to_rgba_array(self):
        return array('B', self.to_8bit())




# Dimensions

class Point(FixedObject):
    classID = 32
    _construct = Struct("",
        Rename("x", field),
        Rename("y", field),
    )

    def __init__(self, x, y=None):
        if y is None: (x, y) = x
        self.x = x
        self.y = y

    @property
    def value(self):
        return (self.x, self.y)

    def __iter__(self):
        return iter(self.value)

    def __repr__(self):
        return 'Point(%r, %r)' % self.value

    def to_value(self):
        return Container(x = self.x, y = self.y)

    @classmethod
    def from_value(cls, value):
        return cls(value.x, value.y)

class Rectangle(FixedObject):
    classID = 33
    _construct = StrictRepeater(4, field)

    @classmethod
    def from_value(cls, value):
        value = list(value)
        return cls(value)




# Form/images

def get_run_length(ctx):
    try:
        return ctx.run_length
    except AttributeError:
        return ctx._.run_length

class Bitmap(FixedObjectByteArray):
    classID = 13
    _construct = Struct("",
        UBInt32("length"),
        construct.String("items", lambda ctx: ctx.length * 4),
        # Identically named "String" class -_-
    )

    @classmethod
    def from_value(cls, obj):
        return cls(obj.items)

    def to_value(self):
        value = self.value
        length = (len(value) + 3) / 4
        value += "\x00" *  (length * 4  -  len(value)) # padding
        return Container(items = value, length = length)

    _int = Struct("int",
        UBInt8("_value"),
        If(lambda ctx: ctx._value > 223,
            IfThenElse("", lambda ctx: ctx._value <= 254, Embed(Struct("",
                UBInt8("_second_byte"),
                Value("_value",
                    lambda ctx: (ctx._value - 224) * 256 + ctx._second_byte),
            )), Embed(Struct("",
                UBInt32("_value"),
            )))
        ),
    )

    _length_run_coding = Struct("",
        Embed(_int), #ERROR?
        Value("length", lambda ctx: ctx._value),

        OptionalGreedyRepeater(
            Struct("data",
                Embed(_int),
                Value("data_code", lambda ctx: ctx._value % 4),
                Value("run_length", lambda ctx:
                    (ctx._value - ctx.data_code) / 4),
                Switch("", lambda ctx: ctx.data_code, {
                    0: Embed(Struct("",
                        StrictRepeater(get_run_length,
                            Value("pixels", lambda ctx: "\x00\x00\x00\x00")
                        ),
                    )),
                    1: Embed(Struct("",
                        Bytes("_b", 1),
                        StrictRepeater(get_run_length,
                            Value("pixels", lambda ctx: ctx._b * 4),
                        ),
                    )),
                    2: Embed(Struct("",
                        Bytes("_pixel", 4),
                        StrictRepeater(get_run_length,
                            Value("pixels", lambda ctx: ctx._pixel),
                        ),
                    )),
                    3: Embed(Struct("",
                        StrictRepeater(get_run_length,
                            Bytes("pixels", 4),
                        ),
                    )),
                }),
            )
        )
    )

    @classmethod
    def from_byte_array(cls, bytes):
        """Decodes a run-length encoded ByteArray and returns a Bitmap.
        The ByteArray decompresses to a sequence of 32-bit values, which are
        stored as a byte string. (The specific encoding depends on Form.depth.)
        """
        runs = cls._length_run_coding.parse(bytes)
        data = ""
        for run in runs.data:
            for pixel in run.pixels:
                data += pixel
        return cls(data)


    def compress(self):
        """Compress to a ByteArray"""
        raise NotImplementedError



class Form(FixedObject, ContainsRefs):
    """A rectangular array of pixels, used for holding images.
    Attributes:
        width, height - dimensions
        depth - how many bits are used to specify the color at each pixel.
        bits - a Bitmap with varying internal structure, depending on depth.
        privateOffset - ?

    Note: do not modify the dict returned from the .value property.
    """

    classID = 34
    _construct = Struct("form",
        Rename("width", field),
        Rename("height", field),
        Rename("depth", field),
        Rename("privateOffset", field),
        Rename("bits", field), # Bitmap
    )

    def __init__(self, **fields):
        self.width = 0
        self.height = 0
        self.depth = None
        self.privateOffset = None
        self.bits = Bitmap("")
        self.colors = None

        self.__dict__.update(fields)

    @property
    def value(self):
        return dict((k, getattr(self, k)) for k in self.__dict__
                    if not k.startswith("_"))

    def to_value(self):
        return Container(**self.value)

    @classmethod
    def from_value(cls, value):
        return cls(**dict(value))

    def copy(self):
        return self.__class__.from_value(self.to_value())

    def __repr__(self):
        return "<%s(%ix%i)>" % (
            self.__class__.__name__,
            self.width, self.height,
        )

    def built(self):
        if isinstance(self.bits, ByteArray):
            self.bits = Bitmap.from_byte_array(self.bits.value)
        assert isinstance(self.bits, Bitmap)

    def _to_pixels(self):
        pixel_bytes = self.bits.value
        if self.depth == 32:
            for i in range(0, len(pixel_bytes), 4):
                (a, r, g, b) = (ord(x) for x in pixel_bytes[i:i+4])
                if a == 0 and (r > 0 or g > 0 or b > 0):
                    a = 255
                yield array("B", (r, g, b, a))

        elif self.depth == 16:
            raise NotImplementedError # TODO: depth 16

        elif self.depth <= 8:
            if self.colors:
                colors = [color.to_rgba_array() for color in self.colors]
            else:
                colors = default_colormap()
            length = len(pixel_bytes) * 8 / self.depth
            repeater = MetaRepeater(length, Bits("pixels", self.depth))
            pixels_construct = BitStruct("", repeater)
            for pixel in pixels_construct.parse(pixel_bytes).pixels:
                yield colors[pixel]

    def to_array(self):
        rgba = array('B') #unsigned byte
        pixel_count = 0
        num_pixels = self.width * self.height

        # Rows are rounded to be a whole number of words (32 bits) long.
        # Presumably this is because Bitmaps are compressed (run-length encoded)
        # in 32-bit segments.
        skip = 0
        if self.depth <= 8:
            pixels_per_word = 32 / self.depth
            pixels_in_last_word = self.width % pixels_per_word
            skip = (pixels_per_word - pixels_in_last_word) % pixels_per_word

        x = 0
        pixels = self._to_pixels()
        while 1:
            try:
                color = pixels.next()
            except StopIteration:
                break

            rgba.extend(color)

            pixel_count += 1
            x += 1
            if x >= self.width:
                for i in xrange(skip):
                    pixel = pixels.next()
                x = 0

        length = self.width * self.height * 4
        blank = array("B", (0, 0, 0, 0))
        while len(rgba) < length:
            rgba.extend(blank)

        assert len(rgba) == length

        return (self.width, self.height, rgba)

    @classmethod
    def from_string(cls, width, height, rgba_string):
        """Returns a Form with 32-bit RGBA pixels
        Accepts string containing raw RGBA color values
        """
        # Convert RGBA string to ARGB
        raw = ""
        for i in range(0, len(rgba_string), 4):
            raw += rgba_string[i+3]   # alpha
            raw += rgba_string[i:i+3] # rgb

        assert len(rgba_string) == width * height * 4

        return Form(
            width = width,
            height = height,
            depth = 32,
            bits = Bitmap(raw),
        )

    @classmethod
    def from_array(cls, width, height, rgba_array):
        """Returns a Form with 32-bit RGBA pixels
        Accepts sequence of flattened r, g, b, a, r, g, b, a ... values for
        each pixel
        """
        # Unused now
        raw = ""
        for i in range(0, len(rgba_array), 4):
            (r, g, b, a) = (chr(x) for x in rgba_array[i:i+4])
            raw += "".join((a, r, g, b))

        return Form(
            width = width,
            height = height,
            depth = 32,
            bits = Bitmap(raw),
        )


class ColorForm(Form):
    """A rectangular array of pixels, used for holding images.
    width, height - dimensions
    depth - how many bits are used to specify the color at each pixel.
    bits - a Bitmap with varying internal structure, depending on depth.
    colors - the colors pointed to by the bits array. (I think?)
    privateOffset - ?
    """
    classID = 35
    _construct = Struct("",
        Embed(Form._construct),
        Rename("colors", field), # Array
    )







