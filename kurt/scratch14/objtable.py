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

"""ObjTable - for de/serialising an object and its related objects.

(You probably want to use the classes in kurt.files directly.)

Otherwise, the main class in this file is ObjTable.
"""

from construct import *
from construct.text import Literal
from functools import partial
import inspect

from fixed_objects import *
import fixed_objects
from inline_objects import field, Ref
from user_objects import *


class ObjectAdapter(Adapter):
    """Decodes a construct to a pythonic class representation.
    The class must have a from_construct classmethod and a to_construct
    instancemethod.
    """

    def __init__(self, classes, *args, **kwargs):
        """Initialize an adapter for a new type/object(s).
        @param classes: class, list of classes, or dict of obj.class name to
        class mapping.
            eg ObjectAdapter({"String": String, "Array": Collection}, <subcon>)
        Note: Must use new-style objects, ie. subclasses of object.
        """
        Adapter.__init__(self, *args, **kwargs)

        if isinstance(classes, list):
            classes = dict((cls.__name__, cls) for cls in classes)
        self.classes = classes

    def _get_class(self, classID):
        if inspect.isclass(self.classes):
            return self.classes
        else:
            return self.classes[classID]

    def _encode(self, obj, context):
        """Encodes a class to a lower-level object using the class' own
        to_construct function.
        If no such function is defined, returns the object unchanged.
        """
        func = getattr(obj, 'to_construct', None)
        if callable(func):
            return func(context)
        else:
            return obj

    def _decode(self, obj, context):
        """Initialises a new Python class from a construct using the mapping
        passed to the adapter.
        """
        cls = self._get_class(obj.classID)
        return cls.from_construct(obj, context)


#-- Get object classes --#

def obj_classes_from_module(module):
    """Return a list of classes in a module that have a 'classID' attribute."""
    for name in dir(module):
        if not name.startswith('_'):
            cls = getattr(module, name)
            if getattr(cls, 'classID', None):
                yield (name, cls)

# Fixed-format objects

fixed_object_classes = []
fixed_object_ids_by_name = {}
fixed_object_cons_by_name = {}

for (name, cls) in obj_classes_from_module(fixed_objects):
    fixed_object_classes.append(cls)
    fixed_object_ids_by_name[name] = cls.classID
    fixed_object_cons_by_name[name] = cls._construct

FixedObjectAdapter = partial(ObjectAdapter, fixed_object_classes)

"""Construct for FixedObjects.

Stored in the object table. May contain references.

"""
fixed_object = FixedObjectAdapter(Struct("fixed_object",
                                         Enum(
                                             UBInt8("classID"), **fixed_object_ids_by_name),
                                         Switch(
                                             "value", lambda ctx: ctx.classID, fixed_object_cons_by_name),
                                         ))

# User-class objects

user_object_ids_by_name = dict((v, k) for (k, v)
                               in user_object_class_ids.items())

uo_struct = Struct("user_object",
                   Enum(UBInt8("classID"),
                        **user_object_ids_by_name
                        ),
                   UBInt8("version"),
                   UBInt8("length"),
                   Rename(
                       "values", MetaRepeater(lambda ctx: ctx.length, field)),
                   )

"""Construct for UserObjects.

Stored in the object table. May contain references.
"""
user_object = uo_struct


#-- Object Table --#

class PythonicAdapter(Adapter):
    """Converts from FixedObject classes to native Python types.
    * String -- python str
    * UTF8 -- python unicode
    * Dictionary -- dict
    * Array -- list/tuple
    """

    def _encode(self, obj, context):
        if isinstance(obj, str):
            return String(obj)
        elif isinstance(obj, unicode):
            return UTF8(obj)
        elif isinstance(obj, dict):
            return Dictionary(obj)
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return Array(obj)
        else:
            return obj

    def _decode(self, obj, context):
        if isinstance(obj, String):
            return str(obj.value)
        elif isinstance(obj, UTF8):
            return unicode(obj.value)
        elif isinstance(obj, Dictionary):
            return obj.value
        elif isinstance(obj, Array):
            return obj.value
        else:
            return obj


