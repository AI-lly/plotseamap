# utils/geo_helpers.py

def save_as_poly(gdf, name, filename):
    with open(filename, "w") as f:
        f.write(f"{name}\n")
        for geom in gdf.geometry:
            if geom.geom_type == "Polygon":
                f.write("1\n")
                for x, y in geom.exterior.coords:
                    f.write(f" {x} {y}\n")
                f.write("END\n")
            elif geom.geom_type == "MultiPolygon":
                for poly in geom.geoms:
                    f.write("1\n")
                    for x, y in poly.exterior.coords:
                        f.write(f" {x} {y}\n")
                    f.write("END\n")
        f.write("END\n")