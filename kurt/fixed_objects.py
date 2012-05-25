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
# You should have received a copy of the GNU Lesser General Public License
# along with Kurt. If not, see <http://www.gnu.org/licenses/>.

"""Primitive fixed-format objects - eg String, Dictionary."""

from construct import Container, Struct, Embed, Rename
from construct import PascalString, UBInt32, SBInt32, UBInt16, UBInt8, Bytes
from construct import BitStruct, Padding, Bits
from construct import Value, Switch, If, IfThenElse, OptionalGreedyRepeater
from construct import Array as StrictRepeater, Array as MetaRepeater
# We can't import the name Array, as we use it. -_-
import construct

# used by Form
from array import array
try:
    import png
except ImportError:
    png = None

from inline_objects import Field



class FixedObject(object):
    """A primitive fixed-format object - eg String, Dictionary.
    value property - contains the object's value."""
    def __init__(self, value):
        self.value = value

    def to_construct(self, context):
        return Container(classID = self.__class__.__name__,
                         value = self.to_value())

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
        return "<#%s>" % self.value


class ByteArray(FixedObjectByteArray):
    classID = 11
    _construct = PascalString("value", length_field=UBInt32("length"))

    def __repr__(self):
        return '<%s(%i bytes)>' % (self.__class__.__name__, len(self.value))


class SoundBuffer(FixedObjectByteArray, FixedObjectWithRepeater):
    classID = 12
    _construct = Struct("",
        UBInt32("length"),
        MetaRepeater(lambda ctx: ctx.length, UBInt16("items")),
    )

# Bitmap 13 - found later in file

class UTF8(FixedObjectByteArray):
    classID = 14
    _construct = PascalString("value", length_field=UBInt32("length"),
                              encoding="utf8")




# Collections

class Collection(FixedObjectWithRepeater, ContainsRefs):
    _construct = Struct("",
        UBInt32("length"),
        MetaRepeater(lambda ctx: ctx.length, Rename("items", Field)),
    )

    def __iter__(self):
        return iter(self.value)

    def __getattr__(self, name):
        if name in ('append', 'count', 'extend', 'index', 'insert', 'pop',
                    'remove', 'reverse', 'sort'):
            return getattr(self.value, name)

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __delitem__(self, index):
        del self.value[index]

    def __len__(self):
        return len(self.value)

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
            Rename("key", Field),
            Rename("value", Field),
        )),
    )

    def to_value(self):
        items = [Container(key=key, value=value) for (key, value)
                 in dict(self.value).items()]
        return Container(items=items, length=len(items))

    @classmethod
    def from_value(cls, obj):
        value = dict([(item.key, item.value) for item in obj.items])
        return cls(value)

    def __getattr__(self, name):
        return getattr(self.value, name)

class IdentityDictionary(Dictionary):
    classID = 25



# Color

class Color(FixedObject):
    """A 32-bit RGB color value.
    Each component r, g, b has a value between 0 and 1023.
    """
    classID = 30
    _construct = BitStruct("value",
        Padding(2),
        Bits("r", 10),
        Bits("g", 10),
        Bits("b", 10),
    )

    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def to_value(self):
        return Container(r=self.r, g=self.g, b=self.b)

    @classmethod
    def from_value(cls, value):
        return cls(value.r, value.g, value.b)

    @property
    def value(self):
        return (self.r, self.g, self.b)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            repr(self.value).strip("()"),
        )

    def to_8bit(self):
        """Returns value with components between 0-256."""
        return tuple(x >> 2 for x in self.value)

    def hexcode(self):
        """Returns the color value in hex/HTML format.
        eg "ff1056".
        """
        hexcode = ""
        for x in self.to_8bit():
            part = hex(x)[2:]
            if len(part) < 2: part = "0" + part
            hexcode += part
        return hexcode


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

    def __init__(self, r, g, b, alpha):
        self.r = r
        self.g = g
        self.b = b
        self.alpha = alpha

    def to_value(self):
        return Container(r=self.r, g=self.g, b=self.b, alpha=self.alpha)

    @classmethod
    def from_value(cls, value):
        return cls(value.r, value.g, value.b, value.alpha)

    @classmethod
    def from_32bit_raw(cls, raw):
        container = cls._construct_32.parse(raw)
        parts = cls.from_value(container)
        color = cls(*(x << 2 for x in parts.value))
        if color.alpha == 0 and (color.r > 0 or color.g > 0 or color.b > 0):
            color.alpha = 1023
        return color

    @property
    def value(self):
        return (self.r, self.g, self.b, self.alpha)

    def hexcode(self, include_alpha=True):
        """Returns the color value in hex/HTML format.
        eg "ff1056ff".
        Argument include_alpha: default True.
        """
        hexcode = Color.hexcode(self)
        if not include_alpha: hexcode = hexcode[:-2]
        return hexcode



# Dimensions

