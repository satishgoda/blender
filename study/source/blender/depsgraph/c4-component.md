# C4 Component Diagram - Blender Dependency Graph

This diagram shows the detailed internal components and their interactions.

## Component Diagram - Node System

```mermaid
C4Component
    title Component Diagram - Node System

    Container_Boundary(nodes, "Node System") {
        Component(node_base, "Node Base", "deg_node.hh", "Abstract base with relations, stats, type info")
        Component(id_node, "IDNode", "deg_node_id.hh", "Represents a data-block, contains components")
        Component(comp_node, "ComponentNode", "deg_node_component.hh", "Represents an aspect (Transform, Geometry)")
        Component(op_node, "OperationNode", "deg_node_operation.hh", "Atomic evaluation operation with callback")
        Component(time_node, "TimeSourceNode", "deg_node_time.hh", "Root time dependency node")
        Component(factory, "NodeFactory", "deg_node_factory.hh", "Creates typed nodes")
    }

    Component_Ext(relation, "Relation", "Directed edge between nodes")

    Rel(id_node, node_base, "Inherits from")
    Rel(comp_node, node_base, "Inherits from")
    Rel(op_node, node_base, "Inherits from")
    Rel(time_node, node_base, "Inherits from")

    Rel(id_node, comp_node, "Contains many")
    Rel(comp_node, op_node, "Contains many")

    Rel(factory, id_node, "Creates")
    Rel(factory, comp_node, "Creates")
    Rel(factory, op_node, "Creates")

    BiRel(node_base, relation, "Connected by")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Component Diagram - Builder System

```mermaid
C4Component
    title Component Diagram - Builder System

    Container_Boundary(builder_system, "Builder System") {
        Component(pipeline, "AbstractBuilderPipeline", "pipeline.h", "Base class for build orchestration")
        Component(node_builder, "DepsgraphNodeBuilder", "deg_builder_nodes.h", "Creates all graph nodes")
        Component(rel_builder, "DepsgraphRelationBuilder", "deg_builder_relations.h", "Creates all relations")
        Component(builder_cache, "DepsgraphBuilderCache", "deg_builder_cache.h", "Caches build-time data")
        Component(rna_builder, "RNANodeQueryIDData", "deg_builder_rna.h", "RNA path to node mapping")
    }

    Container_Boundary(pipelines, "Build Pipelines") {
        Component(view_layer_pipe, "ViewLayerBuilderPipeline", "pipeline_view_layer.h", "Standard scene building")
        Component(render_pipe, "RenderBuilderPipeline", "pipeline_render.h", "Render with compositor")
        Component(from_ids_pipe, "FromIDsBuilderPipeline", "pipeline_from_ids.h", "Build from specific IDs")
        Component(all_objects_pipe, "AllObjectsBuilderPipeline", "pipeline_all_objects.h", "All objects in scene")
    }

    Rel(view_layer_pipe, pipeline, "Inherits")
    Rel(render_pipe, pipeline, "Inherits")
    Rel(from_ids_pipe, pipeline, "Inherits")
    Rel(all_objects_pipe, pipeline, "Inherits")

    Rel(pipeline, node_builder, "Uses")
    Rel(pipeline, rel_builder, "Uses")
    Rel(node_builder, builder_cache, "Uses")
    Rel(rel_builder, builder_cache, "Uses")
    Rel(rel_builder, rna_builder, "Uses")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

## Component Diagram - Evaluation System