class ObjectAdapter(Adapter):

    def _encode(self, obj, context):
        classID = getattr(obj, 'classID', getattr(obj, 'classID'))
        if classID in fixed_object_ids_by_name:
            classID = fixed_object_ids_by_name[classID]
        elif classID in user_object_ids_by_name:
            classID = user_object_ids_by_name[classID]
        return Container(
            classID=classID,
            object=obj,
        )

    def _decode(self, obj, context):
        if hasattr(obj, 'object'):
            return obj.object
        return obj

obj_table_entry = PythonicAdapter(ObjectAdapter(Struct("object",
                                                       Peek(UBInt8("classID")),
                                                       IfThenElse("object", lambda ctx: ctx.classID < 99,
                                                                  fixed_object,
                                                                  user_object,
                                                                  ),
                                                       )))
obj_table_entry.__doc__ = """Construct for object table entries, both
    UserObjects and FixedObjects."""


class ObjectTableAdapter(Adapter):

    def _encode(self, objects, context):
        return Container(
            header="ObjS\x01Stch\x01",
            length=len(objects),
            objects=objects,
        )

    def _decode(self, table, context):
        assert table.length == len(table.objects), "File corrupt?"
        return table.objects

"""Construct for parsing a binary object table.

Includes "ObjS\\x01Stch\\x01" header.

"""
obj_table = ObjectTableAdapter(Struct("object_table",
                                      Const(
                                          Bytes("header", 10), "ObjS\x01Stch\x01"),
                                      UBInt32("length"),
                                      Rename(
                                          "objects", MetaRepeater(lambda ctx: ctx.length, obj_table_entry)),
                                      ))


class InfoTableAdapter(Subconstruct):
    """Info ObjTable found in the project header.
    Adds the preceding info_size header (4 bytes).

    Parses to a Dictionary.

    """

    info_size = UBInt32("info_size")

    def _parse(self, stream, context):
        self.info_size._parse(stream, Container())
        objtable = self.subcon._parse(stream, context)
        return objtable

    def _build(self, obj, stream, context):
        bytes = self.subcon.build(obj)
        size = len(bytes)
        stream.write(self.info_size.build(size))
        stream.write(bytes)

info_table = InfoTableAdapter(obj_table)

scratch_file = Struct("scratch_file",
                      Literal("ScratchV02"),
                      Rename("info", info_table),
                      Rename("stage", obj_table),
                      )


#-- object network to/from table --#

def decode_network(objects):
    """Return root object from ref-containing obj table entries"""
    def resolve_ref(obj, objects=objects):
        if isinstance(obj, Ref):
            # first entry is 1
            return objects[obj.index - 1]
        else:
            return obj

    # Reading the ObjTable backwards somehow makes more sense.
    for i in xrange(len(objects) - 1, -1, -1):
        obj = objects[i]

        if isinstance(obj, Container):
            obj.update((k, resolve_ref(v)) for (k, v) in obj.items())

        elif isinstance(obj, Dictionary):
            obj.value = dict(
                (resolve_ref(field), resolve_ref(value))
                for (field, value) in obj.value.items()
            )

        elif isinstance(obj, dict):
            obj = dict(
                (resolve_ref(field), resolve_ref(value))
                for (field, value) in obj.items()
            )

        elif isinstance(obj, list):
            obj = [resolve_ref(field) for field in obj]

        elif isinstance(obj, Form):
            for field in obj.value:
                value = getattr(obj, field)
                value = resolve_ref(value)
                setattr(obj, field, value)

        elif isinstance(obj, ContainsRefs):
            obj.value = [resolve_ref(field) for field in obj.value]

        objects[i] = obj

    for obj in objects:
        if isinstance(obj, Form):
            obj.built()

    root = objects[0]
    return root


