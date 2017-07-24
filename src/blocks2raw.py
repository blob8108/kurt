#!/usr/bin/env python
# -*- coding: utf-8 -*-

import kurt
import itertools


def strip_text(block):
    return kurt.BlockType._strip_text(block.text)


plugin_specials = {
    "@greenFlag": "green flag",
    "@turnLeft": "cw",
    "@turnRight": "ccw",
    "_myself_": "myself",
    "_mouse_": "mouse",
}

plugin_class_annotations = {
    "@greenFlag": "-green-flag",
    "@turnLeft": "-turn-arrow",
    "@turnRight": "-turn-arrow",
}

plugin_category_classes = {
    "sensor": "purple",
    "wedo": "purple",
    "midi": "purple",
}


def scratchblocks2_definitions(plugin):
    plugin = kurt.plugin.Kurt.get_plugin(plugin)
    plugin_blocks = sorted(plugin.blocks, key=lambda b: b and b.category)

    done_block_text = set()
    last_category = None
    for (category, blocks) in itertools.groupby(plugin_blocks,
                                                key=lambda b: b and b.category):
        if category is None or not blocks or 'obsolete' in category:
            yield
            continue

        if category != last_category:
            yield
            yield
            yield
            yield "## %s ##" % plugin_category_classes.get(category, category)

        for block in blocks:
            if block:
                if strip_text(block) not in done_block_text:
                    defaults = list(block.defaults)
                    code = block.stringify(block_plugin=True).split("\n")[0]

                    classes = set()
                    if block.shape in ("hat", "cap"):
                        classes.add(block.shape)

                    if block.has_insert("stack"):
                        classes.add("cstart")

                    for (match, class_name) in plugin_class_annotations.items():
                        if match in code:
                            classes.add(class_name)

                    for (match, replacement) in plugin_specials.items():
                        if match in code:
                            code = code.replace(match, replacement)

                    if classes:
                        code += " ## " + " ".join(classes)

                    yield code

                    if block.command == "doIf":
                        yield "else ## celse"
                        yield "end ## cend"

                    done_block_text.add(strip_text(block))
            else:
                yield

        last_category = category


def print_definitions(plugin, butnot=None):
    butnot = butnot or set()

    for line in scratchblocks2_definitions(plugin):
        if line not in butnot:
            if line:
                print line

                if not line.startswith("#"):
                    butnot.add(line)
            else:
                print

    return butnot


def print_all_definitions():
    butnot = print_definitions('scratch20')

    print
    print
    print
    print '// Obsolete Scratch 1.4 blocks'

    print_definitions('scratch14', butnot)


if __name__ == "__main__":
    print_all_definitions()
