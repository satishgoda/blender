# Node Hierarchy - Blender Dependency Graph

This document provides detailed documentation of the node type system.

## Node Class Hierarchy Diagram

```mermaid
classDiagram
    class Node {
        <<abstract>>
        +string name
        +NodeType type
        +Vector~Relation*~ inlinks
        +Vector~Relation*~ outlinks
        +Stats stats
        +int custom_flags
        +identifier() string
        +tag_update(Depsgraph*, eUpdateSource)
        +get_entry_operation() OperationNode*
        +get_exit_operation() OperationNode*
    }

    class TimeSourceNode {
        +static TypeInfo typeinfo
    }

    class IDNode {
        +ID_Type id_type
        +ID* id_orig
        +uint id_orig_session_uid
        +ID* id_cow
        +Map~ComponentIDKey,ComponentNode*~ components
        +uint32_t eval_flags
        +eDepsNode_LinkedState_Type linked_state
        +bool is_visible_on_build
        +bool is_enabled_on_eval
        +find_component(NodeType, StringRef) ComponentNode*
        +add_component(NodeType, StringRef) ComponentNode*
        +finalize_build(Depsgraph*)
    }

    class ComponentNode {
        +IDNode* owner
        +Map~OperationIDKey,OperationNode*~ operations_map
        +Vector~OperationNode*~ operations
        +OperationNode* entry_operation
        +OperationNode* exit_operation
        +bool affects_visible_id
        +find_operation(OperationCode) OperationNode*
        +add_operation(callback, OperationCode) OperationNode*
        +set_entry_operation(OperationNode*)
        +set_exit_operation(OperationNode*)
    }

    class OperationNode {
        +ComponentNode* owner
        +DepsEvalOperationCb evaluate
        +uint32_t num_links_pending
        +bool scheduled
        +OperationCode opcode
        +int name_tag
        +int flag
        +is_noop() bool
        +set_as_entry()
        +set_as_exit()
    }

    class Relation {
        +Node* from
        +Node* to
        +const char* name
        +int flag
        +unlink()
    }

    Node <|-- TimeSourceNode
    Node <|-- IDNode
    Node <|-- ComponentNode
    Node <|-- OperationNode

    IDNode "1" *-- "*" ComponentNode : contains
    ComponentNode "1" *-- "*" OperationNode : contains
    Node "*" -- "*" Relation : connected by
```

## NodeType Enumeration

```mermaid
mindmap
    root((NodeType))
        Generic
            UNDEFINED
            OPERATION
            TIMESOURCE
            ID_REF
        Outer Types
            PARAMETERS
            ANIMATION
            TRANSFORM
            GEOMETRY
            SEQUENCER
            LAYER_COLLECTIONS
            COPY_ON_EVAL
            OBJECT_FROM_LAYER
            HIERARCHY
            AUDIO
            ARMATURE
            GENERIC_DATABLOCK
            SCENE
            VISIBILITY
        Evaluation Types
            EVAL_POSE
            BONE
            PARTICLE_SYSTEM
            PARTICLE_SETTINGS
            SHADING
            POINT_CACHE
            IMAGE_ANIMATION
            CACHE
            BATCH_CACHE
            INSTANCING
            SYNCHRONIZATION
            NTREE_OUTPUT
            NTREE_GEOMETRY_PREPROCESS
```

## Component Node Types

### Transform Component

Handles object spatial transformations:

```mermaid
flowchart LR
    subgraph TransformComponent
        INIT[TRANSFORM_INIT]
        LOCAL[TRANSFORM_LOCAL]
        PARENT[TRANSFORM_PARENT]
        CONSTRAINTS[TRANSFORM_CONSTRAINTS]
        EVAL[TRANSFORM_EVAL]
        FINAL[TRANSFORM_FINAL]
    end

    INIT --> LOCAL --> PARENT --> CONSTRAINTS --> EVAL --> FINAL
```

**Operations:**

| OperationCode | Purpose |
|---------------|---------|
| `TRANSFORM_INIT` | Initialize transform evaluation |
| `TRANSFORM_LOCAL` | Apply local transform |
| `TRANSFORM_PARENT` | Apply parent transform |
| `TRANSFORM_CONSTRAINTS` | Evaluate transform constraints |
| `TRANSFORM_SIMULATION_INIT` | Initialize for simulation |
| `TRANSFORM_EVAL` | Handle special cases |
| `TRANSFORM_FINAL` | Finalize world matrix |

### Geometry Component

Handles mesh/curve/volume geometry:

```mermaid
flowchart LR
    subgraph GeometryComponent
        INIT[GEOMETRY_EVAL_INIT]
        MOD1[MODIFIER 1]
        MOD2[MODIFIER 2]
        MODN[MODIFIER N]
        EVAL[GEOMETRY_EVAL]
        DONE[GEOMETRY_EVAL_DONE]
    end

    INIT --> MOD1 --> MOD2 --> MODN --> EVAL --> DONE
```

**Operations:**

| OperationCode | Purpose |
|---------------|---------|
| `GEOMETRY_EVAL_INIT` | Entry point, prepare geometry |
| `MODIFIER` | Individual modifier evaluation |
| `GEOMETRY_EVAL` | Full geometry evaluation |
| `GEOMETRY_EVAL_DONE` | Finalize, cleanup |
| `GEOMETRY_SHAPEKEY` | Shape key evaluation |

### Animation Component

Handles F-Curves, NLA, Actions:

```mermaid
flowchart LR
    subgraph AnimationComponent
        ENTRY[ANIMATION_ENTRY]
        EVAL[ANIMATION_EVAL]
        EXIT[ANIMATION_EXIT]
    end

    ENTRY --> EVAL --> EXIT
```

