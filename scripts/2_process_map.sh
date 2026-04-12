#!/usr/bin/env bash
# =============================================================================
# Step 2: Crop, export, decimate, and convert a .mm map to Potree format.
#
# Usage:
#   bash scripts/2_process_map.sh <path/to/map.mm> [voxel_size_m]
#
# Arguments:
#   map.mm        -- metric map produced by 1_run_slam.sh
#   voxel_size_m  -- voxel decimation size in meters (default: 0.04)
#                    Larger = fewer points = smaller file. Try 0.04–0.10.
#
# Output:
#   pointclouds/<map_name>/   -- Potree tiles ready for GitHub Pages
# =============================================================================

set -e

if [ -z "$1" ]; then
    echo "Usage: bash scripts/2_process_map.sh <path/to/map.mm> [voxel_size_m]"
    exit 1
fi

MM="$1"
VOXEL="${2:-0.04}"

if [ ! -f "$MM" ]; then
    echo "Error: map file not found: $MM"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
NAME="$(basename "$MM" .mm)"

source /opt/ros/jazzy/setup.bash

echo "=== Step 2a: Crop map to bounding box ==="
echo "  Using filter: ${SCRIPT_DIR}/crop_filter.yaml"
mm-filter \
  -i "$MM" \
  -p "${SCRIPT_DIR}/crop_filter.yaml" \
  -o "${NAME}_cropped.mm"

echo ""
echo "=== Step 2b: Export cropped map to PLY ==="
# Note: mm2ply may print a warning/error about the empty 'raw' layer — this is normal.
# The map_cropped layer is written before that error occurs.
mm2ply \
  -i "${NAME}_cropped.mm" \
  -o "${NAME}" \
  --export-fields x,y,z,intensity \
  -b || true

PLY="${NAME}_map_cropped.ply"
if [ ! -f "$PLY" ]; then
    echo "Error: expected PLY file not found: $PLY"
    echo "Check that 'map_cropped' layer exists in ${NAME}_cropped.mm (run mm-info to verify)."
    exit 1
fi

echo ""
echo "=== Step 2c: Decimate and convert to LAZ (voxel size: ${VOXEL} m) ==="
python3 "${SCRIPT_DIR}/ply_to_laz.py" \
  "$PLY" \
  "${NAME}.laz" \
  --voxel-size "$VOXEL"

echo ""
echo "=== Step 2d: Convert LAZ to Potree tiles ==="
mkdir -p "${REPO_DIR}/pointclouds"
LD_LIBRARY_PATH="${REPO_DIR}:${LD_LIBRARY_PATH}" \
  "${REPO_DIR}/PotreeConverter" \
  "${NAME}.laz" \
  -o "${REPO_DIR}/pointclouds/${NAME}"

echo ""
echo "================================================================"
echo "Done! Potree tiles written to: pointclouds/${NAME}/"
echo ""
echo "Next steps:"
echo "  1. Edit index.html — replace YOUR_MAP_NAME with: ${NAME}"
echo "  2. Commit and push:"
echo "       git add pointclouds/${NAME} index.html"
echo "       git commit -m 'Add point cloud map: ${NAME}'"
echo "       git push"
echo "  3. Enable GitHub Pages (Settings → Pages → Deploy from branch → main, root /)"
echo "  4. View at: https://<your-username>.github.io/<your-repo>/"
echo "================================================================"