```mermaid
C4Component
    title Component Diagram - Evaluation System

    Container_Boundary(eval_system, "Evaluation System") {
        Component(eval_core, "deg_eval", "deg_eval.cc", "Main evaluation loop and task scheduling")
        Component(eval_flush, "deg_eval_flush", "deg_eval_flush.cc", "Tag propagation through relations")
        Component(eval_cow, "deg_eval_copy_on_write", "deg_eval_copy_on_write.cc", "CoW data management")
        Component(eval_visibility, "deg_eval_visibility", "deg_eval_visibility.cc", "Visibility state evaluation")
        Component(eval_stats, "deg_eval_stats", "deg_eval_stats.cc", "Performance statistics")
    }

    Container_Boundary(backup, "Runtime Backup") {
        Component(backup_core, "RuntimeBackup", "deg_eval_runtime_backup.cc", "Base backup/restore")
        Component(backup_object, "ObjectRuntimeBackup", "deg_eval_runtime_backup_object.cc", "Object runtime data")
        Component(backup_anim, "AnimationBackup", "deg_eval_runtime_backup_animation.cc", "Animation state")
    }

    Component_Ext(task_pool, "TaskPool", "BLI task system for threading")

    Rel(eval_core, eval_flush, "Calls before evaluation")
    Rel(eval_core, eval_visibility, "Determines what to evaluate")
    Rel(eval_core, eval_cow, "Creates CoW copies via")
    Rel(eval_core, eval_stats, "Records timing in")
    Rel(eval_core, task_pool, "Schedules work via")

    Rel(eval_cow, backup_core, "Uses for preservation")
    Rel(backup_object, backup_core, "Inherits")
    Rel(backup_anim, backup_core, "Inherits")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

## Detailed Node Hierarchy

### Node Class Hierarchy

```text
Node (base)
├── TimeSourceNode
│     └── Provides time dependency root
│
├── IDNode
│     ├── id_orig: ID*       (original data-block)
│     ├── id_cow: ID*        (evaluated copy)
│     ├── components: Map<>   (component nodes)
│     └── eval_flags, customdata_masks
│
├── ComponentNode
│     ├── owner: IDNode*
│     ├── operations: Vector<OperationNode*>
│     ├── entry_operation, exit_operation
│     └── Component types:
│           ├── TransformComponentNode
│           ├── GeometryComponentNode
│           ├── AnimationComponentNode
│           ├── ParametersComponentNode
│           ├── PoseComponentNode
│           ├── BoneComponentNode
│           └── ... (20+ types)
│
└── OperationNode
      ├── owner: ComponentNode*
      ├── evaluate: DepsEvalOperationCb  (callback function)
      ├── opcode: OperationCode
      ├── flag: OperationFlag
      └── num_links_pending, scheduled
