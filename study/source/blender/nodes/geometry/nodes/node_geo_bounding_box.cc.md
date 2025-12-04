## Bounding Box Node — Practical Guide & Code Internals

✅ Summary

The **Bounding Box** node computes the axis-aligned bounds of a geometry and gives you:
- Vector outputs: **Min** and **Max** (the bounding box corners). These are calculated ignoring instances by default — they operate on the realized geometry, which matters for many common node setups.
- Geometry output: **Bounding Box** — a cube mesh (a cuboid) that encloses the provided geometry. The node can output a differently sized cube for each unique sub-geometry (e.g., per-instance bounding boxes) if you realize or feed different geometry sets.

This short tutorial explains what the node does in code, demonstrates how to leverage the Min/Max outputs for practical transformations, and covers typical workflows (per-instance vs combined bounding box), tips, and example exercises.

---

## What the node does (high level)
- Computes axis-aligned bounds for the input geometry.
- `Min` and `Max` vector outputs are computed using a method called `compute_boundbox_without_instances(use_radius)` — the important bit here is _without instances_. That means if your input geometry is an instanced set, values are computed from the underlying geometry instead of from the instance transforms.
- If the geometry includes curves or point clouds and you want to consider their radius (like stroke width or point sizes), enable the `Use Radius` input.
- When the geometry output is requested, the node replaces each mesh in the geometry set with a cuboid mesh sized and transformed to fit the calculated bounds. The node uses one cuboid per unique geometry set, and because the node uses `foreach_real_geometry`, each unique geometry (including instances realized as separate geometry sets) can receive its own cuboid.

---

## How it is implemented (code notes)
The node implementation in `node_geo_bounding_box.cc` does three key steps:

1. Extract input geometry and `Use Radius` flag:

```cpp
GeometrySet geometry_set = params.extract_input<GeometrySet>("Geometry");
const bool use_radius = params.extract_input<bool>("Use Radius");
```

2. Compute Min/Max using `compute_boundbox_without_instances`. This returns a `Bounds<float3>` optional (min/max) that ignores instances for Min/Max outputs:

```cpp
const std::optional<Bounds<float3>> bounds =
		geometry_set.compute_boundbox_without_instances(use_radius);
if (!bounds) {
	params.set_output("Min", float3(0));
	params.set_output("Max", float3(0));
} else {
	params.set_output("Min", bounds->min);
	params.set_output("Max", bounds->max);
}
```

3. If the geometry output is required, the node iterates each real geometry set and either clears it (if there is no bounds) or creates a cuboid mesh to enclose the bounds for that sub-geometry. It calls `create_cuboid_mesh`, computes the cuboid `scale` = `max - min`, computes the `center`, transforms the cube, and replaces the original mesh with the cuboid:

```cpp
geometry::foreach_real_geometry(geometry_set, [&](GeometrySet &sub_geometry) {
	std::optional<Bounds<float3>> sub_bounds;

	if (&sub_geometry == &geometry_set) {
		sub_bounds = bounds;
	}
	else {
		sub_bounds = sub_geometry.compute_boundbox_without_instances(use_radius);
	}

	if (!sub_bounds) {
		sub_geometry.clear();
	}
	else {
		const float3 scale = sub_bounds->max - sub_bounds->min;
		const float3 center = sub_bounds->min + scale / 2.0f;
		Mesh *mesh = geometry::create_cuboid_mesh(scale, 2, 2, 2, "uv_map");
		geometry::transform_mesh(*mesh, center, math::Quaternion::identity(), float3(1));
		sub_geometry.replace_mesh(mesh);
		sub_geometry.keep_only({GeometryComponent::Type::Mesh, GeometryComponent::Type::Edit});
	}
});

params.set_output("Bounding Box", std::move(geometry_set));
```

Note: the nodes also use `propagate_all_instance_attributes()` on the Geometry output so instance attributes survive onto the new bounding box meshes.

---

## Practical workflows & where you might use the Bounding Box node

1) Centering / Aligning Geometry
- Problem: You want to align or center an object inside a scene or snap it to a surface.
- Pattern: Feed the geometry into the Bounding Box node, extract `Min` and `Max` and calculate the center: `(Min + Max) / 2`. Use `Set Position` (or a Transform node) to offset the object by that center, or set the translation property of a `Transform Geometry` node.

Example: move the geometry so it is centered on the origin.
Steps (Node setup):
- Geometry -> Bounding Box -> Min/Max
- Math (Add) -> Multiply -> Set Position (or a Transform Node)

Tip: Multiply the difference (Max - Min) by 0.5 and apply a negative translation if you want the mesh pivot at the corner or to account for flipped axes in your setup.

2) Generate Per-Instance boxes (visualize instance bounds)
- Problem: You have instanced geometry (e.g., many cones or objects) and want bounding boxes for each instance to manipulate them individually or detect overlap.
- Pattern: Either: (A) Use **Instance on Points** with a geometry that contains a mesh and the bounding box node to generate per-instance geometry. Or (B) Realize instances first (Realize Instances node), then feed the realized geometry into Bounding Box to produce a cuboid per realized instance.

Important detail (from the code): Min/Max outputs ignore instances (they compute the bounds on the underlying geometry), but the per-instance cuboid geometry is constructed for each unique geometry set due to `foreach_real_geometry`.

Example: Use **Distribute Points on Faces** → **Instance on Points** → Bounding Box → (Per-instance boxes). If you want a **combined** bounding box for all instances, Realize Instances first, then feed geometry to Bounding Box.

