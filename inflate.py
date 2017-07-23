from PIL import Image
from lxml import etree
from shapely.geometry import Polygon
from shapely.ops import cascaded_union

import random
import itertools

REGION_SHOW = True

def paths(accessor, width, height):
    # Construct initial polygons
    base_polygons = {
        (x, y): Polygon([
            (x, y),
            (x + 1, y),
            (x + 1, y + 1),
            (x, y + 1),
            (x, y),
        ]).convex_hull
        for y in range(height)
        for x in range(width)
        if accessor[x, y]
    }

    polygon_reps = {
        (x, y): (x, y)
        for (x, y) in base_polygons.keys()
    }

    # Iteratively merge adjacent polygons

    iteration = 0
    while True:
        any_changed = False

        iteration += 1
        unique = len(set(polygon_reps.values()))
        print(f"Iteration {iteration}: {unique} unique polygons")

        def replace_representation(rep_from, rep_to):
            for key, value in polygon_reps.items():
                if value == rep_from:
                    polygon_reps[key] = rep_to

        def directional_merge(xoff, yoff):
            nonlocal any_changed

            for (x, y), sec_poly_rep in polygon_reps.items():
                try:
                    pri_poly_rep = polygon_reps[x - xoff, y - yoff]
                except KeyError:
                    continue

                if pri_poly_rep == sec_poly_rep:
                    continue

                pri_poly = base_polygons[pri_poly_rep]
                sec_poly = base_polygons[sec_poly_rep]

                new_poly = cascaded_union(
                    [pri_poly, sec_poly],
                ).simplify(0.01)
                print(list(pri_poly.exterior.coords))
                print(list(sec_poly.exterior.coords))
                print(list(new_poly.exterior.coords))

                if (
                    not new_poly.is_valid or
                    not new_poly.is_simple
                ):
                    continue

                print(f"Merge at {x}, {y} with {x - xoff}, {y - yoff}")
                replace_representation(sec_poly_rep, pri_poly_rep)

                del base_polygons[sec_poly_rep]
                base_polygons[pri_poly_rep] = new_poly

                any_changed = True
                return

        directional_merge(1, 0)
        directional_merge(0, 1)

        if not any_changed:
            break

    for region in base_polygons.values():
        yield list(region.exterior.coords)

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
