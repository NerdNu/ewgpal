ewgpal
======
Generates a palette image of EpicWorldGenerator biome colours.

`ewgpal` loads JSON biome configurations from the `settings/biomes/*/` directories
under the specified world directory and generates a palette image showing:

 * the `biomeType` setting - the group/category of the biome,
 * biome name (as the base name of the file without the `.json` suffix), and
 * biome colour, in two forms: as 6 hexadecimal digits preceded by `#` and as 3 
   base-10 numbers for red, green and blue components.

Where a biome contains multiple colours in the `biomeColors` setting, `ewgpal`
will generate a colour patch for each listed colour.


Command Line Arguments
----------------------
```
$ bin/ewgpal --help
usage: ewgpal.py [-h] -w WORLD_DIR [-o OUTPUT] [-v] [--debug]

Generate a palette image of biomes for EpicWorldGenerator.

optional arguments:
  -h, --help            show this help message and exit
  -w WORLD_DIR, --world-dir WORLD_DIR
                        The path to the world directory containing EWG
                        settings/ directory.
  -o OUTPUT, --output OUTPUT
                        The filename of the outputted palette image.
  -v, --view            Launch an image viewer to show the generated image.
  --debug               Enable debug logging.

Examples:
    /home/david/projects/python/ewgpal.orig/src/ewgpal.py -d ~/servers/pve-dev/world
        Generate ewgpal.png in the current working directory using the biomes
        configured in the specified world directory.

    /home/david/projects/python/ewgpal.orig/src/ewgpal.py -d ~/servers/pve-dev/world -o palette.png
        Save the palette as palette.png in the current directory. You can
        specify a full path to the output file if desired.
```

Sample Output
-------------
`ewgpal` produces the following palette image for the default biomes of EpicWorldGenerator (version 8.0.0-pre5, at the time of writing):

![ewgpal.png](https://github.com/NerdNu/ewgpal/blob/master/images/default-ewgpal.png)
