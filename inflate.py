from PIL import Image
from lxml import etree

import argparse
import itertools
import pathlib
import functools
import pyclipper
import random
import sys
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

REGION_SHOW = False

A4 = ('210mm', '297mm')

SIZE = A4


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

    def descend_node(node):
        if node.Contour:
            yield node.IsHole, node.Contour + [node.Contour[0]]
        for child in node.Childs[::-1]:
            yield from descend_node(child)

    yield from descend_node(result)


def convert(path, fp, invert=False):
    img = Image.open(str(path))
    img = img.convert('1')
    if not invert:
        img = img.point(lambda x: 0 if x else 1)
    unit_paths = paths(img.load(), img.size[0], img.size[1])

    svg_namespace = 'http://www.w3.org/2000/svg'
    xlink_namespace = 'http://www.w3.org/1999/xlink'

    nsmap = {
        None: svg_namespace,
        'xlink': xlink_namespace,
    }

    def tag(tag, namespace):
        return '{' + namespace + '}' + tag

    svg_tag = functools.partial(tag, namespace=svg_namespace)

    with etree.xmlfile(fp, encoding='utf-8') as f:
        f.write_declaration()
        f.write_doctype(
            '<!DOCTYPE svg PUBLIC "-//W3C/DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
        )

        with f.element(
            svg_tag('svg'),
            nsmap=nsmap,
            attrib={
                svg_tag('baseProfile'): 'full',
                svg_tag('width'): SIZE[0],
                svg_tag('height'): SIZE[1],
            },
        ):

            with f.element(
                svg_tag('g'),
                attrib={
                    svg_tag('id'): 'marker',
                    svg_tag('transform'):
                        'translate(50 150) scale(50)',
                    svg_tag('stroke'): 'none',
                    svg_tag('fill-rule'): 'evenodd',
                }
            ):
                with f.element(
                        svg_tag('text'),
                        attrib={
                            svg_tag('fill'): '#999',
                            svg_tag('x'): '9',
                            svg_tag('text-anchor'): 'end',
                            svg_tag('y'): '9.2',
                            svg_tag('font-size'): '0.2px',
                        }
                ):
                    f.write(path.stem)
                with f.element(
                        svg_tag('text'),
                        attrib={
                            svg_tag('fill'): '#999',
                            svg_tag('x'): '1',
                            svg_tag('text-anchor'): 'start',
                            svg_tag('y'): '9.2',
                            svg_tag('font-size'): '0.2px',
                        }
                ):
                    f.write("This way up")
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
                    path_components = [
                        "M{x} {y}".format(
                            x=path[0][0],
                            y=path[0][1],
                        ),
                    ]

                    path_components.extend(
                        "L{x} {y}".format(x=x, y=y)
                        for x, y in path[1:-1]
                    )

                    path_components.append("z")
                    if is_hole:
                        colour = 'white'
                    else:
                        colour = next(region_colours)

                    with f.element(
                        svg_tag('path'),
                        attrib={
                            svg_tag('d'): ' '.join(path_components),
                            svg_tag('fill'): colour,
                        }
                    ):
                        pass


def argument_parser():
    parser = argparse.ArgumentParser()
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
        invert=options.invert,
    )

    for input_file in options.directory.glob('*.png'):
        if input_file.stem == 'mosaic':
            continue
        svg_path = input_file.with_suffix('.svg')
        print("Processing", input_file.stem)
        with svg_path.open('wb') as f:
            process(input_file, f)

        svg_data = svg2rlg(str(svg_path))
        renderPDF.drawToFile(svg_data, str(input_file.with_suffix('.pdf')))


if __name__ == '__main__':
    main(sys.argv[1:])