class Point(FixedObject):
    classID = 32
    _construct = Struct("",
        Rename("x", Field),
        Rename("y", Field),
    )

    def __init__(self, x, y=None):
        if y is None: (x, y) = x
        self.x = x
        self.y = y

    @property
    def value(self):
        return (self.x, self.y)

    def __repr__(self):
        return 'Point(%r, %r)' % self.value

    def to_value(self):
        return Container(x = self.x, y = self.y)

    @classmethod
    def from_value(cls, value):
        return cls(value.x, value.y)

class Rectangle(FixedObject):
    classID = 33
    _construct = StrictRepeater(4, Field)




# Form/images

def get_run_length(ctx):
    try:
        return ctx.run_length
    except AttributeError:
        return ctx._.run_length

class Bitmap(FixedObjectByteArray, FixedObjectWithRepeater):
    classID = 13
    _construct = Struct("",
        UBInt32("length"),
        construct.String("items", lambda ctx: ctx.length * 4, padchar="\x00",
                         paddir="right"),
        # Identically named "String" class -_-
    )

    @classmethod
    def from_value(cls, obj):
        return cls(obj.items)

    def to_value(self):
        return Container(items=self.value, length=(len(self.value) + 2) / 4)

    _int = Struct("int",
        UBInt8("_value"),
        If(lambda ctx: ctx._value > 223,
            IfThenElse("", lambda ctx: ctx._value <= 254, Embed(Struct("",
                UBInt8("_second_byte"),
                Value("_value", lambda ctx: (ctx._value - 224) * 256 + ctx._second_byte),
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
                Value("run_length", lambda ctx: (ctx._value - ctx.data_code) / 4),
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
        Rename("width", Field),
        Rename("height", Field),
        Rename("depth", Field),
        Rename("privateOffset", Field),
        Rename("bits", Field), # Bitmap
    )

    # TODO: default color values
    #_squeak_colors = [-1, -1, -1, 0, 0, 0, -1, -1, -1, -128, -128, -128, -1, 0, 0, 0, -1, 0, 0, 0, -1, 0, -1, -1, -1, -1, 0, -1, 0, -1, 32, 32, 32, 64, 64, 64, 96, 96, 96, -97, -97, -97, -65, -65, -65, -33, -33, -33, 8, 8, 8, 16, 16, 16, 24, 24, 24, 40, 40, 40, 48, 48, 48, 56, 56, 56, 72, 72, 72, 80, 80, 80, 88, 88, 88, 104, 104, 104, 112, 112, 112, 120, 120, 120, -121, -121, -121, -113, -113, -113, -105, -105, -105, -89, -89, -89, -81, -81, -81, -73, -73, -73, -57, -57, -57, -49, -49, -49, -41, -41, -41, -25, -25, -25, -17, -17, -17, -9, -9, -9, 0, 0, 0, 0, 51, 0, 0, 102, 0, 0, -103, 0, 0, -52, 0, 0, -1, 0, 0, 0, 51, 0, 51, 51, 0, 102, 51, 0, -103, 51, 0, -52, 51, 0, -1, 51, 0, 0, 102, 0, 51, 102, 0, 102, 102, 0, -103, 102, 0, -52, 102, 0, -1, 102, 0, 0, -103, 0, 51, -103, 0, 102, -103, 0, -103, -103, 0, -52, -103, 0, -1, -103, 0, 0, -52, 0, 51, -52, 0, 102, -52, 0, -103, -52, 0, -52, -52, 0, -1, -52, 0, 0, -1, 0, 51, -1, 0, 102, -1, 0, -103, -1, 0, -52, -1, 0, -1, -1, 51, 0, 0, 51, 51, 0, 51, 102, 0, 51, -103, 0, 51, -52, 0, 51, -1, 0, 51, 0, 51, 51, 51, 51, 51, 102, 51, 51, -103, 51, 51, -52, 51, 51, -1, 51, 51, 0, 102, 51, 51, 102, 51, 102, 102, 51, -103, 102, 51, -52, 102, 51, -1, 102, 51, 0, -103, 51, 51, -103, 51, 102, -103, 51, -103, -103, 51, -52, -103, 51, -1, -103, 51, 0, -52, 51, 51, -52, 51, 102, -52, 51, -103, -52, 51, -52, -52, 51, -1, -52, 51, 0, -1, 51, 51, -1, 51, 102, -1, 51, -103, -1, 51, -52, -1, 51, -1, -1, 102, 0, 0, 102, 51, 0, 102, 102, 0, 102, -103, 0, 102, -52, 0, 102, -1, 0, 102, 0, 51, 102, 51, 51, 102, 102, 51, 102, -103, 51, 102, -52, 51, 102, -1, 51, 102, 0, 102, 102, 51, 102, 102, 102, 102, 102, -103, 102, 102, -52, 102, 102, -1, 102, 102, 0, -103, 102, 51, -103, 102, 102, -103, 102, -103, -103, 102, -52, -103, 102, -1, -103, 102, 0, -52, 102, 51, -52, 102, 102, -52, 102, -103, -52, 102, -52, -52, 102, -1, -52, 102, 0, -1, 102, 51, -1, 102, 102, -1, 102, -103, -1, 102, -52, -1, 102, -1, -1, -103, 0, 0, -103, 51, 0, -103, 102, 0, -103, -103, 0, -103, -52, 0, -103, -1, 0, -103, 0, 51, -103, 51, 51, -103, 102, 51, -103, -103, 51, -103, -52, 51, -103, -1, 51, -103, 0, 102, -103, 51, 102, -103, 102, 102, -103, -103, 102, -103, -52, 102, -103, -1, 102, -103, 0, -103, -103, 51, -103, -103, 102, -103, -103, -103, -103, -103, -52, -103, -103, -1, -103, -103, 0, -52, -103, 51, -52, -103, 102, -52, -103, -103, -52, -103, -52, -52, -103, -1, -52, -103, 0, -1, -103, 51, -1, -103, 102, -1, -103, -103, -1, -103, -52, -1, -103, -1, -1, -52, 0, 0, -52, 51, 0, -52, 102, 0, -52, -103, 0, -52, -52, 0, -52, -1, 0, -52, 0, 51, -52, 51, 51, -52, 102, 51, -52, -103, 51, -52, -52, 51, -52, -1, 51, -52, 0, 102, -52, 51, 102, -52, 102, 102, -52, -103, 102, -52, -52, 102, -52, -1, 102, -52, 0, -103, -52, 51, -103, -52, 102, -103, -52, -103, -103, -52, -52, -103, -52, -1, -103, -52, 0, -52, -52, 51, -52, -52, 102, -52, -52, -103, -52, -52, -52, -52, -52, -1, -52, -52, 0, -1, -52, 51, -1, -52, 102, -1, -52, -103, -1, -52, -52, -1, -52, -1, -1, -1, 0, 0, -1, 51, 0, -1, 102, 0, -1, -103, 0, -1, -52, 0, -1, -1, 0, -1, 0, 51, -1, 51, 51, -1, 102, 51, -1, -103, 51, -1, -52, 51, -1, -1, 51, -1, 0, 102, -1, 51, 102, -1, 102, 102, -1, -103, 102, -1, -52, 102, -1, -1, 102, -1, 0, -103, -1, 51, -103, -1, 102, -103, -1, -103, -103, -1, -52, -103, -1, -1, -103, -1, 0, -52, -1, 51, -52, -1, 102, -52, -1, -103, -52, -1, -52, -52, -1, -1, -52, -1, 0, -1, -1, 51, -1, -1, 102, -1, -1, -103, -1, -1, -52, -1, -1, -1, -1]
    #_squeak_colors = [_squeak_colors[i:i+4] for i in range(0, len(_squeak_colors), 4)]

    @property
    def value(self):
        return dict((k, getattr(self, k)) for k in self.__dict__
                    if not k.startswith("_"))

    def to_value(self):
        return Container(**self.value)

    @classmethod
    def from_value(cls, value):
        return cls(**dict(value))

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        return "<%s(%ix%i)>" % (self.__class__.__name__,
                                self.width, self.height)

    def built(self):
        if isinstance(self.bits, ByteArray):
            self.bits = Bitmap.from_byte_array(self.bits.value)
        assert isinstance(self.bits, Bitmap)

    def _to_pixels(self):
        pixel_bytes = self.bits.value
        if self.depth == 32:
            for pixel in (pixel_bytes[i:i+4] for i
                          in range(0, len(pixel_bytes), 4)):
                color = TranslucentColor.from_32bit_raw(pixel)
                yield color
        elif self.depth == 16:
            raise NotImplementedError # TODO: depth 16
        elif self.depth <= 8:
            if not hasattr(self, 'colors') or not self.colors:
                raise NotImplementedError("TODO: default color values")
                # default color values are found in squeak_colors
            length = len(pixel_bytes) * 8 / self.depth
            pixels_construct = BitStruct(
                "", MetaRepeater(length, Bits("pixels", self.depth), ), )
            pixels = pixels_construct.parse(pixel_bytes).pixels
            for pixel in pixels:
                yield self.colors[pixel]

    def to_array(self):
        rgba = array('B')
        for pixel in self._to_pixels():
            for color in pixel.to_8bit():
                rgba.append(color)
            if not isinstance(pixel, TranslucentColor):
                rgba.append(255)  # Add alpha channel
        return self.width, self.height, rgba

    def save_png(self, path):
        if not png:
            raise ValueError('Missing dependency: pypng library needed '
                             'for PNG support')
        if not path.endswith(".png"): path += ".png"
        f = open(path, "wb")
        (width, height, rgb_array) = self.to_array()
        writer = png.Writer(width, height, alpha=True)
        writer.write_array(f, rgb_array)
        f.flush()
        f.close()


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
        Rename("colors", Field), # Array
    )