**Operations:**

| OperationCode | Purpose |
|---------------|---------|
| `ANIMATION_ENTRY` | Begin animation evaluation |
| `ANIMATION_EVAL` | Evaluate NLA/Action data |
| `ANIMATION_EXIT` | Finalize animation |
| `DRIVER` | Evaluate individual drivers |

### Pose Component (Armature)

Handles armature pose evaluation:

```mermaid
flowchart TB
    subgraph PoseComponent
        INIT[POSE_INIT]
        INIT_IK[POSE_INIT_IK]
        
        subgraph Bones["For each bone"]
            BONE_LOCAL[BONE_LOCAL]
            BONE_PARENT[BONE_POSE_PARENT]
            BONE_CONST[BONE_CONSTRAINTS]
            BONE_READY[BONE_READY]
            BONE_DONE[BONE_DONE]
        end
        
        IK[POSE_IK_SOLVER]
        CLEANUP[POSE_CLEANUP]
        DONE[POSE_DONE]
    end

    INIT --> INIT_IK
    INIT_IK --> BONE_LOCAL
    BONE_LOCAL --> BONE_PARENT --> BONE_CONST --> BONE_READY
    BONE_READY --> IK
    IK --> BONE_DONE
    BONE_DONE --> CLEANUP --> DONE
```

### Copy-on-Eval Component

Manages evaluated data copies:

```mermaid
flowchart LR
    subgraph CopyOnEvalComponent
        COW[COPY_ON_EVAL]
    end

    ORIGINAL[Original Data] --> COW --> EVALUATED[Evaluated Copy]
```

### Visibility Component

Manages visibility state:

```mermaid
flowchart LR
    subgraph VisibilityComponent
        VIS[VISIBILITY]
    end

    COLLECTION[Collection State] --> VIS
    ANIMATION[Animated Visibility] --> VIS
    VIS --> VISIBLE[Is Visible?]
```

## ID Node Structure

Each data-block gets an IDNode:

```mermaid
flowchart TB
    subgraph IDNode["IDNode (Object)"]
        direction TB
        META[id_type: OB_MESH\nid_orig: Object*\nid_cow: Object*]
        
        subgraph Components
            COW[Copy-on-Eval]
            TRANS[Transform]
            GEOM[Geometry]
            ANIM[Animation]
            SYNC[Synchronization]
        end
    end

    META --- Components
```

## Relation System

### Relation Flags

```mermaid
flowchart LR
    subgraph RelationFlags
        CYCLIC[CYCLIC\nPart of detected cycle]
        NO_FLUSH[NO_FLUSH\nDon't propagate tags]
        USER_ONLY[FLUSH_USER_EDIT_ONLY\nOnly on user edits]
        GODMODE[GODMODE\nCannot be broken]
        CHECK[CHECK_BEFORE_ADD\nAvoid duplicates]
        NO_VIS[NO_VISIBILITY_CHANGE\nIgnore for visibility]
    end
```

### Common Relation Patterns

**Parent-Child:**

```mermaid
flowchart LR
    P_TRANS[Parent.Transform.FINAL]
    C_TRANS[Child.Transform.PARENT]
    P_TRANS -->|"Parent relation"| C_TRANS
```

**Modifier Dependency:**

```mermaid
flowchart LR
    TARGET[Target.Geometry.EVAL]
    MOD[Object.Geometry.MODIFIER]
    TARGET -->|"Modifier input"| MOD
```

**Driver:**

```mermaid
flowchart LR
    SRC[Source.Parameters.PROP]
    DRIVER[Target.Animation.DRIVER]
    DRIVEN[Target.Transform.LOCAL]
    
    SRC -->|"Driver input"| DRIVER
    DRIVER -->|"Driver output"| DRIVEN
```

**Constraint:**

```mermaid
flowchart LR
    TARGET[Target.Transform.FINAL]
    CONST[Object.Transform.CONSTRAINTS]
    
    TARGET -->|"Constraint target"| CONST
```

## Node Factory System

```mermaid
classDiagram
    class DepsNodeFactory {
        <<interface>>
        +type() NodeType
        +type_name() const char*
        +id_recalc_tag() int
        +create_node() Node*
    }

    class DepsNodeFactoryImpl~T~ {
        +type() NodeType
        +type_name() const char*
        +create_node() Node*
    }

    DepsNodeFactory <|-- DepsNodeFactoryImpl

    note for DepsNodeFactoryImpl "Template creates\nfactory per node type"
```

## Node Statistics

Each node tracks evaluation statistics:

```cpp
struct Node::Stats {
    double current_time;  // Time for current evaluation
    
    void reset();
    void reset_current();
};
```

Used for:

- Performance profiling
- Identifying bottlenecks
- Debug visualization

## Custom Flags Usage

The `custom_flags` field is repurposed in different phases:

| Phase | IDNode Usage | ComponentNode Usage |
|-------|--------------|---------------------|
| **Build** | Build state | Build state |
| **Flush** | `ID_STATE_MODIFIED` | `COMPONENT_STATE_*` |
| **Eval** | Visibility state | Visibility state |

## Source Files

| Type | Header | Implementation |
|------|--------|----------------|
| Node base | `deg_node.hh` | `deg_node.cc` |
| IDNode | `deg_node_id.hh` | `deg_node_id.cc` |
| ComponentNode | `deg_node_component.hh` | `deg_node_component.cc` |
| OperationNode | `deg_node_operation.hh` | `deg_node_operation.cc` |
| TimeSourceNode | `deg_node_time.hh` | `deg_node_time.cc` |
| Factory | `deg_node_factory.hh` | `deg_node_factory.cc` |
