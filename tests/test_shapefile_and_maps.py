"""Pure-python shapefile reader, geometry join and map rendering. Data-free.

The shapefiles here are built byte by byte in the test, so nothing depends on data/gis/.
"""

import struct

import pandas as pd
import pytest

from apps.dashboard import maps
from case_studies.guadeloupe.domain.geometry import build_geometry_join
from core.data.shapefile import Polygon, read_dbf, read_layer, read_polygons


def _polygon_record(number: int, rings: list[list[tuple[float, float]]]) -> bytes:
    points = [p for ring in rings for p in ring]
    parts, running = [], 0
    for ring in rings:
        parts.append(running)
        running += len(ring)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    content = struct.pack("<i", 5)
    content += struct.pack("<4d", min(xs), min(ys), max(xs), max(ys))
    content += struct.pack("<ii", len(parts), len(points))
    content += struct.pack(f"<{len(parts)}i", *parts)
    for x, y in points:
        content += struct.pack("<2d", x, y)
    header = struct.pack(">ii", number, len(content) // 2)
    return header + content


def _write_shp(path, shapes: list[list[list[tuple[float, float]]]]) -> None:
    body = b"".join(_polygon_record(i + 1, rings) for i, rings in enumerate(shapes))
    header = struct.pack(">i", 9994) + b"\x00" * 20
    header += struct.pack(">i", (100 + len(body)) // 2)
    header += struct.pack("<ii", 1000, 5)
    header += struct.pack("<4d", 0, 0, 100, 100) + struct.pack("<4d", 0, 0, 0, 0)
    path.write_bytes(header + body)


def _write_dbf(path, fields: list[str], rows: list[dict], width: int = 16) -> None:
    header_length = 32 + 32 * len(fields) + 1
    record_length = 1 + width * len(fields)
    out = bytearray()
    out += struct.pack("<B3B", 3, 24, 1, 1)
    out += struct.pack("<IHH", len(rows), header_length, record_length)
    out += b"\x00" * 20
    for name in fields:
        out += name.encode("latin-1")[:11].ljust(11, b"\x00")
        out += b"C" + b"\x00" * 4 + bytes([width]) + b"\x00" * 15
    out += b"\r"
    for row in rows:
        out += b" "
        for name in fields:
            out += str(row[name]).encode("latin-1")[:width].ljust(width, b" ")
    path.write_bytes(bytes(out))


SQUARE = [[(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0), (0.0, 0.0)]]
TRIANGLE = [[(20.0, 0.0), (30.0, 0.0), (25.0, 10.0), (20.0, 0.0)]]


def test_reads_polygon_rings_and_bounds(tmp_path):
    shp = tmp_path / "layer.shp"
    _write_shp(shp, [SQUARE, TRIANGLE])
    shapes = read_polygons(shp)
    assert len(shapes) == 2
    assert shapes[0].bounds == (0.0, 0.0, 10.0, 10.0)
    assert shapes[1].rings[0][0] == (20.0, 0.0)


def test_centroid_of_a_square_is_its_centre(tmp_path):
    shp = tmp_path / "layer.shp"
    _write_shp(shp, [SQUARE])
    (square,) = read_polygons(shp)
    assert square.centroid == pytest.approx((5.0, 5.0))


def test_multi_ring_polygons_keep_every_ring(tmp_path):
    hole = [(2.0, 2.0), (2.0, 4.0), (4.0, 4.0), (4.0, 2.0), (2.0, 2.0)]
    shp = tmp_path / "layer.shp"
    _write_shp(shp, [SQUARE + [hole]])
    (shape,) = read_polygons(shp)
    assert len(shape.rings) == 2


def test_dbf_fields_are_returned_stripped(tmp_path):
    dbf = tmp_path / "layer.dbf"
    _write_dbf(dbf, ["pacage", "surf_parc"], [{"pacage": "A1", "surf_parc": "3.90"}])
    assert read_dbf(dbf) == [{"pacage": "A1", "surf_parc": "3.90"}]


def test_read_layer_refuses_a_misaligned_pair(tmp_path):
    # Position IS the join between .shp and .dbf; a mismatch would draw every parcel with
    # its neighbour's attributes, silently.
    _write_shp(tmp_path / "layer.shp", [SQUARE, TRIANGLE])
    _write_dbf(tmp_path / "layer.dbf", ["pacage"], [{"pacage": "A1"}])
    with pytest.raises(ValueError, match="cannot be joined by position"):
        read_layer(tmp_path / "layer.shp")


def test_a_non_polygon_layer_is_refused(tmp_path):
    shp = tmp_path / "points.shp"
    header = struct.pack(">i", 9994) + b"\x00" * 20 + struct.pack(">i", 50)
    header += struct.pack("<ii", 1000, 1)  # shape type 1 = point
    header += struct.pack("<4d", 0, 0, 1, 1) + struct.pack("<4d", 0, 0, 0, 0)
    shp.write_bytes(header)
    with pytest.raises(ValueError, match="not a polygon layer"):
        read_polygons(shp)


# --- the farm-signature join ----------------------------------------------------


def _layer(tmp_path, rows):
    shp = tmp_path / "rpg.shp"
    _write_shp(shp, [SQUARE for _ in rows])
    _write_dbf(shp.with_suffix(".dbf"), ["pacage", "code_insee", "surf_parc"], rows)
    return shp


def test_join_matches_farms_by_signature(tmp_path):
    layer = _layer(tmp_path, [
        {"pacage": "PAC1", "code_insee": "97101", "surf_parc": "3.00"},
        {"pacage": "PAC1", "code_insee": "97101", "surf_parc": "5.00"},
        {"pacage": "PAC2", "code_insee": "97102", "surf_parc": "7.00"},
    ])
    parc = pd.DataFrame(
        {"COMMUNE": [97101, 97101, 97102], "SURF_HA": [3.0, 5.0, 7.0]},
        index=["P1", "P2", "P3"],
    )
    plot_farm = pd.Series({"P1": "E1", "P2": "E1", "P3": "E2"})
    join = build_geometry_join(parc, plot_farm, layer)
    assert set(join.polygons) == {"P1", "P2", "P3"}
    assert join.matched_farms == 2
    assert join.ambiguous_plots == 0


def test_join_leaves_identical_farms_unmatched_rather_than_guessing(tmp_path):
    # Two farms with the same signature: pairing them would put a parcel on someone else's
    # land, and gains nothing.
    layer = _layer(tmp_path, [
        {"pacage": "PAC1", "code_insee": "97101", "surf_parc": "3.00"},
        {"pacage": "PAC2", "code_insee": "97101", "surf_parc": "3.00"},
    ])
    parc = pd.DataFrame({"COMMUNE": [97101, 97101], "SURF_HA": [3.0, 3.0]},
                        index=["P1", "P2"])
    join = build_geometry_join(parc, pd.Series({"P1": "E1", "P2": "E2"}), layer)
    assert join.polygons == {}
    assert join.matched_farms == 0
    assert join.total_farms == 2


def test_join_counts_interchangeable_plots_inside_a_farm(tmp_path):
    layer = _layer(tmp_path, [
        {"pacage": "PAC1", "code_insee": "97101", "surf_parc": "3.00"},
        {"pacage": "PAC1", "code_insee": "97101", "surf_parc": "3.00"},
    ])
    parc = pd.DataFrame({"COMMUNE": [97101, 97101], "SURF_HA": [3.0, 3.0]},
                        index=["P1", "P2"])
    join = build_geometry_join(parc, pd.Series({"P1": "E1", "P2": "E1"}), layer)
    assert len(join.polygons) == 2
    # Both plots share commune AND surface, so which polygon each got is arbitrary -- the
    # count is what the map's caveat is built on.
    assert join.ambiguous_plots == 2


# --- rendering -------------------------------------------------------------------


def test_map_figure_builds_and_colours_by_family():
    polygons = {"P1": Polygon(rings=SQUARE), "P2": Polygon(rings=TRIANGLE)}
    fig = maps.build_map_figure(
        polygons, {"P1": "CS_BT_NISM", "P2": "BA_INT"}, title="t"
    )
    assert fig.axes
    assert maps.group_color("CS_BT_NISM") == maps.GROUP_COLORS["CS"]
    assert maps.group_color("BA_INT") == maps.GROUP_COLORS["BA"]


def test_an_unallocated_plot_is_drawn_not_dropped():
    # A hole in the map reads as missing data; it means unused land.
    polygons = {"P1": Polygon(rings=SQUARE)}
    fig = maps.build_map_figure(polygons, {}, title="t")
    (collection,) = [c for c in fig.axes[0].collections]
    assert len(collection.get_paths()) == 1


def test_change_figure_separates_kept_from_changed():
    polygons = {"P1": Polygon(rings=SQUARE), "P2": Polygon(rings=TRIANGLE)}
    fig = maps.build_change_figure(
        polygons,
        {"P1": "CS_BT_NISM", "P2": "CS_BT_NISM"},
        {"P1": "CS_NGT_NIM", "P2": "BA_INT"},  # P1 stays cane, P2 becomes banana
        title="t",
    )
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "inchangé (1)" in labels
    assert "changé (1)" in labels


def test_shared_bounds_spans_every_polygon():
    polygons = {"P1": Polygon(rings=SQUARE), "P2": Polygon(rings=TRIANGLE)}
    assert maps.shared_bounds(polygons) == (0.0, 0.0, 30.0, 10.0)


def test_filter_polygons_keeps_only_the_requested_plots():
    polygons = {"P1": Polygon(rings=SQUARE), "P2": Polygon(rings=TRIANGLE)}
    assert set(maps.filter_polygons(polygons, {"P2"})) == {"P2"}
    assert maps.filter_polygons(polygons, None) is polygons
