from PIL import Image
from lxml import etree

import argparse
import itertools
import pathlib
import functools
import pyclipper
import random
import sys

REGION_SHOW = False

def paths(accessor, width, height):
    pc = pyclipper.Pyclipper()

    for y in range(height):
        for x in range(width):
            if not accessor[x, y]:
                continue

            pc.AddPath([
                (x, y),
                (x + 1, y),
                (x + 1, y + 1),
                (x, y + 1),
            ], pyclipper.PT_SUBJECT, True)

    result = pc.Execute2(
        pyclipper.CT_UNION,
        pyclipper.PFT_EVENODD,
        pyclipper.PFT_EVENODD,
    )

    print(result.Parent)

    def descend_node(node):
        if node.Contour:
            yield node.IsHole, node.Contour + [node.Contour[0]]
        for child in node.Childs[::-1]:
            yield from descend_node(child)

    yield from descend_node(result)

def convert(path, fp, scale_factor=100, margin=10, invert=False):
    img = Image.open(str(path))
    img = img.convert('1')
    if not invert:
        img = img.point(lambda x: 0 if x else 1)
    unit_paths = paths(img.load(), img.size[0], img.size[1])

    svg_namespace = 'http://www.w3.org/2000/svg'
    xlink_namespace = 'http://www.w3.org/1999/xlink'

    margin = 10

    nsmap = {
        None: svg_namespace,
        'xlink': xlink_namespace,
    }

    def tag(tag, namespace):
        return '{' + namespace + '}' + tag

    with etree.xmlfile(fp, encoding='utf-8') as f:
        f.write_declaration()
        f.write_doctype(
            '<!DOCTYPE svg PUBLIC "-//W3C/DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
        )

        with f.element(
            tag('svg', svg_namespace),
            nsmap=nsmap,
            attrib={
                tag('baseProfile', svg_namespace): 'full',
                tag('width', svg_namespace): str(scale_factor * img.size[0] + 2 * margin),
                tag('height', svg_namespace): str(scale_factor * img.size[1] + 2 * margin),
            },
        ):
            with f.element(
                tag('g', svg_namespace),
                attrib={
                    tag('id', svg_namespace): 'marker',
                    tag('transform', svg_namespace):
                        f'translate({margin} {margin}) scale({scale_factor})',
                    tag('stroke', svg_namespace): 'none',
                    tag('fill-rule', svg_namespace): 'evenodd',
                }
            ):
                if REGION_SHOW:
                    region_colours = [
                        '#001f3f', # navy
                        '#0074d9', # blue
                        '#7fdbff', # aqua
                        '#39cccc', # teal
                        '#3d9970', # olive
                        '#2ecc40', # green
                        '#01ff70', # lime
                        '#ffdc00', # yellow
                        '#ff851b', # orange
                        '#ff4136', # red
                        '#85144b', # maroon
                        '#f012be', # fuchsia
                        '#b10dc9', # purple
                        '#111111', # black
                        '#aaaaaa', # grey
                        '#dddddd', # silver
                    ]

                    random.shuffle(region_colours)

                    region_colours = itertools.cycle(region_colours)
                else:
                    region_colours = itertools.cycle(['black'])

                for is_hole, path in unit_paths:
                    path_components = [f"M{path[0][0]} {path[0][1]}"]

                    print(path)

                    path_components.extend(
                        f"L{x} {y}"
                        for x, y in path[1:-1]
                    )

                    path_components.append("z")
                    if is_hole:
                        colour = 'white'
                    else:
                        colour = next(region_colours)

                    with f.element(
                        tag('path', svg_namespace),
                        attrib={
                            tag('d', svg_namespace): ' '.join(path_components),
                            tag('fill', svg_namespace): colour,
                        }
                    ):
                        pass

def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s',
        '--scale',
        help="scale factor for images",
        type=int,
        default=100,
    )
    parser.add_argument(
        '-m',
        '--margin',
        help="margin on output images",
        type=int,
        default=10,
    )
    parser.add_argument(
        '-i',
        '--invert',
        help="invert source images",
        action='store_true',
    )
    parser.add_argument(
        'directory',
        help="directory of source images",
        type=pathlib.Path,
    )
    return parser

def main(arguments):
    options = argument_parser().parse_args(arguments)
    process = functools.partial(
        convert,
        scale_factor=options.scale,
        margin=options.margin,
        invert=options.invert,
    )

    for input_file in options.directory.glob('*.png'):
        with input_file.with_suffix('.svg').open('wb') as f:
            print(input_file.stem)
            process(input_file, f)

if __name__ == '__main__':
    main(sys.argv[1:])
