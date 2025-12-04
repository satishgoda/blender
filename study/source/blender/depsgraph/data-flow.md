# Data Flow Diagram - Blender Dependency Graph

This document explains how data flows through the dependency graph system.

## High-Level Data Flow

```mermaid
flowchart TB
    subgraph Input["Input Phase"]
        USER[User Action]
        SCRIPT[Python Script]
        ANIM[Animation Playback]
    end

    subgraph Tagging["Tagging Phase"]
        TAG[DEG_id_tag_update]
        TAGS[(Entry Tags)]
    end

    subgraph Flush["Flush Phase"]
        FLUSH[deg_graph_flush_updates]
        TAGGED[(Tagged Nodes)]
    end

    subgraph Eval["Evaluation Phase"]
        SCHED[Task Scheduler]
        EXEC[Node Execution]
        COW[Copy-on-Eval]
    end

    subgraph Output["Output Phase"]
        VIEWPORT[Viewport Display]
        RENDER[Render Output]
        EXPORT[File Export]
    end

    USER --> TAG
    SCRIPT --> TAG
    ANIM --> TAG

    TAG --> TAGS
    TAGS --> FLUSH
    FLUSH --> TAGGED
    TAGGED --> SCHED
    SCHED --> EXEC
    EXEC <--> COW

    EXEC --> VIEWPORT
    EXEC --> RENDER
    EXEC --> EXPORT
```

## Detailed Flow: Object Transform Update

This sequence shows what happens when a user moves an object:

```mermaid
sequenceDiagram
    participant User
    participant Editor as 3D Viewport
    participant DEG as Depsgraph API
    participant Graph as Graph Core
    participant Flush as Flush System
    participant Eval as Evaluator

    User->>Editor: Move object
    Editor->>DEG: DEG_id_tag_update(obj, ID_RECALC_TRANSFORM)
    
    DEG->>Graph: Find IDNode for object
    Graph-->>DEG: IDNode
    DEG->>Graph: Add to entry_tags
    
    Note over DEG,Graph: Tagging complete, evaluation triggered
    
    DEG->>Flush: deg_graph_flush_updates()
    Flush->>Graph: Get entry_tags
    
    loop For each tagged node
        Flush->>Graph: Propagate via relations
        Graph->>Graph: Mark dependents as needing update
    end
    
    Flush-->>DEG: Flush complete
    
    DEG->>Eval: deg_evaluate_on_refresh()
    
    loop For each ready node
        Eval->>Eval: Execute operation callback
        Eval->>Eval: Update pending counts
        Eval->>Eval: Schedule children
    end
    
    Eval-->>DEG: Evaluation complete
    DEG-->>Editor: Notify update
    Editor->>User: Redraw viewport
```

## Copy-on-Eval Data Flow

```mermaid
flowchart LR
    subgraph Original["Original Data (Main)"]
        OBJ_ORIG[Object Original]
        MESH_ORIG[Mesh Original]
    end

    subgraph Depsgraph["Depsgraph (CoW)"]
        OBJ_COW[Object CoW Copy]
        MESH_COW[Mesh CoW Copy]
        MESH_EVAL[Evaluated Mesh]
    end

    subgraph Display["Display"]
        GPU[GPU Buffers]
    end

    OBJ_ORIG -->|"Copy-on-Eval"| OBJ_COW
    MESH_ORIG -->|"Copy-on-Eval"| MESH_COW
    MESH_COW -->|"Modifier Stack"| MESH_EVAL
    MESH_EVAL -->|"Batch Cache"| GPU

    style OBJ_ORIG fill:#ffd700
    style MESH_ORIG fill:#ffd700
    style OBJ_COW fill:#90ee90
    style MESH_COW fill:#90ee90
    style MESH_EVAL fill:#90ee90
```

## Tag Propagation Flow

Shows how update tags flow through the graph:

```mermaid
flowchart TB
    subgraph Scene["Scene Graph"]
        PARENT[Parent Object]
        CHILD[Child Object]
        MESH[Mesh Data]
        MAT[Material]
        ARMATURE[Armature]
        BONE[Bone]
    end

    PARENT -->|"Parent relation"| CHILD
    MESH -->|"Object data"| CHILD
    MAT -->|"Material slot"| MESH
    ARMATURE -->|"Modifier target"| MESH
    BONE -->|"Pose bone"| ARMATURE

    subgraph Update["Update Flow"]
        direction TB
        TAG1[Parent tagged]
        TAG2[Child tagged via relation]
        TAG3[Modifiers tagged]
    end

    TAG1 --> TAG2
    TAG2 --> TAG3

    PARENT -.->|triggers| TAG1
    TAG2 -.->|affects| CHILD
```

