#!/usr/bin/env python
#------------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from collections import defaultdict

import argparse
import glob
import simplejson
import os.path
import sys
from boto.utils import JSONDecodeError
from PIL import Image, ImageFont, ImageDraw, ImageColor
from math import ceil

DEBUG = False

#------------------------------------------------------------------------------

def eprint(*args, **kwargs):
    '''
    Print to stderr.
    '''
    print(*args, file=sys.stderr, **kwargs)
    
#------------------------------------------------------------------------------

def error(*args, **kwargs):
    '''
    Print an error message beginning with ERROR: to stderr.
    '''
    eprint(*(['ERROR:'] + list(args)), **kwargs)

#------------------------------------------------------------------------------

def warning(*args, **kwargs):
    '''
    Print a warning message beginning with WARNING: to stderr.
    '''
    eprint(*(['WARNING:'] + list(args)), **kwargs)

#------------------------------------------------------------------------------

class readable_dir(argparse.Action):
    '''
    Extend argparse to check for readable directory arguments, courtesy of
    StackOverflow.
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir=values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentError(self, "readable_dir: {0} does not exist".format(prospective_dir))
        if os.access(prospective_dir, os.R_OK):
            setattr(namespace, self.dest, prospective_dir)
        else:
            raise argparse.ArgumentError(self, "readable_dir: {0} is not a readable dir".format(prospective_dir))

#------------------------------------------------------------------------------

def maxSize(*sizes):
    '''
    Given a list of size 2-tuples (width,height), return a size 2-tuple that
    is the max() of all the widths, followed by the max() of all the heights.
    
    Args:
        sizes - List of 2-tuples (width,height).
        
    Returns:
        2-tuple consisting of the max of the corresponding components.
    '''
    maxWidth = max(map(lambda s: s[0], sizes))
    maxHeight= max(map(lambda s: s[1], sizes))
    return (maxWidth, maxHeight)
    
#------------------------------------------------------------------------------

def colorCode(hex):
    '''
    Given a 6 digit hex color code string, ensure that it begins with the '#'
    character (some EWG biomes omit it.
    '''
    return hex if hex.startswith('#') else '#' + hex 


#------------------------------------------------------------------------------

def contrastingColor(rgb):
    '''
    Given a 3-tuple of RGB components, return a contrasting color.
    See: https://trendct.org/2016/01/22/how-to-choose-a-label-color-to-contrast-with-background/
    '''
    brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
    return "#ffffff" if brightness < 123 else "#000000"
    
#------------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a palette image of biomes for EpicWorldGenerator.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog='''
Examples:
    {0} -d ~/servers/pve-dev/world
        Generate ewgpal.png in the current working directory using the biomes
        configured in the specified world directory.

    {0} -d ~/servers/pve-dev/world -o palette.png
        Save the palette as palette.png in the current directory. You can
        specify a full path to the output file if desired.
                                     '''.format(sys.argv[0]))
    parser.add_argument('-w', '--world-dir', 
                        required=True, action=readable_dir,
                        help='''The path to the world directory containing EWG
                                settings/ directory.''')
    parser.add_argument('-o', '--output',
                        action='store', type=argparse.FileType('wb'), 
                        default='ewgpal.png',
                        help='The filename of the outputted palette image.')
    parser.add_argument('-v', '--view',
                        action='store_true', default=False,
                        help='Launch an image viewer to show the generated image.')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging.')

    args = parser.parse_args()
    DEBUG = args.debug
    if DEBUG:
        print('# dir:', args.world_dir)
        print('# output:', args.output)
        print('# view:', args.view)
        print()

    # If no args are given, show short usage.
    if len(sys.argv) == 1:
        parser.print_usage()
        sys.exit(0)
    
    # Map from 'biomeType' to dict: baseName -> biome dict.
    biomesByType = defaultdict(dict)
    for biomeFileName in glob.glob(args.world_dir + '/settings/biomes/*/*.json'):
        with open(biomeFileName, "r") as biomeFile:
            baseName, _ = os.path.splitext(os.path.basename(biomeFileName))
            try:
                biome = simplejson.load(biomeFile)
                enabledStatus = 'Enabled' if biome['enabled'] else 'Disabled'
                #print('{:<30} {:<8} {:<25}'.format(baseName, enabledStatus, biome.get('biomeType')))
                biomesByType[biome['biomeType']][baseName] = biome
            except JSONDecodeError as err:
                eprint('JSON error: ' + biomeFileName + ': line ' + str(err.lineno) + ', column ' + str(err.colno) + ': ' + err.msg)

    # Map biomeType to list of dict { 'biomeName': str, 'biomeColor': str }.
    biomePatches = defaultdict(list)
    for biomeType in sorted(biomesByType.keys()):
        for biomeName in sorted(biomesByType[biomeType]):
            biome = biomesByType[biomeType][biomeName]
            for biomeColor in biome['biomeColors']:
                biomePatches[biomeType].append({ 'biomeName': biomeName, 'biomeColor': colorCode(biomeColor) })

    if DEBUG:
        # List patches.
        for biomeType in sorted(biomePatches.keys()):
            patches = biomePatches[biomeType]        
            typeLine = biomeType + ' (' + str(len(patches)) + '): '
            for patch in patches:
                typeLine += patch['biomeName'] + ' (' + patch['biomeColor'] + ') '
            print(typeLine)
            
    # Compute the largest number of patches of any biome type.
    maxPatches = max(map(lambda patches: len(patches), biomePatches.values()))

    # Wrap around long rows of patches, and compute a map of biome type to rows.
    wrapColumns =  3 * int(ceil(pow(maxPatches, 1/3.0)))
    biomeTypeRows = {}
    rows = 0
    for biomeType, patches in biomePatches.iteritems():
        wrappedRows = (wrapColumns - 1 + len(patches)) // wrapColumns
        biomeTypeRows[biomeType] = wrappedRows
        rows += wrappedRows
        
    # Columns is the number of columns to show patches, excluding the first
    # (biomeType) column.
    columns = min(maxPatches, wrapColumns)
    
    # Compute the width of the first column.
    fontSize = 16
    font = ImageFont.truetype("arial", size=fontSize)
    patchPadding = font.getsize('   ')[0] 
    firstColumnWidth = 2 * patchPadding + max(map(lambda biomeType: font.getsize(biomeType)[0], biomePatches.keys()))
    
    # Compute the patch width and height from the biome name text size.
    patchTextRows = 7
    patchWidth = 0
    patchHeight = 0
    for patches in biomePatches.values():
        for patch in patches:
            textSize = font.getsize(patch['biomeName'])
            patchWidth = max(textSize[0] + 2 * patchPadding, patchWidth)
            patchHeight = max(patchTextRows * textSize[1] + 2 * patchPadding, patchHeight)
    
    # Create an image to draw on.    
    imageWidth = 1 + firstColumnWidth + patchWidth * columns
    imageHeight = 1 + patchHeight * rows
    img = Image.new("RGB", (imageWidth, imageHeight), '#404040')
    draw = ImageDraw.Draw(img)
    draw = ImageDraw.Draw(img)
    
    row = 0
    for biomeType in sorted(biomePatches.keys()):
        textSize = font.getsize(biomeType)
        patches = biomePatches[biomeType] 
        for r in range(biomeTypeRows[biomeType]):
            # Draw the biomeType (row label) in the first column.
            draw.rectangle((0, row * patchHeight, firstColumnWidth, (row + 1) * patchHeight), '#404040', '#000000')
            draw.text(((firstColumnWidth - textSize[0]) / 2, row * patchHeight + (patchHeight - textSize[1]) / 2),
                      biomeType, font=font, fill='#ffffff')
            
            # Draw all the patches in the row.
            for c in range(columns):
                patchIndex = r * columns + c
                if patchIndex >= len(patches):
                    break
                
                patch = patches[patchIndex]
                colorName = patch['biomeColor']
                rgb = ImageColor.getrgb(colorName)
                draw.rectangle((firstColumnWidth + c * patchWidth, 
                                row * patchHeight, 
                                firstColumnWidth + (c + 1) * patchWidth, 
                                (row + 1) * patchHeight), rgb, '#000000')

                # Three lines of text in patch.
                lines = [ patch['biomeName'], colorName, '{}  {}  {}'.format(rgb[0], rgb[1], rgb[2])]
                line0Size = draw.textsize(lines[0], font=font)
                line0Height = line0Size[1]
                lineGap = line0Height / 2
                totalTextHeight = 3 * line0Height + 2 * lineGap
                
                textY = row * patchHeight + (patchHeight - totalTextHeight) / 2
                for line in lines:
                    lineW, lineH = draw.textsize(line, font=font) 
                    draw.text((firstColumnWidth + (c % columns) * patchWidth + (patchWidth - lineW) / 2, textY), 
                              line, font=font, fill=contrastingColor(rgb)) 
                    textY += lineH + lineGap
                
            row += 1
            
    if args.view:
        img.show()
    img.save(args.output)