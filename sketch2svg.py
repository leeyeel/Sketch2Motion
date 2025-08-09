import io
import  sys
import subprocess
from PIL import Image
from svgpathtools import parse_path,Path
from xml.etree import ElementTree as ET

if sys.platform == "win32":
    executable_path = "potrace.exe"
else:
    executable_path = "potrace"

def sketch2svg(
    img_path: str,
    output_path: str =""
        ):
    
    print(f"Processing image: {img_path}", file=sys.stderr)
    im = Image.open(img_path)
    gray = im.convert("L")
    bw = gray.point(lambda x: 0 if x < 128 else 1, mode='1')
    buf = io.BytesIO()
    bw.save(buf, format='BMP')
    pbm_data = buf.getvalue()
    
    proc = subprocess.run(
            [f"{executable_path}", "-s", "--group", "-o", "-"],
            input=pbm_data,
            stdout=subprocess.PIPE,
            check=True
    )

    #svg_data = split_svg_by_subpaths(proc.stdout)
    svg_data = proc.stdout

    if not output_path:
        output_path = img_path.rsplit('.', 1)[0] + ".svg"
    with open(output_path, "wb") as f:
        f.write(svg_data)

    print(f"SVG saved to: {output_path}", file=sys.stderr)
    
    return output_path, output_path


def split_svg_by_subpaths(svg_bytes: bytes) -> bytes:
    """
    split SVG <path> by subpaths,

    dependencies:
    - svgpathtools: for parsing SVG paths,
    install with:
    pip install svgpathtools
    """
    # register SVG namespace and parse the SVG bytes
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    root = ET.fromstring(svg_bytes)
    NS = "{http://www.w3.org/2000/svg}"
    style_attrs = ['fill', 'stroke', 'stroke-width', 'fill-rule', 'style']


    for parent in root.findall(".//"):
        children = list(parent)
        for child in children:
            if child.tag == NS + 'path':
                d_original = child.get('d')
                d_abs = parse_path(d_original).d()
                

                subpaths = ['M' + sp for sp in d_abs.strip().split('M') if sp.strip()]


                own_attrs = dict(child.attrib)
                inherited = {}
                if parent.tag == NS + 'g':
                    for attr in style_attrs:
                        if attr not in own_attrs and parent.get(attr) is not None:
                            inherited[attr] = parent.get(attr)

                new_elems = []
                for d_sub in subpaths:
                    ne = ET.Element(NS + 'path')
                    for k, v in inherited.items():
                        ne.set(k, v)

                    for k, v in own_attrs.items():
                        if k != 'd':
                            ne.set(k, v)
                    ne.set('d', d_sub)
                    new_elems.append(ne)


                idx = children.index(child)
                parent.remove(child)
                for i, ne in enumerate(new_elems):
                    parent.insert(idx + i, ne)

    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding='utf-8', xml_declaration=True)
    return buf.getvalue()


def is_hole(subpath: Path) -> bool:
    """
    judge if a subpath is a "hole" by checking the signed area of its segments.
    if the area is negative, it is a hole (counter-clockwise direction).
    """
    pts = [seg.start for seg in subpath]
    if not pts:
        return False
    pts.append(subpath[-1].end)
    area = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i].real, pts[i].imag
        x1, y1 = pts[i+1].real, pts[i+1].imag
        area += x0*y1 - x1*y0
    area *= 0.5
    return area < 0

def point_in_poly(x: float, y: float, poly: list[tuple[float,float]]) -> bool:
    """
    determine if a point (x,y) is inside a polygon defined by a list of vertices.
    Uses the ray-casting algorithm.
    """
    inside = False
    n = len(poly)
    for i in range(n):
        x0,y0 = poly[i]
        x1,y1 = poly[(i+1)%n]
        if ((y0>y) != (y1>y)) and (x < (x1-x0)*(y-y0)/(y1-y0) + x0):
            inside = not inside
    return inside

def hole_belongs_to_outer(hole: Path, outer: Path) -> bool:
    """
    check if a hole belongs to an outer path by checking if the centroid of the hole's points
    is inside the outer path polygon.
    """
    hpts = [seg.start for seg in hole]
    if not hpts:
        return False
    cx = sum(p.real for p in hpts) / len(hpts)
    cy = sum(p.imag for p in hpts) / len(hpts)
    opts = [seg.start for seg in outer]
    opts.append(outer[-1].end)
    poly = [(p.real,p.imag) for p in opts]
    return point_in_poly(cx, cy, poly)

def split_svg_by_subpaths(svg_bytes: bytes) -> bytes:
    """
    1. decompose SVG <path> by subpaths,
    2. check if each subpath is a hole or an outer path,
    3. group outer paths with their holes,
    4. generate new <path> elements with fill-rule="evenodd" for holes.
    5. return the modified SVG as bytes. 
    """
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    root = ET.fromstring(svg_bytes)
    NS = "{http://www.w3.org/2000/svg}"
    style_attrs = ['fill','stroke','stroke-width','fill-rule','style']

    for parent in root.findall(".//"):
        for child in list(parent):
            if child.tag != NS + 'path':
                continue

            d_abs = parse_path(child.get('d')).d()

            parts = ['M'+p for p in d_abs.strip().split('M') if p.strip()]
            parsed = [(p, parse_path(p)) for p in parts]

            outers = [(s,sp) for s,sp in parsed if not is_hole(sp)]
            holes  = [(s,sp) for s,sp in parsed if     is_hole(sp)]

            used_holes = set()
            groups = []
            for o_str,o_path in outers:
                grp_holes = []
                for h_str,h_path in holes:
                    if h_str in used_holes:
                        continue
                    if hole_belongs_to_outer(h_path, o_path):
                        grp_holes.append(h_str)
                        used_holes.add(h_str)
                groups.append((o_str, grp_holes))

            for h_str,h_path in holes:
                if h_str not in used_holes:
                    groups.append((h_str, []))

            own_attrs = dict(child.attrib)
            inherited = {}
            if parent.tag == NS+'g':
                for attr in style_attrs:
                    if attr not in own_attrs and parent.get(attr) is not None:
                        inherited[attr] = parent.get(attr)

            idx = list(parent).index(child)
            parent.remove(child)
            for i,(outer_str, hole_strs) in enumerate(groups):
                ne = ET.Element(NS+'path')
                for k,v in inherited.items():
                    ne.set(k,v)
                for k,v in own_attrs.items():
                    if k!='d':
                        ne.set(k,v)
                combined = outer_str + ''.join(hole_strs)
                ne.set('d', combined)
                if hole_strs:
                    ne.set('fill-rule', 'evenodd')
                parent.insert(idx+i, ne)

    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding='utf-8', xml_declaration=True)
    return buf.getvalue()