3) Automatic collision proxies / LOD placeholders
- Problem: Physics or LOD setups require simple proxies: neutral boxes are fast to collide with or represent complex geometry at low cost.
- Pattern: Use Bounding Box geometry output as a proxy mesh. Because the bounding box geometry is a simple cube per unique geometry set, you can use it as a collider proxy, for LODs, or as an optimization in viewport logic.

4) Size-driven procedural design (fit geometry to bounds)
- Problem: Instance a decorative object and scale or align it according to its bounding box so objects fit inside areas, like boxes inside chests, or fit models to adapt to different instances.
- Pattern: Min/Max outputs give the scale and center (scale = Max - Min; center = (Min + Max) / 2). Feed this into transforms, Set Position, or Instance scale inputs to adapt objects automatically to their own bounding box.

---

## Visual examples (inspired by your screenshots)

The screenshots you provided show two useful setups. The examples below are step-by-step recreations in Node terms.

Example A — Center geometry with a mirrored offset (top image):
1. Input geometry: any mesh.
2. Nodes: Bounding Box -> Min/Max -> Multiply (flip axes if needed) -> Set Position -> Transform Geometry -> Output.
3. Use Multiply to invert selected components, or to offset in particular directions. The bounding box center lets you accurately control where geometry goes with `Set Position`.

Example B — Per-Instance Bounding Box vs Combined Bounding Box (bottom image):
1. Input mesh (Group Input) → Distribute Points on Faces → Instance on Points → Realize Instances (optional for combined) → Bounding Box.
2. If you want per-instance boxes: feed the instanced geometry to `Instance on Points` and connect the **Bounding Box** to the Instances geometry input (per-instance behavior depends on how your graph constructs geometry sets).
3. If you want one combined bounding box for all instances: add **Realize Instances** before Bounding Box. The node will treat the resulting collection as a single geometry and compute a combined `Min/Max`.
4. To switch between modes: you can use a **Switch** node or **Menu Switch** pattern in the Geometry Node graph to switch sources (Direct Instances vs Realized Instances) for the Bounding Box input.

The screenshots show a `Menu Switch` that selects between the `Per-Instance` bounding boxes and the `Combined` bounding box via which geometry stream is passed to the same downstream nodes.

---

## Tips, Tricks & Gotchas
- Vector outputs `Min/Max` are computed _without instances_. If you need per-instance Min/Max, compute bounds after realizing instances or use the per-sub-geometry cuboid output and read attributes if you store them.
- `Use Radius`: set this to true to account for curve radii, Grease Pencil point radius, and point cloud radius. This matters a lot when the visual geometry is padded by thickness/point size (so the bounding box includes stroke width or point sizes).
- Per-sub-geometry: The bounding box geometry output is generated per unique geometry set. When instances share geometry but are transformed differently, the node can produce cuboids for each transformed geometry set when used in combination with instance realization or instance propagation.
- Empty geometry: If a geometry set has no bounds or is empty, the node writes float3(0) into the vector outputs and clears the geometry produced for that set.
- Keep only Mesh + Edit components: The Bounding Box output clears unnecessary components and keeps only Mesh/Edit types, so the output is simplified into clean bounding geometry.

---

## Exercises for the PDF and example files (progressive)

Exercise 1 — Center Mesh on floor
1. Create a simple cube or mesh, feed it into the Bounding Box node.
2. Use Min/Max to compute the center and move the object so its base (Min.y) is exactly at Y=0 (the floor).
3. Optional: Add a Scale node so the object is scaled to match a target box via `(target_size / (Max - Min))`.

Exercise 2 — Per-instance bounding box visualizer
1. Distribute points on a mesh and Instance a varied set of objects on those points.
2. Use Instance on Points to place instances.
3. Feed the instances directly into Bounding Box to generate boxes for each instance (or Realize Instances first to compute a single combined bounding box).
4. Use the boxes to detect overlap or to feed other logic that depends on instance sizes.

Exercise 3 — Radius-aware bounds for curves and points
1. Use a point cloud or a curve with variable radius/stroke.
2. Enable `Use Radius` in Bounding Box.
3. Compare Min/Max vector results with and without the `Use Radius` feature to see the difference in bounds when point/curve thickness is relevant.

Exercise 4 — Proxy geometry for physics or LOD
1. Convert a large, complex geometry to a simple proxy by feeding it to Bounding Box and using the output as a collision or simplified visual placeholder.
2. Use the Min/Max/Scale to control object size and physics properties.

---

## Final notes & Selling the idea
- The Bounding Box node is small but powerful — it lets you extract a succinct numeric representation (Min/Max) for programmatic manipulation and generates simple geometry proxies suitable for many workflows.
- This node is essential for any of the following: automatic alignment (snap, center), per-instance transform logic (fit, scale), collision/LOD proxies, and debugging visual feedback in procedural systems.
- The examples and exercises above can be used as lesson modules in a PDF, along with downloadable `.blend` files to reproduce the exact results from the screenshots. Try to include both the `Per-Instance` and `Realize Instances` variations in the examples — they teach the key behavioral distinction of the node (instances vs realized geometry).
- If you'd like, I can also generate ready-to-download `.blend` example files for each exercise, or export the tutorial as a printable PDF ready for sale. Let me know which format you'd like next (PDF, ZIP of examples, step-by-step .blend files) and I’ll prepare them.

