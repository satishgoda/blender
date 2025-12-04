# Geometry Nodes Analysis using blender-mcp

## Prompt
Study the geometry node network on the active object and write a summary of the setup.

## Thinking
The user wants to understand the geometry nodes modifier setup on the active object in Blender. To accomplish this, I need to:
1. Access the active object in Blender
2. Find the geometry nodes modifier
3. Analyze the node tree structure including nodes and their connections
4. Document the flow and purpose of the network

The approach is to use the blender-mcp MCP server to execute Python code that introspects the geometry nodes modifier and reports on:
- The modifier name and node group
- All nodes in the tree with their types and inputs/outputs
- All links between nodes showing how data flows

## Tool Calling
Using `mcp_my-blender-mc_execute_blender_code` to run Python code that analyzes the geometry nodes network.

## MCP Server Output

### Python Code Executed
```python
import bpy

# Get the active object
obj = bpy.context.active_object

if obj is not None:
    # Check if object has a geometry nodes modifier
    geo_mod = None
    for mod in obj.modifiers:
        if mod.type == 'NODES':
            geo_mod = mod
            break
    
    if geo_mod is not None:
        node_tree = geo_mod.node_group
        print(f"Geometry Nodes Setup for {obj.name}:")
        print(f"{'='*50}")
        print(f"Modifier: {geo_mod.name}")
        print(f"Node Group: {node_tree.name}")
        print(f"\nNodes ({len(node_tree.nodes)}):")
        print("-" * 50)
        
        for node in node_tree.nodes:
            print(f"  • {node.name} (type: {node.bl_idname})")
            if hasattr(node, 'inputs') and len(node.inputs) > 0:
                for inp in node.inputs:
                    print(f"      Input: {inp.name}")
            if hasattr(node, 'outputs') and len(node.outputs) > 0:
                for out in node.outputs:
                    print(f"      Output: {out.name}")
        
        print(f"\nLinks ({len(node_tree.links)}):")
        print("-" * 50)
        for link in node_tree.links:
            from_node = link.from_node.name
            from_socket = link.from_socket.name
            to_node = link.to_node.name
            to_socket = link.to_socket.name
            print(f"  {from_node}.{from_socket} → {to_node}.{to_socket}")
    else:
        print(f"No geometry nodes modifier found on {obj.name}")
else:
    print("No active object selected")
```

### Execution Output
```
Geometry Nodes Setup for Suzanne:
==================================================
Modifier: GeometryNodes
Node Group: Geometry Nodes

Nodes (9):
--------------------------------------------------
  • Group Input (type: NodeGroupInput)
      Output: Geometry
      Output: 
  • Group Output (type: NodeGroupOutput)
      Input: Geometry
      Input: 
  • Mesh Island (type: GeometryNodeInputMeshIsland)
      Output: Island Index
      Output: Island Count
  • Store Named Attribute (type: GeometryNodeStoreNamedAttribute)
      Input: Geometry
      Input: Selection
      Input: Name
      Input: Value
      Output: Geometry
  • Viewer (type: GeometryNodeViewer)
      Input: Geometry
      Input: Island Index
      Input: 
  • Set Material Index (type: GeometryNodeSetMaterialIndex)
      Input: Geometry
      Input: Selection
      Input: Material Index
      Output: Geometry
  • Math (type: ShaderNodeMath)
      Input: Value
      Input: Value
      Input: Value
      Output: Value
  • Frame (type: NodeFrame)
  • Frame.001 (type: NodeFrame)

Links (8):
--------------------------------------------------
  Group Input.Geometry → Store Named Attribute.Geometry
  Mesh Island.Island Index → Store Named Attribute.Value
  Store Named Attribute.Geometry → Viewer.Geometry
  Mesh Island.Island Index → Viewer.Island Index
  Mesh Island.Island Index → Math.Value
  Math.Value → Set Material Index.Material Index
  Set Material Index.Geometry → Group Output.Geometry
  Group Input.Geometry → Set Material Index.Geometry
```

## Analysis Summary

### Network Purpose
The geometry nodes network on the Suzanne object automatically assigns different materials to disconnected mesh islands. This is a data-driven material assignment system that uses mesh topology analysis.

### Node Architecture

#### Input/Output Layer
- **Group Input**: Receives the base mesh geometry
- **Group Output**: Outputs the final processed geometry with material indices assigned

#### Analysis Layer
- **Mesh Island**: Analyzes the mesh topology to identify separate, disconnected components
  - Output: Island Index (which island each face belongs to)
  - Output: Island Count (total number of islands)

#### Data Storage Layer
- **Store Named Attribute**: Preserves the island index information as a named attribute on the geometry for later reference

#### Processing Layer
- **Math Node**: Processes/transforms the island index values (likely for calculations or remapping)

#### Application Layer
- **Set Material Index**: Assigns the processed material indices to the geometry based on the computed values

#### Visualization Layer
- **Viewer**: Displays the geometry and island indices for debugging and real-time visualization

#### Organization
- Two **Frame** nodes organize nodes visually in the editor

### Data Flow
```
Group Input Geometry
    ↓
    ├→ Store Named Attribute (stores island index as attribute)
    │   ↓
    │   Viewer (displays for debugging)
    │
    └→ Set Material Index (receives original geometry)
        ↑
        └─ Math Node (processes island index)
            ↑
            └─ Mesh Island (identifies islands)
    
    Final output to Group Output
```

### Key Features
1. **Automatic Island Detection**: Uses Mesh Island node to identify topology
2. **Attribute Storage**: Preserves island data for reference
3. **Value Processing**: Math operations allow flexible material assignment logic
4. **Material Assignment**: Material indices are computed and applied to faces
5. **Live Preview**: Viewer node provides real-time visual feedback
