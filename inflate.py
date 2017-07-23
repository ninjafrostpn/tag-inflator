from PIL import Image
from lxml import etree

import random

REGION_SHOW = False

def path_steps_from_region(region):
    region = set(region)

    if not region:
        raise ValueError("empty region")

    start = min(region)
    current_x, current_y = start

    yield start

    while True:
        if (
            (current_x, current_y) in region and
            (current_x, current_y - 1) not in region
        ):
            current_x += 1
        elif (current_x - 1, current_y) in region:
            current_y += 1
        elif (current_x - 1, current_y - 1) in region:
            current_x -= 1
        else:
            current_y -= 1

        yield current_x, current_y

        if (current_x, current_y) == start:
            break


def is_colinear(a, b, c):
    if a[0] == b[0] == c[0]:
        return True

    if a[1] == b[1] == c[1]:
        return True

    return False


def path_from_region(region):
    steps = list(path_steps_from_region(region))

    # Optimise steps
    optimised = False

    while not optimised:
        for i in range(len(steps) - 2):
            a = steps[i]
            b = steps[i + 1]
            c = steps[i + 2]

            if is_colinear(a, b, c):
                del steps[i + 1]
                break
        else:
            optimised = True

    return steps

def paths(accessor, width, height):
    # A fairly dumb algorithm to group islands of pixels together
    regions = []

    for y in range(height):
        for x in range(width):
            if not accessor[x, y]:
                continue

            for region in regions:
                if (x, y - 1) in region:
                    region.add((x, y))
                    break
            else:
                for region in regions:
                    if (
                        (x - 1, y) in region and
                        (x - 1, y - 1) not in region
                    ):
                        region.add((x, y))
                        break
                else:
                    regions.append({(x, y)})

    for region in regions:
        yield path_from_region(region)

def convert(path, fp, scale_factor=100):
    img = Image.open(str(path))
    img = img.convert('1')
    img = img.point(lambda x: 0 if x else 1)
    #img = img.point(lambda x: 255 if x else 0)
    #img = img.point(lambda x: 255 if x < 128 else 0)
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
                }
            ):
                region_colours = [
                    'red',
                    'blue',
                    'green',
                    'magenta',
                    'cyan',
                    'yellow',
                    'orange',
                    'purple',
                    '#555',
                    '#bbb',
                ]

                random.shuffle(region_colours)

                for path in unit_paths:
                    path_components = [f"M{path[0][0]} {path[0][1]}"]

                    path_components.extend(
                        f"L{x} {y}"
                        for x, y in path[1:-1]
                    )

                    path_components.append("z")

                    if REGION_SHOW:
                        colour = region_colours.pop()
                    else:
                        colour = 'black'

                    with f.element(
                        tag('path', svg_namespace),
                        attrib={
                            tag('d', svg_namespace): ' '.join(path_components),
                            tag('fill', svg_namespace): colour,
                        }
                    ):
                        pass

with open('output.svg', 'wb') as f:
    convert('/Users/alynn/Downloads/tag36h11/tag36_11_00000.png', f)
