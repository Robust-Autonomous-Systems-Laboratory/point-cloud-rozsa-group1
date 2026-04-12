#!/usr/bin/env python3
"""
Convert a binary PLY point cloud to a decimated LAZ file.

Reads x, y, z, intensity from a binary PLY file, applies voxel grid
decimation to reduce point count, and writes a LAS 1.2 LAZ file.

Requires: numpy, laspy, laszip
  sudo apt install python3-laspy python3-laszip

Usage:
    python3 scripts/ply_to_laz.py <input.ply> <output.laz> [--voxel-size 0.04]
"""

import argparse
import os
import sys

import numpy as np
import laspy


PLY_TO_NUMPY = {
    'float': np.float32, 'float32': np.float32,
    'double': np.float64, 'float64': np.float64,
    'int': np.int32, 'int32': np.int32,
    'uint': np.uint32, 'uint32': np.uint32,
    'short': np.int16, 'int16': np.int16,
    'ushort': np.uint16, 'uint16': np.uint16,
    'char': np.int8, 'int8': np.int8,
    'uchar': np.uint8, 'uint8': np.uint8,
}


def read_ply(path):
    """Read a binary PLY file, return (points_structured_array, field_names)."""
    with open(path, 'rb') as f:
        fields = []
        n_points = 0
        fmt = None
        while True:
            line = f.readline().decode('ascii', errors='ignore').strip()
            if line == 'end_header':
                break
            parts = line.split()
            if parts[0] == 'format':
                fmt = parts[1]
            elif parts[0] == 'element' and parts[1] == 'vertex':
                n_points = int(parts[2])
            elif parts[0] == 'property':
                fields.append((parts[1], parts[2]))  # (type, name)
        raw = f.read()

    if fmt not in ('binary_little_endian', 'binary_big_endian'):
        sys.exit(f"ERROR: only binary PLY supported (got '{fmt}')")

    byteorder = '<' if 'little' in fmt else '>'
    dtype = np.dtype(
        [(name, PLY_TO_NUMPY.get(t, np.float32)) for t, name in fields]
    )
    if byteorder == '>':
        dtype = dtype.newbyteorder('>')

    pts = np.frombuffer(raw, dtype=dtype, count=n_points)
    field_names = [name for _, name in fields]
    return pts, field_names, n_points


def voxel_decimate(pts, voxel_size):
    """Keep one point per voxel cell. Returns index array into pts."""
    xs = pts['x'].astype(np.float64)
    ys = pts['y'].astype(np.float64)
    zs = pts['z'].astype(np.float64)

    vx = np.floor(xs / voxel_size).astype(np.int64)
    vy = np.floor(ys / voxel_size).astype(np.int64)
    vz = np.floor(zs / voxel_size).astype(np.int64)

    # Hash voxel coordinates to a single key. Large prime multipliers to
    # reduce collisions across the expected coordinate range.
    keys = vx * 10_000_003 + vy * 10_003 + vz
    _, idx = np.unique(keys, return_index=True)
    return idx


def convert(ply_path, laz_path, voxel_size):
    print(f"Reading {ply_path} ...")
    pts, field_names, n_total = read_ply(ply_path)
    print(f"  {n_total:,} points, fields: {field_names}")

    print(f"Voxel decimating at {voxel_size} m ...")
    idx = voxel_decimate(pts, voxel_size)
    kept = pts[idx]
    n_kept = len(idx)
    print(f"  {n_kept:,} points retained ({n_kept / n_total * 100:.1f}%)")

    xs = kept['x'].astype(np.float64)
    ys = kept['y'].astype(np.float64)
    zs = kept['z'].astype(np.float64)

    print(f"Writing {laz_path} ...")
    header = laspy.LasHeader(point_format=0, version='1.2')
    header.offsets = np.array([xs.min(), ys.min(), zs.min()])
    header.scales = np.array([0.001, 0.001, 0.001])

    las = laspy.LasData(header=header)
    las.x = xs
    las.y = ys
    las.z = zs

    if 'intensity' in field_names:
        raw_i = kept['intensity'].astype(np.float64)
        i_max = float(raw_i.max())
        if i_max <= 1.0:
            las.intensity = np.clip(raw_i * 65535.0, 0, 65535).astype(np.uint16)
        else:
            las.intensity = np.clip(raw_i, 0, 65535).astype(np.uint16)
    else:
        las.intensity = np.zeros(n_kept, dtype=np.uint16)

    las.write(laz_path, laz_backend=laspy.LazBackend.Laszip)

    size_mb = os.path.getsize(laz_path) / 1024 / 1024
    print(f"Done: {laz_path}  ({size_mb:.1f} MB, {n_kept:,} points)")


def main():
    parser = argparse.ArgumentParser(
        description='Convert binary PLY to decimated LAZ.'
    )
    parser.add_argument('input_ply', help='Input binary PLY file')
    parser.add_argument('output_laz', help='Output LAZ file')
    parser.add_argument(
        '--voxel-size', type=float, default=0.04,
        help='Voxel grid size in metres for decimation (default: 0.04). '
             'Larger = fewer points = smaller file.'
    )
    args = parser.parse_args()
    convert(args.input_ply, args.output_laz, args.voxel_size)


if __name__ == '__main__':
    main()