## Evaluation Stage Flow

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle --> Tagged: DEG_id_tag_update()
    Tagged --> Flushing: DEG_evaluate_on_refresh()
    
    Flushing --> CopyOnEval: Flush complete
    
    state CopyOnEval {
        [*] --> CheckCoW
        CheckCoW --> CreateCopy: Needs copy
        CheckCoW --> Skip: Already exists
        CreateCopy --> [*]
        Skip --> [*]
    }
    
    CopyOnEval --> DynamicVisibility
    
    state DynamicVisibility {
        [*] --> EvalVisibility
        EvalVisibility --> UpdateVisible: Has animation
        EvalVisibility --> Keep: Static
        UpdateVisible --> [*]
        Keep --> [*]
    }
    
    DynamicVisibility --> ThreadedEval
    
    state ThreadedEval {
        [*] --> Schedule
        Schedule --> Execute: Node ready
        Execute --> CheckChildren
        CheckChildren --> Schedule: Children ready
        CheckChildren --> Wait: Dependencies pending
        Wait --> Schedule: Dependency done
        Execute --> [*]: All done
    }
    
    ThreadedEval --> ClearTags
    ClearTags --> Idle
```

## Relation Types and Data Flow

```mermaid
flowchart TB
    subgraph DataFlow["Data Dependency"]
        A1[Mesh Data] -->|"Geometry"| A2[Object Geometry]
        A2 -->|"Input"| A3[Modifier]
    end

    subgraph TimeFlow["Time Dependency"]
        B1[Time Source] -->|"Frame"| B2[Animation]
        B2 -->|"Value"| B3[Transform]
    end

    subgraph VisFlow["Visibility Dependency"]
        C1[Collection] -->|"Contains"| C2[Object]
        C2 -->|"Instances"| C3[Instance]
    end

    subgraph DriverFlow["Driver Dependency"]
        D1[Driver Target] -->|"Drives"| D2[Driver]
        D2 -->|"Output"| D3[Animated Property]
    end
```

## Multi-Object Update Example

```mermaid
sequenceDiagram
    participant World as World Data
    participant Armature as Armature Object
    participant Mesh as Mesh Object
    participant DEG as Depsgraph

    Note over World,DEG: Armature bone moves

    Armature->>DEG: Tag TRANSFORM update
    DEG->>DEG: Flush to Mesh (via Armature modifier)
    
    par Parallel Evaluation
        DEG->>Armature: Evaluate Pose
        Armature-->>DEG: Bone matrices ready
    and
        DEG->>World: Evaluate World
        World-->>DEG: World ready
    end
    
    Note over DEG: Mesh waits for Armature
    
    DEG->>Mesh: Evaluate Geometry
    Mesh->>Armature: Read bone matrices
    Mesh-->>DEG: Deformed mesh ready
```

## Physics Simulation Flow

```mermaid
flowchart TB
    subgraph Frame1["Frame N"]
        SIM1[Simulation State]
        OBJ1[Object Transform]
    end

    subgraph Frame2["Frame N+1"]
        SIM2[Simulation Step]
        OBJ2[Object Transform]
    end

    subgraph Cache["Point Cache"]
        PC[Cache Data]
    end

    SIM1 -->|"Previous state"| SIM2
    OBJ1 -->|"Forces"| SIM2
    SIM2 -->|"New transform"| OBJ2
    SIM2 <-->|"Read/Write"| PC
```

## Data Flow Summary

| Phase | Input | Processing | Output |
|-------|-------|------------|--------|
| **Tagging** | User edit, script, animation | `DEG_id_tag_update()` | Entry tags in graph |
| **Flushing** | Entry tags | Relation traversal | All affected nodes tagged |
| **CoW** | Original data | Deep copy | Evaluated data copies |
| **Evaluation** | Tagged nodes | Topological order execution | Updated evaluated data |
| **Output** | Evaluated data | Batch cache, draw calls | Viewport/render |

## Key Data Structures

### Entry Tags

```cpp
// In Depsgraph struct
Set<OperationNode *> entry_tags;  // Initially modified nodes
```

### Node Update Flags

```cpp
enum OperationFlag {
    DEPSOP_FLAG_NEEDS_UPDATE      = (1 << 0),
    DEPSOP_FLAG_DIRECTLY_MODIFIED = (1 << 1),
    DEPSOP_FLAG_USER_MODIFIED     = (1 << 2),
};
```

### Recalc Flags

```cpp
// In DNA_ID.h
typedef enum IDRecalcFlag {
    ID_RECALC_TRANSFORM   = (1 << 0),
    ID_RECALC_GEOMETRY    = (1 << 1),
    ID_RECALC_ANIMATION   = (1 << 2),
    ID_RECALC_SHADING     = (1 << 8),
    // ... more flags
} IDRecalcFlag;
```
