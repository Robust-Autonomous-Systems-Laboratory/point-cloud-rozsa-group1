# EE5531 — Point Cloud Mapping Lab

In this lab you will process a LiDAR bag file into an interactive 3D point cloud map hosted on GitHub Pages.

**Pipeline overview:**
```
bag.mcap  →  MOLA SLAM  →  crop & filter  →  LAZ  →  Potree tiles  →  GitHub Pages
```

---

## Prerequisites

### On the lab machine (or your own Ubuntu machine with ROS 2 Jazzy)

```bash
# Python libraries for LAZ export
sudo apt install python3-laspy python3-laszip

# MOLA (already installed on the lab machine; for personal machines):
sudo apt install ros-jazzy-mola-lidar-odometry
```

### GitHub setup

1. Click **"Use this template"** on this repo to create your own copy.
2. Clone your repo to the lab machine:
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```
3. Enable GitHub Pages: **Settings → Pages → Deploy from branch → `main`, root `/`**.  
   Your viewer will be live at `https://<your-username>.github.io/<your-repo>/`.

---

## Step 1 — Run MOLA SLAM

Run the SLAM pipeline on your bag file. This takes 5–20 minutes depending on bag length.

```bash
bash scripts/1_run_slam.sh <path/to/your_bag.mcap>
```

**What it does:**
- Runs LiDAR odometry (`mola-lidar-odometry-cli`) to build a simple map of poses + scans
- Converts to a metric map (`.mm` file) with static/dynamic point separation
- Prints the map's bounding box at the end — **note these values for the next step**

**Outputs:** `your_bag.mcap.simplemap`, `your_bag.mcap.mm`, `trajectory.tum`

---

## Step 2 — Choose your crop region

The SLAM map covers the robot's full trajectory. You'll crop it to a region of interest.

Open `scripts/crop_filter.yaml` and edit the bounding box to match the area you want to keep.  
Use the **X/Y/Z bounds printed by Step 1** as a guide.

```yaml
filters:
  - class_name: mp2p_icp_filters::FilterBoundingBox
    params:
      input_pointcloud_layer: "map"
      inside_pointcloud_layer: "map_cropped"
      bounding_box_min: [-50.0, -50.0, -50.0]   # ← edit these
      bounding_box_max: [ 50.0,  50.0,  50.0]   # ← edit these
```

Tips:
- A **±50 m cube** (100 m on each side) works well for a typical campus walk.
- Check the Z bounds from `mm-info` — you probably don't need more than ±10 m vertically.
- Run `mm-info your_bag.mcap.mm` at any time to re-check bounds.

---

## Step 3 — Process the map

Convert the `.mm` file to Potree tiles ready for the web.

```bash
bash scripts/2_process_map.sh <path/to/your_bag.mcap.mm>
```

Optional: pass a voxel decimation size (default `0.04` m ≈ 10 MB output):
```bash
bash scripts/2_process_map.sh your_bag.mcap.mm 0.06   # fewer points, smaller file
bash scripts/2_process_map.sh your_bag.mcap.mm 0.02   # more points, larger file
```

**What it does:**
| Sub-step | Tool | Output |
|---|---|---|
| Crop to bounding box | `mm-filter` | `*_cropped.mm` |
| Export to PLY | `mm2ply` | `*_map_cropped.ply` |
| Decimate + convert to LAZ | `scripts/ply_to_laz.py` | `*.laz` |
| Convert to Potree tiles | `PotreeConverter` | `pointclouds/<name>/` |

**Output:** `pointclouds/<your_map_name>/` — this is what you upload to GitHub.

---

## Step 4 — Update the viewer

Edit `index.html` and replace `YOUR_MAP_NAME` with the folder name printed at the end of Step 3:

```javascript
// Before:
Potree.loadPointCloud("./pointclouds/YOUR_MAP_NAME/cloud.js", "map", e => {

// After (example):
Potree.loadPointCloud("./pointclouds/rosbag2_2026_04_09-19_50_35_0.mcap/cloud.js", "map", e => {
```

You can also update the description on this line:
```javascript
viewer.setDescription("EE5531 Point Cloud Map");
```

---

## Step 5 — Publish to GitHub Pages

```bash
git add pointclouds/ index.html
git commit -m "Add point cloud map"
git push
```

Wait ~60 seconds, then visit `https://<your-username>.github.io/<your-repo>/`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `mola-lidar-odometry-cli: command not found` | Run `source /opt/ros/jazzy/setup.bash` first, or use the lab machine |
| `No module named 'laspy'` | `sudo apt install python3-laspy python3-laszip` |
| `mm2ply` prints an error about `raw` layer | Normal — the `raw` layer is empty. The `map_cropped.ply` is still written correctly. |
| `PotreeConverter: error while loading shared libraries: liblaszip.so` | Must run from the repo root as shown (the script handles this automatically) |
| Blank page on GitHub Pages | Check that `pointclouds/<name>/cloud.js` exists in your repo and the path in `index.html` matches |
| Point cloud loads but looks wrong | Adjust `elevationRange` in `index.html` to match your Z bounds from `mm-info` |

---

## File reference

```
scripts/
  1_run_slam.sh       -- bag → .mm SLAM map
  2_process_map.sh    -- .mm → Potree tiles
  ply_to_laz.py       -- PLY → voxel decimated LAZ
  crop_filter.yaml    -- edit to set your crop region
  sm2mm_voxels_static_dynamic_points.yaml  -- map generation config (do not edit)
index.html            -- Potree viewer (edit YOUR_MAP_NAME)
PotreeConverter       -- Linux binary (included)
liblaszip.so          -- Required by PotreeConverter (included)
resources/            -- Potree viewer libraries (included, do not edit)
```
