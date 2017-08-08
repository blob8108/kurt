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

"""Inline values - such as nil, boolean, int - and references."""

from construct import *
from construct import Array as MetaRepeater
# We can't import the name Array, as we use it. -_-


### Inline fields & Refs ###

class Ref(object):
    """A reference to an object located in a serialized object table.

    Used internally for parsing object tables. Allows for complex interlinked
    object networks to be serialized to a list of objects.

    Found in UserObjects and certain FixedObjects.

    """

    def __init__(self, index):
        """Initialise a reference.
        @param index: the index in the object table that the reference points to
        Note that the first index is 1.
        """
        self.index = int(index)

    def to_construct(self):
        #index1 = self.index % 65536
        #index2 = (self.index - index1) >> 16
        # return Container(classID = 'Ref', _index1 = index1, _index2 = index2)
        return Container(classID="Ref", index=self.index)

    @classmethod
    def from_construct(cls, obj):
        index = obj.index  # int(obj._index2 << 16) + obj._index1
        return Ref(index)

    def __repr__(self):
        return 'Ref(%i)' % self.index

    def __eq__(self, other):
        return isinstance(other, Ref) and self.index == other.index

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.index)


class RefAdapter(Adapter):

    def _encode(self, obj, context):
        assert isinstance(obj, Ref)
        return obj.to_construct()

    def _decode(self, obj, context):
        return Ref.from_construct(obj)


class LargeIntegerAdapter(Adapter):

    def __init__(self, sign, *args, **kwargs):
        self.sign = sign
        Adapter.__init__(self, *args, **kwargs)

    def _decode(self, obj, context):
        value = 0
        for x in reversed(obj.data):
            value <<= 8
            value += x
        if self.sign == '-':
            value = -value
        return value

    def _encode(self, obj, context):
        bytes = []
        while obj:
            bytes.append(obj & 0xff)
            obj >>= 8
        return Container(length=len(bytes), data=bytes)


class FieldAdapter(Adapter):

    def _encode(self, obj, context):
        assert not isinstance(obj, str)

        if obj is None:
            classID = 'nil'
        elif obj is True:
            classID = 'true'
        elif obj is False:
            classID = 'false'
        elif isinstance(obj, float):
            classID = 'Float'
        elif isinstance(obj, Ref):
            classID = 'Ref'
        elif isinstance(obj, int) or isinstance(obj, long):
            if -32768 <= obj <= 32767:
                classID = 'SmallInteger16'
            elif -2147483648 <= obj <= 2147483647:
                classID = 'SmallInteger'
            elif obj >= 0:
                classID = 'LargePositiveInteger'
            else:
                classID = 'LargeNegativeInteger'
        else:
            raise NotImplementedError, 'no field type for %r' % obj
        return Container(classID=classID, value=obj)

    def _decode(self, obj, context):
        if isinstance(obj, Ref):
            return obj
        else:
            return obj.value


"""Construct for simple inline field values and references.

They are encoded inline and not stored as object table entries. They do not
contain references (though they may *be* references).

"""
field = FieldAdapter(Struct("field",
                            Enum(UBInt8("classID"),
                                 nil=1,
                                 true=2,
                                 false=3,
                                 SmallInteger=4,
                                 SmallInteger16=5,
                                 LargePositiveInteger=6,
                                 LargeNegativeInteger=7,
                                 Float=8,
                                 Ref=99,
                                 ),
                            Switch("value", lambda ctx: ctx.classID, {
                                "nil": Value("", lambda ctx: None),
                                "true": Value("", lambda ctx: True),
                                "false": Value("", lambda ctx: False),
                                "SmallInteger": SBInt32(""),
                                "SmallInteger16": SBInt16(""),
                                "LargePositiveInteger": LargeIntegerAdapter('+', Struct("",
                                                                                        UBInt16(
                                                                                            "length"),
                                                                                        MetaRepeater(
                                                                                            lambda ctx: ctx.length, UBInt8("data")),
                                                                                        )),
                                "LargeNegativeInteger": LargeIntegerAdapter('-', Struct("",
                                                                                        UBInt16(
                                                                                            "length"),
                                                                                        MetaRepeater(
                                                                                            lambda ctx: ctx.length, UBInt8("data")),
                                                                                        )),
                                "Float": BFloat64(""),
                                "Ref": RefAdapter(BitStruct("",
                                                            BitField(
                                                                "index", 24),
                                                            )),
                            })
                            ))
