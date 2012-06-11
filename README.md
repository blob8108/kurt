
# kurt

Kurt is a Python library for reading/writing Scratch project (.sb) and sprite files.

So far, it can read/write sprites and their properties, including scripts, blocks, variables, and lists. It can read costumes and export them to separate image files. It can also export scripts to `scratchblocks` format for pasting into the Scratch forums/wiki.

You could use it for:

* converting to another format (like the `scratchblocks` converter does)
* generating Scratch projects using Python code
* analysing the scripts in a project
* *(someday, perhaps...)* making a "Scratch IDE" text-based editor for Scratch scripts... :)

[Install](#installation) Kurt, and then see [Usage](#usage) to get started!

(It *can't* read/write sounds yet, but they're on the [to-do list](#todo) — see below)

**WARNING**: Make sure you take a backup of your Scratch projects before saving anything with kurt! kurt is by no means fully tested. I can't accept responsibility for corrupting your files.

If you're interested in technical details of how the format works: the code should be pretty self-documenting; but check out the documentation on the [Scratch wiki](http://wiki.scratch.mit.edu/wiki/Scratch_File_Format), which might be more readable...


## Installation

Options 1 and 2 will automatically install kurt, and its dependencies
[Construct](http://construct.wikispaces.com/) and
[PyPNG](https://code.google.com/p/pypng/).

### Option 1 (pip or easy_install)

If you have either `easy_install` or `pip` installed, installation is as simple
as running one of the following:

    pip install kurt
    easy_install kurt

### Option 2 (setup.py)

Download (or git clone) the latest version of Kurt. From the kurt folder
containing `setup.py` run:

    python setup.py install

### Option 2 (manual install)

Download the latest version of Kurt and extract the `kurt` folder somewhere in your `sys.path` — or in the same directory as your code, if you prefer.

You'll need the **latest version** of the awesome [**Construct**](http://construct.wikispaces.com/) library — used for defining the format. It currently appears to be available [here](http://pypi.python.org/pypi/construct). (I'm using Construct version 2.04).

For saving images, you'll need the [**PyPNG**](https://code.google.com/p/pypng/) module. Kurt *should* work without it, if you don't want to save images — but it's strongly recommended.

Now see [Usage](#usage) to get started!

Tested with **Python 2.6**. Works with **Scratch 1.4**; not tested with earlier versions, but possibly works.

[Scratch](http://scratch.mit.edu/) is created by the Lifelong Kindergarten Group at the MIT Media Lab.


## Recent Changes 

###v1.3, decompiler:
* Can now build projects entirely "from scratch" (as it were) in Python code using `ScratchProjectFile.new()`
* **Decompiler** to export all images, scripts from .sb file as PNG/JPG format and scratchblocks text files
* Experimental **compiler** for making .sb files, the reverse of decompiler
* *Highly* experimental scratchblocks **parser** for generating scripts
* Most **images** now work! Details:
	* Images with depth 1 and 2 now work — (fixed some buggy reverse-engineered code).
	* Default color values ("squeak_colors") now work — fixed a bug saving all-white stage background.


###v1.2, images:
* Can now parse images! :D

	Well, most images. If not, try reloading the project with Scratch and saving it again — this sometimes helps.
	
	Unfortunately, Kurt doesn't compress the images when saving them back to the file again (yet), so it may massively increase your file size :P Again, you can just open it in Scratch and save it again, and the file size will be back to normal.

* Split Sprite.media into separate costumes/sounds lists.

###v1.1, scripts:

* `Script` and `Block` classes for manipulating scripts.
* **Block plugin** formatter — reads all the scripts in a project file and outputs `[scratchblocks]` syntax code for posting on the Scratch forums/wiki.
* Filled out the `_fields` list for most of the objects in `user_objects` from the Squeak source (not the unused ones), so there should now be no "undefined" fields.
* `Color` is now parsed correctly
* Added `ScratchProjectFile.sprites` shortcut as an alias for `project.stage.sprites`


## Usage
**Getting Started** | [Scripts](#scripts) | [Images](#images) | [Decompiler](#decompiler) | [Compiler](#compiler)

Here's a quick getting started — grab a Python interpreter (Python's `>>>` prompt — just type `python` into your terminal, or load up IDLE), and have a go!

You'll probably just want to use the provided `ScratchProjectFile` and `ScratchSpriteFile` classes. Load them by passing the path to the file to their constructor and use their provided `.save()` methods.

You can import just these classes them using:

    from kurt.files import *

Load a file (you'll find a preview file, `game.sb`, saved in the `tests` directory; but feel free to try it with any Scratch project file).

	# Just pass in the absolute or relative path to the file:
	project = ScratchProjectFile("tests/game.sb")
	
    # You can reload the file at any time with .load()

Inspect project:

    project.info['author'] # u'blob8108'
    project.stage # <ScratchStageMorph(Stage)>
    
    # List fields on object:
    project.stage.fields.keys() # ['volume', 'hPan', 'sprites', 'lists', 'name', 'vars', 'obsoleteSavedState', 'color', 'media', 'bounds', 'submorphs', 'zoom', 'isClone', 'flags', 'costume', 'scripts', 'owner', 'tempoBPM', 'vPan', 'properties', 'sceneStates']

    # Access fields using dot notation:
    project.stage.tempoBPM # 60
    project.stage.sprites # OrderedCollection([<ScratchSpriteMorph(ScratchCat)>])
    
    cat = project.stage.sprites[0]
    cat.name # u'ScratchCat'

Most of the objects you're interested in, like `ScratchStageMorph` and `ScratchSpriteMorph`, inherit from `UserObject`. You can use `.fields.keys()` to see the available fields on one of these objects.

`FixedObjects` like `OrderedCollection` have a `.value` property to access their value.

Inline objects, such as `int` and `bool`, are converted transparently to their Pythonic counterparts. `Array` and `Dictionary` are converted to `list` and `dict`, too. 

Make changes:

    cat.vars # {u'vx': 0.0}
    cat.vars['vx'] = 100

Save:

    project.save()

Now re-open the project with Scratch!

Everything should, of course, work perfectly; if you do have any problems, please file an issue, and I'll take a look! (:

### Scripts
A list of scripts can be found on the `scripts` property of both sprites and the stage.

    >>> cat.scripts
    [Script(Point(23, 36.0), [
        Block('EventHatMorph', 'Scratch-StartClicked'),
        Block('xpos:', 0),
        Block('doForever',  [
                Block('doIf', 
                    Block('keyPressed:', 'right arrow'),
                    [
                        Block('changeVariable', u'vx', <#changeVar:by:>, 2),
                    ]),
                Block('doIf', 
                    Block('keyPressed:', 'left arrow'),
                    [
                        Block('changeVariable', u'vx', <#changeVar:by:>, -2),
                    ]),
                Block('changeVariable', u'vx', <#setVar:to:>, 
                    Block('*', 
                        Block('readVariable', u'vx'),
                    0.80000000000000004),
                ),
                Block('changeXposBy:', 
                    Block('readVariable', u'vx'),
                ),
            ])])]

Use the `to_block_plugin` method to print them nicely:

    >>> print cat.scripts[0].to_block_plugin()
    when green flag clicked
    set x to (0)
    forever
        if <key [right arrow v] pressed?>
            change [vx v] by (2)
        end
        if <key [left arrow v] pressed?>
            change [vx v] by (-2)
        end
        set [vx v] to ((vx) * (0.8))
        change x by (vx)
    end

This is identical to `scratchblocks` format, so you can paste them straight into the Scratch forums or wiki.

### Images
You can find costumes under a sprite's `costumes` property (similarly for stage `backgrounds`).

    cat.costumes # [<ImageMedia(costume1)>, <ImageMedia(costume2)>]
    image = cat.costumes[0]

Save to an external file:

    image.save("scratch_cat.png")

### Decompiler

There's a script under `util/decompile.py` for exporting all the images, scripts, and most other stuff in a Scratch project to separate files, with a folder for each sprite. Think a Scratch [project summary](#note1) on steroids. It puts everything in a folder named `<project name> files`. Just pass it the path to your project file:

    $ python util/decompile.py tests/game.sb

And get a folder structure a bit like this:

    game files/
        00 Stage/
            backgrounds/
                01 background1.png
            backgrounds.txt
            lists/
            scripts/
            variables.txt
        
        01 ScratchCat/
            costumes/
                01 costume1.png
                02 costume2.png
            costumes.txt
            lists/
            scripts/
                01 when gf clicked.txt
            variables.txt

### Compiler
There's also a *proof-of-concept* compiler under `util/compile.py` that takes a folder structure generated by decompile as an argument, and compiles all the images and scripts back into a .sb file. It's rather incomplete, and doesn't include lists or variables, and the scratchblocks parser complains at lots of things like `<` and `>` signs, but it kinda works... :P

Decompile the provided `game.sb`, edit one of the scripts (make sure your scratchblocks syntax is absolutely perfect), and then try compiling it!

Again, just pass it the path to your project folder:

    $ python util/decompile.py "tests/game files"

## Licence

Kurt is released under the [LGPL](http://www.gnu.org/licenses/lgpl) Version 3 (or any later version).

I'm not a lawyer; but I _think_ this means while you can use Kurt in your own, non-GPL'd code, any Kurt modifications must be distributed under the (L)GPL and include the source code. _(This is not legal advice and does not affect the terms as stated in the licence...)_


## Todo

* ~~Import images from a separate `.png` or `.jpg` file and save them into a Scratch file.~~ DONE!

* ~~"Default project" for building projects entirely "from scratch" (as it were) in Python code?~~ DONE! (Lists work, too!)

* ~~Compiler~~ Done, sort of — kind of a proof-of-concept.
	* Booleans like `<(1) < (2)>` don't work, unsurprisingly

* ~~Parse images~~ DONE! :D
	* Compress Bitmap to ByteArray on save (using run-length encoding)
	* Images with depth `16` are not supported *(need an example)*

* Make some decent tests

* Read/write external Sound files

* Optimise `ObjectNetworkAdapter` for building large files.	

	Kurt is currently very quick at parsing files; but pretty slow at writing them, particularly ones with very long scripts.

* Optimise image parsing.

## Notes

<a name="note1"></a>*project summary* — a txt file with the detail of the project such as scripts in text form. Obtained by shift-clicking Scratch's "File" menu and choosing "Write project summary".