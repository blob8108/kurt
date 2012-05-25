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


def default_colormap(depth):
    full = 2**depth - 1
    half = full / 2
    quarter = full / 4
    eighth = full / 8
    three_eighths = full * 3 / 8
    five_eighths = full * 5 / 8
    three_quarters = full * 3 / 4
    seven_eighths = full * 7 / 8

    # This generation comes from the sqeuak source under initializeIndexColors
    colormap = []
    # 1-bit colors
    colormap.append((full, full, full, full))
    colormap.append((0.0, 0.0, 0.0, full))
    # additional 2-bit colors
    colormap.append((full, full, full, full))
    colormap.append((half, half, half, full))
    # additional 4-bit colors
    colormap.append((full, 0.0, 0.0, full))
    colormap.append((0.0, full, 0.0, full))
    colormap.append((0.0, 0.0, full, full))
    colormap.append((0.0, full, full, full))
    colormap.append((full, full, 0.0, full))
    colormap.append((full, 0.0, full, full))
    colormap.append((eighth, eighth, eighth, full))
    colormap.append((quarter, quarter, quarter, full))
    colormap.append((three_eighths, three_eighths, three_eighths, full))
    colormap.append((five_eighths, five_eighths, five_eighths, full))
    colormap.append((three_quarters, three_quarters, three_quarters, full))
    colormap.append((seven_eighths, seven_eighths, seven_eighths, full))
    # additional 8-bit colors
    for i in range(32):  # 24 more shades of gray
        if i % 4 == 0:
            continue
        value = full * i / 32
        colormap.append((value, value, value, full))
    for red in range(6):  # Color "cube" with six steps for each primary color
        for blue in range(6):
            for green in range(6):
                colormap.append((full * red / 5,
                                 full * green / 5,
                                 full * blue / 5,
                                 full))
    return colormap


class FixedObject(object):
    """A primitive fixed-format object - eg String, Dictionary.
    value property - contains the object's value."""
    def __init__(self, value):
        self.value = value
    
    def to_construct(self, context):
        return Container(classID = self.__class__.__name__, value = self.to_value())
    
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
    _construct = PascalString("value", length_field=UBInt32("length"), encoding="utf8")




# Collections

class Collection(FixedObjectWithRepeater, ContainsRefs):
    _construct = Struct("",
        UBInt32("length"),
        MetaRepeater(lambda ctx: ctx.length, Rename("items", Field)),
    )
    
    def __init__(self, value=None):
        if value == None:
            value = []
        FixedObject.__init__(self, value)
    
    def __iter__(self):
        return iter(self.value)
    
    def __getattr__(self, name):
        if name in ('append', 'count', 'extend', 'index', 'insert', 'pop', 'remove', 'reverse', 'sort'):
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
    
    def __init__(self, value=None):
        if value == None: value = {}
        Collection.__init__(self, value)
    
    def to_value(self):
        items = [Container(key=key, value=value) for (key, value) in dict(self.value).items()]
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
    
    _construct_32_rgba = Struct("",
        UBInt8("r"),
        UBInt8("g"),
        UBInt8("b"),
        UBInt8("alpha"),
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
    
    def to_rgba_array(self):
        (r, g, b) = self.to_8bit()
        return array('B', (r, g, b, 255))
    
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
    def from_32bit_raw_argb(cls, raw):
        container = cls._construct_32.parse(raw)
        parts = cls.from_value(container)
        color = cls(*(x << 2 for x in parts.value))
        if color.alpha == 0 and (color.r > 0 or color.g > 0 or color.b > 0):
            color.alpha = 1023
        return color
    
    def to_rgba_array(self):
        return array('B', self.to_8bit())
    
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
    
    def __iter__(self):
        return iter(self.value)
    
    def __repr__(self):
        return 'Point(%r, %r)' % self.value
    
    def to_value(self):
        return Container(x = self.x, y = self.y)
    
    @classmethod
    def from_value(cls, value):
        return cls(value.x, value.y)
    
    @classmethod
    def from_string(cls, string):
        (x, y) = string.split(",")
        return cls(float(x), float(y))

class Rectangle(FixedObject):
    classID = 33
    _construct = StrictRepeater(4, Field)
    
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

class Bitmap(FixedObjectByteArray, FixedObjectWithRepeater):
    classID = 13
    _construct = Struct("",
        UBInt32("length"),
        construct.String("items", lambda ctx: ctx.length * 4, padchar="\x00", paddir="right"),
        # Identically named "String" class -_-
    )
        
    @classmethod
    def from_value(cls, obj):
        return cls(obj.items)

    def to_value(self):
        return Container(items = self.value, length = (len(self.value) + 2) / 4)
    
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
        The ByteArray decompresses to a sequence of 32-bit values, which are stored as 
        a byte string. (The specific encoding depends on Form.depth.)
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
        return dict((k, getattr(self, k)) for k in self.__dict__ if not k.startswith("_"))
    
    def to_value(self):
        return Container(**self.value)
    
    @classmethod
    def from_value(cls, value):
        return cls(**dict(value))
    
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
                colors = default_colormap(self.depth)
            length = len(pixel_bytes) * 8 / self.depth
            repeater = MetaRepeater(length, Bits("pixels", self.depth))
            pixels_construct = BitStruct("", repeater)
            for pixel in pixels_construct.parse(pixel_bytes).pixels:
                yield colors[pixel]
    
    def to_array(self):
        rgba = array('B') #unsigned byte
        pixel_count = 0
        num_pixels = self.width * self.height

        # Rows are rounded to be a whole number of words (32 bits) long.  I
        # *think* this is because Bitmaps are run-length encoded in 32-bit
        # segments.
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
        
        return (self.width, self.height, rgba)
    
    def save_png(self, path):
        if not path.endswith(".png"): path += ".png"
        
        if not png:
            raise ValueError, "Missing dependency: pypng library needed for PNG support"
        
        f = open(path, "wb")
        (width, height, rgba_array) = self.to_array()
        writer = png.Writer(width, height, alpha=True)
        writer.write_array(f, rgba_array)
        f.flush()
        f.close()

    @classmethod
    def from_array(cls, width, height, rgba_array):
        """Returns a Form with 32-bit RGBA pixels"""
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
    
    @classmethod
    def load_png(cls, path):
        reader = png.Reader(filename=path)
        (width, height, color_array, metadata) = reader.read_flat()
        if metadata["bitdepth"] != 8:
            raise ValueError("Only PNG images with depth 8 are supported")

        rgba_array = array('B')
        pixel_size = 4 if metadata["alpha"] else 3
        for i in range(0, len(color_array), pixel_size):
            rgba_array += color_array[i:i+pixel_size]
            if not metadata["alpha"]:
                rgba_array += 255

        return cls.from_array(width, height, rgba_array)


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


        




