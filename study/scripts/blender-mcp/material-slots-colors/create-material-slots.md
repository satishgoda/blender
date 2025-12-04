# Creating Material Slots using blender-mcp

## Prompt
Using blender-mcp, create 4 material slots on the active object

## Thinking
The user wants to add 4 material slots to the active object in Blender. To accomplish this, I need to:
1. Access the active object in Blender
2. Create 4 new materials
3. Append each material to the object's material slots

The approach is to use the blender-mcp MCP server to execute Python code that:
- Gets the active object context
- Creates 4 new materials with unique names
- Appends them to the object's material data

## Tool Calling
Using `mcp_my-blender-mc_execute_blender_code` to run Python code that creates and assigns materials.

## MCP Server Output

### Python Code Executed
```python
import bpy

# Get the active object
obj = bpy.context.active_object

if obj is not None:
    # Create 4 material slots
    for i in range(4):
        mat = bpy.data.materials.new(name=f"Material_{i+1}")
        obj.data.materials.append(mat)
    
    print(f"Created 4 material slots on {obj.name}")
    print(f"Total material slots: {len(obj.data.materials)}")
else:
    print("No active object selected")
```

### Execution Output
```
Created 4 material slots on Suzanne
Total material slots: 4
```

## Summary
Successfully created 4 material slots on the active object (Suzanne). Each slot has a unique material named Material_1, Material_2, Material_3, and Material_4. The object now has a total of 4 material slots assigned to it.
