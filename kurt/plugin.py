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

"""
To add support for a new file format, write a new :class:`KurtPlugin` subclass::

    import kurt
    from kurt.plugin import Kurt, KurtPlugin

    class MyScratchModPlugin(KurtPlugin):
        def load(self, fp):
            kurt_project = kurt.Project()
            # ... set kurt_project attributes ... #
            return kurt_project

        def save(self, fp, kurt_project):
            # ... save kurt_project attributes to file ...

    Kurt.register(MyScratchModPlugin())

Take a look at :mod:`kurt.scratch20` for a more detailed example.


List available plugins
~~~~~~~~~~~~~~~~~~~~~~

To get a list of the plugins registered with :class:`Kurt`:

    >>> kurt.plugin.Kurt.plugins.keys()
    ['scratch20', 'scratch14']

You should see your plugin in the output, unless you forgot to :attr:`register
<Kurt.register>` it.


Notes
~~~~~

Some things to keep in mind:

* Most Scratch file formats have the *stage* as the base object -- so project
  attributes, such as the notes and the list of sprites, are stored on the
  stage object.
* For Scratch, which doesn't support stage-specific variables, global variables
  and lists are stored on the Project, not the Stage.
* If your plugin contains obsolete blocks, they should be at the *end* of the
  :attr:`blocks` list. Otherwise things might not work properly.

"""

from collections import OrderedDict

import kurt


class KurtPlugin(object):
    """Handles a specific file format.

    Loading and saving converts between a :class:`Project`, kurt's internal
    representation, and a file of this format.

    """

    name = "scratch14"
    """Short name of this file format, Python identifier style. Used internally
    by kurt.

    Examples: ``"scratch14"``, ``"scratch20.sprite"``, ``"byob3"``, ``"snap"``

    """

    display_name = "Scratch 2.0 Sprite"
    """Human-readable name of this file format. May be displayed to the user.
    Should not contain "Project" or "File".

    Examples: ``"Scratch 1.4"``, ``"Scratch 2.0 Sprite"``, ``"BYOB 3.1"``

    """

    extension = ".sb"
    """The extension used by this format, with leading dot.

    Used by :attr:`Project.load` to recognise its files.

    """

    features = []
    """A list of the :class:`Features <Feature>` that the plugin supports."""

    blocks = []
    """The list of :class:`PluginBlockType` objects supported by this
    plugin, in the order they appear in the program's interface.

    """

    def __repr__(self):
        return self.__module__ + "." + self.__class__.__name__ + "()"

    # Override the following methods in subclass:

    def load(self, fp):
        """Load a project from a file with this format.

        :attr:`Project.path` will be set later. :attr:`Project.name` will be
        set to the filename of the path to the file if unset.

        :param fp: A file pointer to the file, opened in binary mode.
        :returns: :class:`Project`

        """

        raise NotImplementedError

    def save(self, fp, project):
        """Save a project to a file with this format.

        :param path: A file pointer to the file, opened in binary mode.
        :param project: a :class:`Project`

        """

        raise NotImplementedError


class Kurt(object):
    """The Kurt file format loader.

    This class manages the registering and selection of file formats. Used by
    :class:`Project`.
    """

    plugins = OrderedDict()

    blocks = []

    @classmethod
    def register(cls, plugin):
        """Register a new :class:`KurtPlugin`.

        Once registered, the plugin can be used by :class:`Project`, when:

        * :attr:`Project.load` sees a file with the right extension

        * :attr:`Project.convert` is called with the format as a parameter

        """

        cls.plugins[plugin.name] = plugin

        # make features
        plugin.features = map(Feature.get, plugin.features)

        # fix blocks
        blocks = []
        for pbt in plugin.blocks:
            if pbt:
                pbt = pbt.copy()
                pbt.format = plugin.name
            blocks.append(pbt)
        plugin.blocks = blocks

        # add blocks
        new_blocks = filter(None, plugin.blocks)
        for pbt in new_blocks:
            for bt in cls.blocks:
                if (bt.has_command(pbt.command) or
                        bt.has_command(pbt._match)):
                    bt._add_conversion(plugin.name, pbt)
                    break
            else:
                if pbt._match:
                    raise ValueError, "Couldn't match %r" % pbt._match
                cls.blocks.append(kurt.BlockType(pbt))

    @classmethod
    def get_plugin(cls, name=None, **kwargs):
        """Returns the first format plugin whose attributes match kwargs.

        For example::

            get_plugin(extension="scratch14")

        Will return the :class:`KurtPlugin` whose :attr:`extension
        <KurtPlugin.extension>` attribute is ``"scratch14"``.

        The :attr:`name <KurtPlugin.name>` is used as the ``format`` parameter
        to :attr:`Project.load` and :attr:`Project.save`.

        :raises: :class:`ValueError` if the format doesn't exist.

        :returns: :class:`KurtPlugin`

        """

        if isinstance(name, KurtPlugin):
            return name

        if 'extension' in kwargs:
            kwargs['extension'] = kwargs['extension'].lower()
        if name:
            kwargs["name"] = name
        if not kwargs:
            raise ValueError, "No arguments"

        for plugin in cls.plugins.values():
            for name in kwargs:
                if getattr(plugin, name) != kwargs[name]:
                    break
            else:
                return plugin

        raise ValueError, "Unknown format %r" % kwargs

    @classmethod
    def block_by_command(cls, command):
        """Return the block with the given :attr:`command`.

        Returns None if the block is not found.

        """

        for block in cls.blocks:
            if block.has_command(command):
                return block

    @classmethod
    def blocks_by_text(cls, text):
        """Return a list of blocks matching the given :attr:`text`.

        Capitalisation and spaces are ignored.

        """

        text = kurt.BlockType._strip_text(text)
        matches = []
        for block in cls.blocks:
            for pbt in block.conversions:
                if pbt.stripped_text == text:
                    matches.append(block)
                    break
        return matches


