from PIL import Image
from lxml import etree
from shapely.geometry import Polygon
from shapely.ops import cascaded_union

import random
import itertools

REGION_SHOW = True

def merge_polygons(polygons):
    working_queue = list(polygons)
    random.shuffle(working_queue)

    while working_queue:
        focus = working_queue.pop()

        new_working_queue = []

        for candidate in working_queue:
            if candidate.touches(focus):
                focus_prime = focus.union(candidate)
                if isinstance(focus_prime, Polygon):
                    focus = focus_prime
                    continue
            new_working_queue.append(candidate)

        yield focus

def paths(accessor, width, height):
    # Construct initial polygons
    polygons = [
        Polygon([
            (x, y),
            (x + 1, y),
            (x + 1, y + 1),
            (x, y + 1),
            (x, y),
        ]).convex_hull
        for y in range(height)
        for x in range(width)
        if accessor[x, y]
    ]

    num_polygons = len(polygons)

    for iteration in itertools.count(0):
        print(f"Iteration {iteration}: {num_polygons} polys")
        polygons = list(merge_polygons(polygons))
        new_num_polygons = len(polygons)

        if new_num_polygons == num_polygons:
            break

        num_polygons = new_num_polygons

    return [
        list(x.simplify(0.01).exterior.coords)
        for x in polygons
    ]

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

                for path in unit_paths:
                    path_components = [f"M{path[0][0]} {path[0][1]}"]

                    print(path)

                    path_components.extend(
                        f"L{x} {y}"
                        for x, y in path[1:-1]
                    )

                    path_components.append("z")
                    colour = next(region_colours)

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
