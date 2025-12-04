# Setting Diffuse Color Property on Materials using blender-mcp

## Prompt
Also set the corresponding diffuse_color property to the corresponding base color.

## Thinking
The user wants to set the `diffuse_color` property on materials 2-4 to match their base colors (red, green, blue). The `diffuse_color` property is a legacy material property in Blender that's separate from the shader node colors. To accomplish this, I need to:
1. Access the active object and its materials 2-4
2. Set the `diffuse_color` property on each material to the corresponding RGB color
3. Use the same color values as the base colors (red, green, blue)

The approach is to use the blender-mcp MCP server to execute Python code that:
- Iterates through materials 2-4
- Sets the `diffuse_color` property directly on the material object
- Uses the same RGBA tuples as the shader base colors

## Tool Calling
Using `mcp_my-blender-mc_execute_blender_code` to run Python code that sets material properties.

## MCP Server Output

### Python Code Executed
```python
import bpy

# Get the active object
obj = bpy.context.active_object

if obj is not None and len(obj.data.materials) >= 4:
    # Set colors for materials 2, 3, 4 (indices 1, 2, 3)
    colors = [
        (1.0, 0.0, 0.0, 1.0),  # Red
        (0.0, 1.0, 0.0, 1.0),  # Green
        (0.0, 0.0, 1.0, 1.0),  # Blue
    ]
    
    for i, color in enumerate(colors, start=1):
        mat = obj.data.materials[i]
        # Set diffuse_color property
        mat.diffuse_color = color
        print(f"Material_{i+1}: diffuse_color set to {['Red', 'Green', 'Blue'][i-1]}")
else:
    print("Active object doesn't have enough materials")
```

### Execution Output
```
Material_2: diffuse_color set to Red
Material_3: diffuse_color set to Green
Material_4: diffuse_color set to Blue
```

## Summary
Successfully set the `diffuse_color` property for materials 2-4:
- Material_2: diffuse_color = (1.0, 0.0, 0.0, 1.0) - Red
- Material_3: diffuse_color = (0.0, 1.0, 0.0, 1.0) - Green
- Material_4: diffuse_color = (0.0, 0.0, 1.0, 1.0) - Blue

The `diffuse_color` property is now synchronized with the shader base colors, ensuring consistency across both the legacy material properties and the modern shader node system.
