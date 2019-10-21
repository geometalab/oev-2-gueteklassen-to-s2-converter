import itertools

import geopandas as gpd
import s2_py as s2
from shapely.geometry import polygon as shapely_polygon, MultiPolygon as shapely_MultiPolygon

def main():
    layer_df = read_gdb("Final_OeVGK_2018.gdb.zip", "oevgk18_2018_11_13_Tag")
    polys = convert(layer_df)
    # for i, poly in polys.items():
    #     print(i, poly.num_loops(), layer.geometry[i].geom_type)
    #     compute_covering(poly)
    layer_df['covering'] = polys.apply(compute_covering)
    print(layer_df)
    print(assign_grade(layer_df))
    #covering = compute_covering(poly)
    #print(covering[0].ToLatLng())
    #print(covering[0].id())

def read_gdb(file, layer_name):
    layer = gpd.read_file(file, layer=layer_name)
    layer = layer.to_crs({'init': 'epsg:4326'})
    layer.geometry = layer.geometry.apply(fix_geometry)
    return layer

def convert(layer_df):
    #return [s2poly(multipolygon) for multipolygon in layer.geometry]
    return layer_df.geometry.apply(s2anypoly)
    # TODO: use builder on result

def compute_covering(s2polygon):
    coverer = s2.S2RegionCoverer()
    coverer.set_min_level(17)
    coverer.set_max_level(17)
    coverer.set_max_cells(100)
    covering = coverer.GetCovering(s2polygon)
    return covering

def assign_grade(layer_df):
    dictionary = {}
    for i, row in layer_df.iterrows():
        grade = row.grade
        covering = row.covering
        for cell in covering:
            cell_id=cell.id()
            old_grade = dictionary.get(cell_id, "Z")
            dictionary[cell_id] = min(grade, old_grade)
    return dictionary


def s2anypoly(geom):
    if type(geom) is shapely_MultiPolygon:
        return s2multipoly(geom)
    else:
        assert type(geom) is shapely_polygon.Polygon
        return s2singlepoly(geom)

def fix_geometry(geometry):
    fixed_geom = geometry.buffer(0)
    assert fixed_geom.is_valid
    return fixed_geom

def s2multipoly(multipolygon) -> s2.S2Polygon:  # a S2 "Polygon" can represent an OGC / Shapely MultiPolygon
    assert multipolygon.is_valid
    assert type(multipolygon) is shapely_MultiPolygon
    polygons = multipolygon.geoms

    rings = itertools.chain.from_iterable(extract_rings(polygon) for polygon in polygons)
    s2loops = [s2loop(ring) for ring in rings]
    result = s2.S2Polygon()
    result.InitNested(s2loops)
    return result

def s2singlepoly(polygon) -> s2.S2Polygon:  # a S2 "Polygon" can represent an OGC / Shapely Polygon
    assert polygon.is_valid
    assert type(polygon) is shapely_polygon.Polygon

    rings = extract_rings(polygon)
    s2loops = [s2loop(ring) for ring in rings]
    result = s2.S2Polygon()
    result.InitNested(s2loops)
    return result

#def s2singlepoly(polygon_unoriented) -> s2.S2Polygon:
#    result = s2.S2Polygon()
#    result.InitNested(extract_rings(polygon_unoriented))

def extract_rings(polygon_unoriented):
    polygon_oriented = shapely_polygon.orient(polygon_unoriented, 1.0)
    return [polygon_oriented.exterior, *polygon_oriented.interiors]

def s2loop(ring: shapely_polygon.LinearRing):
    s2points = [s2point(coord_pair) for coord_pair in ring.coords]
    result = s2.S2Loop(s2points)
    result.Normalize()  # orient so that at most 1/2 sphere is enclosed
    return result

def s2point(coord_pair):
    lng, lat = coord_pair
    latlng = s2.S2LatLng.FromDegrees(lat, lng)
    point = latlng.ToPoint()
    return point

if __name__ == "__main__":
    main()