#-- Features --#

def empty_generator():
    if False:
        yield


class Feature(object):
    """A format feature that a plugin supports."""

    FEATURES = {}

    @classmethod
    def get(cls, name):
        if isinstance(name, Feature):
            return name

        return cls.FEATURES[name]

    def __init__(self, name, description):
        self.name = name
        self.description = description

        Feature.FEATURES[name] = self

    def __repr__(self):
        return "<Feature(%s)>" % self.name

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.name == other

        return self is other

    def normalize(self, project):
        """Convert project to a plugin that SUPPORTS this feature."""

        return empty_generator()

    def workaround(self, project):
        """Convert project to a plugin that does NOT support this feature."""

        return empty_generator()


def workaround(feature):
    feature = Feature.get(feature)

    def _wrapper(f):
        assert callable(f)

        feature.workaround = f

    return _wrapper


def normalize(feature):
    feature = Feature.get(feature)

    def _wrapper(f):
        assert callable(f)

        feature.normalize = f

    return _wrapper


Feature("Vector Images",
        """Allow vector format (SVG) image files for costumes.""")


@workaround("Vector Images")
def _workaround_no_vector_images(project):
    """Replace vector images with fake ones."""

    RED = (255, 0, 0)
    PLACEHOLDER = kurt.Image.new((32, 32), RED)

    for scriptable in [project.stage] + project.sprites:
        for costume in scriptable.costumes:
            if costume.image.format == "SVG":
                yield "%s - %s" % (scriptable.name, costume.name)
                costume.image = PLACEHOLDER

Feature("Stage-specific Variables",
        """Can have stage-specific variables and lists, in addition to global
        variables and lists (which are stored on the :class:`Project`).""")


@workaround("Stage-specific Variables")
def _workaround_no_stage_specific_variables(project):
    """Make Stage-specific variables global (move them to Project)."""

    for (name, var) in project.stage.variables.items():
        yield "variable %s" % name

    for (name, _list) in project.stage.lists.items():
        yield "list %s" % name

    project.variables.update(project.stage.variables)
    project.lists.update(project.stage.lists)
    project.stage.variables = {}
    project.stage.lists = {}

Feature("Custom Blocks",
        """Blocks accept :class:`CustomBlockType` objects for
        their :attr:`type`.""")

Feature("First-class Lists",
        """Variables can take list values. Nested lists are supported.
        `Scriptable.lists` and `Project.lists` are unused.""")


@workaround("First-class Lists")
def _workaround_no_first_class_lists(project):
    """Replace list-containing variables with lists of the same name."""

    return empty_generator()  # TODO


@normalize("First-class Lists")
def _normalize_first_class_lists(project):
    """Replace `Scriptable.lists` with variables containing lists."""

    return empty_generator()  # TODO


#-- Convert Blocks --#

def block_workaround(bt, workaround):
    if isinstance(workaround, kurt.Block):
        w = workaround
        workaround = lambda block: w.copy()
    else:
        assert callable(workaround)

    bt = kurt.BlockType.get(bt)
    bt._add_workaround(workaround)