```

### Component Types

| Type | NodeType Enum | Purpose |
|------|---------------|---------|
| Transform | `TRANSFORM` | Object transforms, constraints |
| Geometry | `GEOMETRY` | Mesh, curves, modifiers |
| Animation | `ANIMATION` | NLA, Actions, F-Curves |
| Parameters | `PARAMETERS` | Custom properties, RNA |
| Pose | `EVAL_POSE` | Armature pose evaluation |
| Bone | `BONE` | Individual bone evaluation |
| Shading | `SHADING` | Material, texture updates |
| Visibility | `VISIBILITY` | Visibility state |
| Copy-on-Eval | `COPY_ON_EVAL` | CoW component |
| Synchronization | `SYNCHRONIZATION` | Sync back to original |

### Operation Codes (OperationCode enum)

**Transform Operations:**

- `TRANSFORM_INIT` - Initialize transform
- `TRANSFORM_LOCAL` - Local transforms
- `TRANSFORM_PARENT` - Parent relationship
- `TRANSFORM_CONSTRAINTS` - Constraint evaluation
- `TRANSFORM_FINAL` - Final world matrix

**Geometry Operations:**

- `GEOMETRY_EVAL_INIT` - Initialize geometry eval
- `MODIFIER` - Modifier stack evaluation
- `GEOMETRY_EVAL` - Full geometry evaluation
- `GEOMETRY_EVAL_DONE` - Finalize geometry

**Pose/Bone Operations:**

- `POSE_INIT` - Initialize pose
- `BONE_LOCAL` - Bone local transform
- `BONE_POSE_PARENT` - Bone parent/rest pose
- `BONE_CONSTRAINTS` - Bone constraints
- `BONE_DONE` - Finalize bone
- `POSE_IK_SOLVER` - IK solver

**Animation Operations:**

- `ANIMATION_ENTRY` - Start animation eval
- `ANIMATION_EVAL` - Evaluate animation
- `DRIVER` - Driver evaluation

## Relation Types

```cpp
enum RelationFlag {
    RELATION_FLAG_CYCLIC        // Part of a cycle
    RELATION_FLAG_NO_FLUSH      // Don't propagate updates
    RELATION_FLAG_FLUSH_USER_EDIT_ONLY  // Only on user edit
    RELATION_FLAG_GODMODE       // Can't be broken by cycle solver
    RELATION_CHECK_BEFORE_ADD   // Check existence first
    RELATION_NO_VISIBILITY_CHANGE  // Doesn't affect visibility
};
```

### Relation Structure

```cpp
struct Relation {
    Node *from;           // Source node (A)
    Node *to;             // Target node (B)
    const char *name;     // Debug label
    int flag;             // RelationFlag bitmask
};
// Meaning: B depends on A (A must evaluate before B)
```

## Builder Process Detail

### Phase 1: Node Building

```text
DepsgraphNodeBuilder::build_view_layer()
├── build_scene_parameters()
├── build_scene_compositor()
├── For each LayerCollection:
│   └── build_collection()
│       └── For each Object:
│           └── build_object()
│               ├── add_id_node(object)
│               ├── build_object_transform()
│               ├── build_object_data()
│               ├── build_object_modifiers()
│               ├── build_animdata()
│               └── build_constraints()
└── build_layer_collections()
```

### Phase 2: Relation Building

```text
DepsgraphRelationBuilder::build_view_layer()
├── build_scene_parameters()
├── For each Object:
│   └── build_object()
│       ├── build_object_parent()
│       │   └── add_relation(parent.TRANSFORM_FINAL → child.TRANSFORM_PARENT)
│       ├── build_constraints()
│       │   └── add_relation(target → constraint_component)
│       ├── build_object_modifiers()
│       │   └── add_relation(modifier_data → GEOMETRY)
│       └── build_animdata()
│           └── add_relation(ANIMATION → animated_property)
└── build_driver_relations()
```

## Evaluation Process Detail

```text
deg_evaluate_on_refresh(graph)
├── deg_graph_flush_updates(graph)     // Propagate tags
│   ├── flush_schedule_entrypoints()   // Get tagged nodes
│   └── For each tagged node:
│       └── flush to dependents via relations
│
├── Evaluation stages:
│   ├── COPY_ON_EVAL stage
│   │   └── Ensure all CoW data exists
│   │
│   ├── DYNAMIC_VISIBILITY stage
│   │   └── Evaluate visibility-affecting operations
│   │
│   └── THREADED_EVALUATION stage
│       ├── calculate_pending_parents()
│       ├── schedule_root_nodes()       // Nodes with 0 pending
│       └── TaskPool parallel execution:
│           └── For each ready node:
│               ├── evaluate_node()
│               └── schedule_children()
│
└── deg_graph_clear_tags(graph)        // Clean up
```

## Source File Reference

| Component | File | Purpose |
|-----------|------|---------|
| Node base | `intern/node/deg_node.hh` | Base node class |
| ID Node | `intern/node/deg_node_id.hh` | Per-datablock node |
| Component Node | `intern/node/deg_node_component.hh` | Component types |
| Operation Node | `intern/node/deg_node_operation.hh` | Atomic operations |
| Relation | `intern/depsgraph_relation.hh` | Edge/dependency |
| Node Builder | `intern/builder/deg_builder_nodes.h` | Node creation |
| Relation Builder | `intern/builder/deg_builder_relations.h` | Relation creation |
| Pipeline | `intern/builder/pipeline.h` | Build orchestration |
| Evaluation | `intern/eval/deg_eval.cc` | Evaluation engine |
| Flush | `intern/eval/deg_eval_flush.cc` | Tag propagation |
| CoW | `intern/eval/deg_eval_copy_on_write.cc` | Copy-on-eval |
