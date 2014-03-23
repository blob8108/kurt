"""
Load fonts into Scratch as costumes, complete with a script for stamping text.

Each font is loaded into a sprite, and can write any message you please - feel
free to export any of the sprites and use them in your own projects!

Customise the options below...

"""
import os
import sys
import re

from PIL import Image, ImageDraw, ImageFont

# try and find kurt directory
path_to_file = os.path.join(os.getcwd(), __file__)
path_to_lib = os.path.split(os.path.split(path_to_file)[0])[0]
sys.path.append(path_to_lib)
import kurt


################################################################################



### SETTINGS: ###


# Text color (r, g, b)
TEXT_COLOR = (0, 0, 0)

# Background color
BG_COLOR = (255, 255, 255)

# Height of character images in pixels
FONT_SIZE = 100

# Name of the .sb file
PROJECT_NAME = "Fonts"

FONT_PATHS = [
    # Add the full path to your font files here, for example:
    "url('http://www.fontsaddict.com/fontface/analogue-reduced-45-light.ttf');}",

]

# The list of characters
# Default is A-z, 0-9, and ' !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
CHARACTERS = ''.join(map(chr, range(32, 127)))

# Set the Fonts.Message variable
# Used in the demo script
MESSAGE = "Dots "


### End of settings ###



################################################################################



def text_to_image(font, text, color):
    (w, h) = font.getsize(text)
    image = Image.new("RGB", (w, h), BG_COLOR) #(w*2, h*2))
    draw = ImageDraw.Draw(image)
    draw.text((0,0), text, color, font=font)
    draw.fontmode = "1"
    #image = image.resize((w, h), Image.ANTIALIAS)
    return image



project = kurt.Project()

y = 170

project.variables = {
    'Fonts.Message': kurt.Variable(),
    'Fonts.x': kurt.Variable(),
    'Fonts.y': kurt.Variable(),
    'Fonts.line_height': kurt.Variable(),
    'Fonts.Font': kurt.Variable(),
}

stage_script = """
when gf clicked
clear
set Fonts.Message to "{MESSAGE}"
set Fonts.x to (-230)
set Fonts.y to (170)
set Fonts.line_height to (::line_height::)
""".format(**locals())

line_height = 0

for font_path in FONT_PATHS:
    font = ImageFont.truetype(font_path, FONT_SIZE)
    (_, font_name) = os.path.split(font_path)
    if "." in font_name:
        font_name = ".".join(font_name.split(".")[:-1])
    font_name = font_name.replace("_", "")
    if font_name in project.sprites:
        continue
    print font_name

    sprite = kurt.Sprite(project, name=font_name)

    for name in ("i", "j", "word x", "message"):
        sprite.variables[name] = kurt.Variable(0)

    sprite.lists["widths"] = kurt.List()

    error = False
    for char in CHARACTERS:
        pil_image = text_to_image(font, char, TEXT_COLOR)
        (width, height) = pil_image.size
        if char == " " and width == 0 or height == 0:
            width = max(1, width)
            height = max(1, width)
            pil_image = Image.new("RGB", (width, height), (255, 255, 255))

        try:
            costume = kurt.Costume(char, kurt.Image(pil_image), (0, 0))
        except SystemError:
            error = True
            break
        sprite.costumes.append(costume)
        if char == 'A':
            sprite.costume = costume

        sprite.lists["widths"].items.append(costume.width)
        line_height = max(line_height, costume.height)

    if error:
        continue

    sprite.parse("""
    when gf clicked
    hide
    """)

    sprite.parse("""
    when I receive "Fonts.Write"
    if not Fonts.Font = "{font_name}"
        stop script
    end
    hide
    go to x:(Fonts.x) y:(Fonts.y)
    set i to 1
    set message to Fonts.Message
    repeat until i > (length of message) - 1
        set word x to x position
        set j to i
        switch costume to "!"
        repeat until (costume # = 1 or j > (length of message) - 1)
            switch costume to letter j of message
            change word x by (item (costume #) of widths)
            if word x > 230
                set x to -230
                change y by 0 - Fonts.line_height
                if y position < -170
                    wait 1 secs
                    clear
                    set y to 170
                end
                switch costume to 1 + 0
                set j to 0
            else
                change j by 1
            end
            if costume # = 1
                change j by -1
            end
        end
        repeat until i > j
            switch costume to letter i of message
            stamp
            change x by item costume # of widths
            change i by 1
        end
    end
    switch costume to A
    set Fonts.x to x position
    set Fonts.y to y position
    """.format(**locals()))

    stage_script += """
    set Fonts.Font to "{font_name}"
    broadcast "Fonts.Write" and wait
    """.format(**locals())

    project.sprites.append(sprite)
    y -= 100


stage_script = stage_script.replace("::line_height::", str(line_height))
project.stage.parse(stage_script)

project.stage.parse("""
set Fonts.Message to "Hello there!"
set Fonts.x to 0
set Fonts.y to 0
set Fonts.Font to "HelveticaCY"
broadcast "Fonts.Write" and wait
""")


print
print "Saving %i fonts..." % len(project.sprites)
project.convert('scratch14')
project.save(PROJECT_NAME)