def encode_network(root):
    """Yield ref-containing obj table entries from object network"""
    orig_objects = []
    objects = []

    def get_ref(value, objects=objects):
        """Returns the index of the given object in the object table,
        adding it if needed.

        """
        value = PythonicAdapter(Pass)._encode(value, None)
        # Convert strs to FixedObjects here to make sure they get encoded
        # correctly

        if isinstance(value, (Container, FixedObject)):
            if getattr(value, '_tmp_index', None):
                index = value._tmp_index
            else:
                objects.append(value)
                index = len(objects)
                value._tmp_index = index
                orig_objects.append(value)  # save the object so we can
                # strip the _tmp_indexes later
            return Ref(index)
        else:
            return value  # Inline value

    def fix_fields(obj):
        obj = PythonicAdapter(Pass)._encode(obj, None)
        # Convert strs to FixedObjects here to make sure they get encoded
        # correctly

        if isinstance(obj, Container):
            obj.update((k, get_ref(v)) for (k, v) in obj.items()
                       if k != 'class_name')
            fixed_obj = obj

        elif isinstance(obj, Dictionary):
            fixed_obj = obj.__class__(dict(
                (get_ref(field), get_ref(value))
                for (field, value) in obj.value.items()
            ))

        elif isinstance(obj, dict):
            fixed_obj = dict(
                (get_ref(field), get_ref(value))
                for (field, value) in obj.items()
            )

        elif isinstance(obj, list):
            fixed_obj = [get_ref(field) for field in obj]

        elif isinstance(obj, Form):
            fixed_obj = obj.__class__(**dict(
                (field, get_ref(value))
                for (field, value) in obj.value.items()
            ))

        elif isinstance(obj, ContainsRefs):
            fixed_obj = obj.__class__([get_ref(field)
                                       for field in obj.value])

        else:
            return obj

        fixed_obj._made_from = obj
        return fixed_obj

    root = PythonicAdapter(Pass)._encode(root, None)

    i = 0
    objects = [root]
    root._tmp_index = 1
    while i < len(objects):
        objects[i] = fix_fields(objects[i])
        i += 1

    for obj in orig_objects:
        obj._tmp_index = None
        # Strip indexes off objects in case we save again later

    return objects


def encode_network(root):
    """Yield ref-containing obj table entries from object network"""
    def fix_values(obj):
        if isinstance(obj, Container):
            obj.update((k, get_ref(v)) for (k, v) in obj.items()
                       if k != 'class_name')
            fixed_obj = obj

        elif isinstance(obj, Dictionary):
            fixed_obj = obj.__class__(dict(
                (get_ref(field), get_ref(value))
                for (field, value) in obj.value.items()
            ))

        elif isinstance(obj, dict):
            fixed_obj = dict(
                (get_ref(field), get_ref(value))
                for (field, value) in obj.items()
            )

        elif isinstance(obj, list):
            fixed_obj = [get_ref(field) for field in obj]

        elif isinstance(obj, Form):
            fixed_obj = obj.__class__(**dict(
                (field, get_ref(value))
                for (field, value) in obj.value.items()
            ))

        elif isinstance(obj, ContainsRefs):
            fixed_obj = obj.__class__([get_ref(field)
                                       for field in obj.value])

        else:
            return obj

        fixed_obj._made_from = obj
        return fixed_obj

    objects = []

    def get_ref(obj, objects=objects):
        obj = PythonicAdapter(Pass)._encode(obj, None)

        if isinstance(obj, (FixedObject, Container)):
            if getattr(obj, '_index', None):
                index = obj._index
            else:
                objects.append(None)
                obj._index = index = len(objects)
                objects[index - 1] = fix_values(obj)
            return Ref(index)
        else:
            return obj  # Inline value

    get_ref(root)

    for obj in objects:
        if getattr(obj, '_index', None):
            del obj._index
    return objects


def decode_obj_table(table_entries, plugin):
    """Return root of obj table. Converts user-class objects"""
    entries = []
    for entry in table_entries:
        if isinstance(entry, Container):
            assert not hasattr(entry, '__recursion_lock__')
            user_obj_def = plugin.user_objects[entry.classID]
            assert entry.version == user_obj_def.version
            entry = Container(class_name=entry.classID,
                              **dict(zip(user_obj_def.defaults.keys(),
                                         entry.values)))
        entries.append(entry)

    return decode_network(entries)


def encode_obj_table(root, plugin):
    """Return list of obj table entries. Converts user-class objects"""
    entries = encode_network(root)

    table_entries = []
    for entry in entries:
        if isinstance(entry, Container):
            assert not hasattr(entry, '__recursion_lock__')
            user_obj_def = plugin.user_objects[entry.class_name]
            attrs = OrderedDict()
            for (key, default) in user_obj_def.defaults.items():
                attrs[key] = entry.get(key, default)
            entry = Container(classID=entry.class_name,
                              length=len(attrs),
                              version=user_obj_def.version,
                              values=attrs.values())
        table_entries.append(entry)
    return table_entries
