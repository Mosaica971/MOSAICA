"""A minimal ESRI shapefile reader: polygons and their attribute table, nothing else.

Written rather than pulled in, on purpose. The alternative is geopandas, which drags GDAL
behind it -- a heavy, platform-specific install for a repo whose only geographic need is to
draw parcel outlines. The shapefile format is small, frozen since 1998 and fully published,
and the two files that matter here (.shp for geometry, .dbf for attributes) are simple binary
records. This module reads exactly the subset the dashboard needs and refuses the rest loudly.

Coordinates are returned in the file's own projected units, untransformed. The Guadeloupe RPG
is in WGS84 / UTM 20N (metres), so plotting x against y is already a correct equal-scale map
at this extent; no reprojection, hence no pyproj.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Shape type codes we accept. Everything else (points, polylines, multipatch, Z/M variants)
# would need different parsing and is not what a parcel layer contains.
_POLYGON = 5
_POLYGON_Z = 15
_POLYGON_M = 25
_ACCEPTED = {_POLYGON, _POLYGON_Z, _POLYGON_M}
_NULL_SHAPE = 0


@dataclass(frozen=True)
class Polygon:
    """One shapefile record: its rings, in file order, as lists of (x, y).

    A shapefile polygon may hold several rings -- outer boundaries and holes, distinguished
    by winding order. For drawing an outline they can all be stroked as-is, which is what the
    dashboard does; nothing here interprets holes.
    """

    rings: list[list[tuple[float, float]]]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        xs = [x for ring in self.rings for x, _ in ring]
        ys = [y for ring in self.rings for _, y in ring]
        if not xs:
            return (0.0, 0.0, 0.0, 0.0)
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def centroid(self) -> tuple[float, float]:
        """Centroid of the first (outer) ring by the shoelace formula, falling back to the
        mean vertex when the ring has zero area."""
        if not self.rings or len(self.rings[0]) < 3:
            return (0.0, 0.0)
        ring = self.rings[0]
        area = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        if area == 0:
            n = len(ring)
            return (sum(x for x, _ in ring) / n, sum(y for _, y in ring) / n)
        return (cx / (3.0 * area), cy / (3.0 * area))


def read_polygons(path: str | Path) -> list[Polygon | None]:
    """Every record of a .shp, in file order. A null shape yields None so the list stays
    aligned with the .dbf rows -- position IS the join between the two files."""
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 100:
        raise ValueError(f"{path.name}: file too short to be a shapefile")
    file_type = struct.unpack("<i", data[32:36])[0]
    if file_type not in _ACCEPTED and file_type != _NULL_SHAPE:
        raise ValueError(
            f"{path.name}: shape type {file_type} is not a polygon layer "
            f"(accepted: {sorted(_ACCEPTED)})"
        )

    shapes: list[Polygon | None] = []
    offset = 100  # past the 100-byte header
    total = len(data)
    while offset + 8 <= total:
        # Record header is big-endian: record number, then content length in 16-bit words.
        _, content_words = struct.unpack(">ii", data[offset:offset + 8])
        offset += 8
        end = offset + content_words * 2
        if end > total:
            break
        shapes.append(_parse_polygon(data, offset, end))
        offset = end
    return shapes


def _parse_polygon(data: bytes, start: int, end: int) -> Polygon | None:
    shape_type = struct.unpack("<i", data[start:start + 4])[0]
    if shape_type == _NULL_SHAPE:
        return None
    if shape_type not in _ACCEPTED:
        return None
    # Layout: type(4) bbox(32) numParts(4) numPoints(4) parts(4*n) points(16*m)
    num_parts, num_points = struct.unpack("<ii", data[start + 36:start + 44])
    parts_at = start + 44
    parts = list(struct.unpack(f"<{num_parts}i", data[parts_at:parts_at + 4 * num_parts]))
    points_at = parts_at + 4 * num_parts
    coords = struct.unpack(
        f"<{2 * num_points}d", data[points_at:points_at + 16 * num_points]
    )

    rings: list[list[tuple[float, float]]] = []
    boundaries = parts + [num_points]
    for first, last in zip(boundaries, boundaries[1:]):
        ring = [(coords[2 * i], coords[2 * i + 1]) for i in range(first, last)]
        if ring:
            rings.append(ring)
    return Polygon(rings=rings) if rings else None


def read_dbf(path: str | Path) -> list[dict[str, str]]:
    """The attribute table as a list of {field: text}, in file order.

    Everything is returned as stripped text: the dBASE numeric type is itself stored as
    text, and deciding what is a number belongs to the caller, which knows the column.
    """
    path = Path(path)
    with open(path, "rb") as handle:
        header = handle.read(32)
        if len(header) < 32:
            raise ValueError(f"{path.name}: truncated dBASE header")
        record_count, header_length, record_length = struct.unpack("<IHH", header[4:12])

        fields: list[tuple[str, int]] = []
        while True:
            descriptor = handle.read(32)
            if not descriptor or descriptor[0:1] in (b"\r", b"\x00", b""):
                break
            name = descriptor[0:11].split(b"\x00")[0].decode("latin-1")
            fields.append((name, descriptor[16]))

        handle.seek(header_length)
        rows = []
        for _ in range(record_count):
            raw = handle.read(record_length)
            if len(raw) < record_length:
                break
            position = 1  # first byte is the deletion flag
            row: dict[str, str] = {}
            for name, width in fields:
                row[name] = raw[position:position + width].decode("latin-1").strip()
                position += width
            rows.append(row)
    return rows


def read_layer(shp_path: str | Path) -> tuple[list[Polygon | None], list[dict[str, Any]]]:
    """(geometries, attributes) of one layer, aligned by position -- which is how a
    shapefile relates its two files: the nth record of the .shp belongs to the nth row of
    the .dbf. Raises if the two disagree, because a silent misalignment would draw every
    parcel with its neighbour's data."""
    shp_path = Path(shp_path)
    shapes = read_polygons(shp_path)
    rows = read_dbf(shp_path.with_suffix(".dbf"))
    if len(shapes) != len(rows):
        raise ValueError(
            f"{shp_path.name}: {len(shapes)} geometries against {len(rows)} attribute rows "
            f"-- the layer is inconsistent and cannot be joined by position"
        )
    return shapes, rows
