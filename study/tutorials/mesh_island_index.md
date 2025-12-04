# Geometry Nodes: Marking Mesh Islands and Driving Materials (Blender 5.0)

![Geometry Nodes : Mesh Island Node](geoNodes_meshIsland_a001_b001_v002-ss2.png)

This tutorial walks through the node tree shown in the screenshot and explains how it stores a mesh-island index as a named attribute, uses that index to isolate islands, and assigns material slots per island. The goal is to understand the intent behind each node so you can adapt the pattern to your own meshes.

## What the graph does

- Computes a connected-component ("mesh island") index for every element of the incoming geometry.
- Stores that index as a reusable named attribute `mesh_island_index` on the point domain.
- Builds selections from the stored index (e.g., keep only islands that match a target ID).
- Optionally offsets the index to drive material slot numbers, then writes it with **Set Material Index**.
- Uses **Viewer** nodes to inspect both the field values and the geometry after filtering.

## Node-by-node logic

1. **Group Input → Mesh Island**
   - The **Mesh Island** node computes two fields: the per-element `Island Index` and the total `Island Count`.
   - Feeding the whole geometry in ensures every connected component gets a stable integer label.

2. **Store Named Attribute** (Integer, Point domain, Name = `mesh_island_index`)
   - Writes the `Island Index` field onto the geometry as a named attribute on points.
   - Storing on points makes the value available to face/edge selections (fields flow upward in domain).
   - Result: every point (and therefore every face) knows which island it belongs to via `mesh_island_index`.

3. **Not Equal** (A = `mesh_island_index`, B = 0)
   - Creates a boolean selection where the island ID is **not** zero. Changing `B` targets a different island.
   - This selection can be reused for filtering or for limiting downstream material assignment.

4. **Delete Geometry** (Domain: Face, Selection = Not Equal result)
   - Deletes faces that pass the selection (islands ≠ target). The Viewer attached here shows only the kept island(s), useful for debugging which IDs you are selecting.

5. **Named Attribute** (Attribute = `mesh_island_index`)
   - Reads back the stored index anywhere downstream. Its **Exists** output is handy to guard against missing attributes in more complex setups.

6. **Add** (A = `mesh_island_index`, B = 1)
   - Offsets the island index by 1 before assigning materials. This prevents using material slot 0 if you want to reserve it, and ensures each island maps to a distinct slot.

7. **Set Material Index** (Selection optional, Material Index = Add result)
   - Writes the computed material slot index onto faces. If you plug the same Not Equal selection here, only the chosen islands receive the material change; leave it empty to affect all islands.

8. **Group Output**
   - Outputs the geometry with the island index attribute embedded and (optionally) per-island material slots applied.

## How to use or adapt this setup

- **Target a different island**: change the `B` value on **Not Equal** (e.g., set to 2 to isolate island ID 2). Swap **Not Equal** for **Equal** if you prefer an explicit match test.
- **Assign unique materials per island**: keep the **Add** node and ensure you have enough material slots on the object. Slot number = `mesh_island_index + 1` in this graph.
- **Debug island IDs**: connect a **Viewer** to the `Island Index` output of **Mesh Island** or to the **Named Attribute** node. Hovering in the spreadsheet helps reveal which IDs belong to which pieces.
- **Change attribute domain**: if your downstream logic works on faces, you can store the attribute on the Face domain instead of Point; keep it consistent with where you consume it.
- **Preserve the attribute**: because the value is stored with **Store Named Attribute**, it survives through later modifiers/operations and can be read in other node groups via the same name `mesh_island_index`.

## Concepts reinforced

- Using **Mesh Island** to label connected components.
- Persisting fields with **Store Named Attribute** for reuse downstream or in other modifiers.
- Building selections from integer attributes with compare nodes.
- Assigning material slots procedurally by deriving indices from geometry attributes.

With this pattern you can quickly isolate, visualize, and materialize individual mesh islands in Blender 5.0, and reuse the stored attribute wherever you need it.
