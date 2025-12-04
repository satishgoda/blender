# Evaluation Process - Blender Dependency Graph

This document explains how the dependency graph evaluates nodes to produce updated scene data.

## Evaluation Overview

```mermaid
flowchart TB
    subgraph Trigger["Evaluation Trigger"]
        FRAME[Frame Change]
        REFRESH[Data Refresh]
        RENDER[Render Request]
    end

    subgraph Evaluation["Evaluation Pipeline"]
        FLUSH[Flush Updates]
        COW_STAGE[Copy-on-Eval Stage]
        VIS_STAGE[Dynamic Visibility Stage]
        THREAD_STAGE[Threaded Evaluation Stage]
        SINGLE_STAGE[Single-Thread Workaround]
        CLEAR[Clear Tags]
    end

    subgraph Output["Results"]
        EVAL_DATA[Evaluated Data]
        NOTIFY[Editor Notification]
    end

    FRAME --> FLUSH
    REFRESH --> FLUSH
    RENDER --> FLUSH

    FLUSH --> COW_STAGE --> VIS_STAGE --> THREAD_STAGE --> SINGLE_STAGE --> CLEAR
    CLEAR --> EVAL_DATA --> NOTIFY
```

## Evaluation Entry Points

```mermaid
C4Component
    title Evaluation Entry Points

    Component_Ext(scene_update, "BKE_scene_graph_update_*", "Scene update triggers")
    
    Container_Boundary(deg_api, "Depsgraph API") {
        Component(frame_change, "DEG_evaluate_on_framechange", "Frame change evaluation")
        Component(refresh, "DEG_evaluate_on_refresh", "General refresh")
    }
    
    Container_Boundary(internal, "Internal") {
        Component(deg_eval, "deg_evaluate_on_refresh", "Main evaluation function")
        Component(flush, "deg_graph_flush_updates", "Tag propagation")
    }

    Rel(scene_update, frame_change, "Calls")
    Rel(scene_update, refresh, "Calls")
    Rel(frame_change, deg_eval, "Delegates to")
    Rel(refresh, deg_eval, "Delegates to")
    Rel(deg_eval, flush, "First calls")
```

## Stage 1: Flush Updates

The flush phase propagates update tags through the graph:

```mermaid
flowchart TB
    subgraph FlushProcess["Flush Process"]
        PREPARE[flush_prepare\nReset scheduled flags]
        ENTRY[flush_schedule_entrypoints\nQueue tagged nodes]
        
        subgraph Loop["For each queued node"]
            HANDLE_ID[flush_handle_id_node\nMark ID modified]
            HANDLE_COMP[flush_handle_component_node\nTag component operations]
            SCHEDULE[flush_schedule_children\nQueue dependents]
        end
        
        COMPLETE[Flush Complete]
    end

    PREPARE --> ENTRY --> HANDLE_ID --> HANDLE_COMP --> SCHEDULE
    SCHEDULE -->|"More nodes"| HANDLE_ID
    SCHEDULE -->|"Done"| COMPLETE
```

### Tag Propagation Rules

```mermaid
flowchart LR
    subgraph FlushRules["Flush Rules"]
        NORMAL[Normal Relation\nAlways flush]
        NO_FLUSH[NO_FLUSH flag\nNever flush]
        USER_ONLY[USER_EDIT_ONLY\nFlush if user edit]
    end

    A[Node A\nModified] -->|"NORMAL"| B[Node B\nTagged]
    A -->|"NO_FLUSH"| C[Node C\nNot tagged]
    A -->|"USER_EDIT_ONLY"| D{User edit?}
    D -->|"Yes"| E[Node D\nTagged]
    D -->|"No"| F[Node D\nNot tagged]
```

## Stage 2: Copy-on-Eval

Ensures all needed data has evaluated copies:

```mermaid
flowchart TB
    subgraph COW["Copy-on-Eval Stage"]
        CHECK[Check if COW exists]
        
        subgraph CreateCopy["Create Copy"]
            ALLOC[Allocate memory]
            COPY[Deep copy data]
            PATCH[Patch pointers]
            BACKUP[Backup runtime data]
        end
        
        READY[CoW ready]
    end

    CHECK -->|"Needs copy"| ALLOC
    CHECK -->|"Exists"| READY
    ALLOC --> COPY --> PATCH --> BACKUP --> READY
```

### CoW Data Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Original: User creates
    Original --> Copying: Graph built
    Copying --> Evaluated: CoW complete
    Evaluated --> Evaluating: Tag received
    Evaluating --> Evaluated: Evaluation done
    Evaluated --> Syncing: Writeback needed
    Syncing --> Original: Sync complete
    Original --> [*]: Deleted
```

## Stage 3: Dynamic Visibility

Evaluates visibility-affecting operations:

```mermaid
flowchart TB
    subgraph VisibilityEval["Visibility Evaluation"]
        FIND_VIS[Find visibility operations]
        
        subgraph EvalVis["For each visibility op"]
            EVAL_DRIVER[Evaluate visibility driver]
            EVAL_ANIM[Evaluate visibility animation]
            UPDATE_VIS[Update visibility state]
        end
        
        RECALC[Recalculate pending parents]
    end

    FIND_VIS --> EVAL_DRIVER --> EVAL_ANIM --> UPDATE_VIS
    UPDATE_VIS -->|"More"| EVAL_DRIVER
    UPDATE_VIS -->|"Done"| RECALC
```

## Stage 4: Threaded Evaluation

Main parallel evaluation of operations:

```mermaid
flowchart TB
    subgraph ThreadedEval["Threaded Evaluation"]
        CALC_PENDING[calculate_pending_parents]
        INIT[Initialize task pool]
        
        subgraph TaskPool["Task Pool"]
            T1[Thread 1]
            T2[Thread 2]
            T3[Thread 3]
            TN[Thread N]
        end
        
        subgraph NodeExec["Node Execution"]
            CHECK_READY{Dependencies\nready?}
            EXEC[Execute callback]
            UPDATE_CHILDREN[Update children pending]
            SCHEDULE_READY[Schedule ready children]
        end
        
        WAIT[Wait for completion]
    end

    CALC_PENDING --> INIT --> TaskPool
    T1 & T2 & T3 & TN --> NodeExec
    CHECK_READY -->|"Yes"| EXEC --> UPDATE_CHILDREN --> SCHEDULE_READY
    CHECK_READY -->|"No"| WAIT
    SCHEDULE_READY -->|"Schedule"| TaskPool
```

### Pending Count Management

```mermaid
sequenceDiagram
    participant Scheduler
    participant NodeA as Node A
    participant NodeB as Node B (depends on A)
    participant NodeC as Node C (depends on A)

    Note over Scheduler,NodeC: Initial pending counts
    Scheduler->>NodeA: pending = 0 (root)
    Scheduler->>NodeB: pending = 1
    Scheduler->>NodeC: pending = 1

    Scheduler->>NodeA: Execute (pending=0)
    NodeA-->>Scheduler: Complete
    
    Scheduler->>NodeB: Decrement pending
    Note over NodeB: pending = 0
    Scheduler->>NodeC: Decrement pending
    Note over NodeC: pending = 0
    
    par Execute in parallel
        Scheduler->>NodeB: Execute
        Scheduler->>NodeC: Execute
    end
```

### Visibility Optimization

```mermaid
flowchart TB
    subgraph VisOpt["Visibility Optimization"]
        CHECK_VIS{Is visible?}
        CHECK_AFFECTS{Affects visible?}
        
        EXECUTE[Execute normally]
        SKIP[Skip evaluation]
    end

    CHECK_VIS -->|"Yes"| EXECUTE
    CHECK_VIS -->|"No"| CHECK_AFFECTS
    CHECK_AFFECTS -->|"Yes"| EXECUTE
    CHECK_AFFECTS -->|"No"| SKIP
```

## Stage 5: Single-Thread Workaround

Some operations must run single-threaded:

```mermaid
flowchart LR
    subgraph SingleThread["Single-Thread Stage"]
        METABALLS[Metaball evaluation]
        NOTES[Explanation]
    end

    NOTES[/"Metaballs iterate all bases\nRequest dupli-lists\nCannot parallelize"/]
```

## Evaluation Callbacks

Operation nodes contain callbacks to BKE functions:

```mermaid
flowchart TB
    subgraph Callbacks["Evaluation Callbacks"]
        OP[OperationNode]
        CB[DepsEvalOperationCb]
        
        subgraph BKE["BKE Functions"]
            TRANS[BKE_object_eval_transform]
            GEOM[BKE_object_eval_mesh]
            POSE[BKE_pose_eval]
            MOD[BKE_modifier_eval]
        end
    end

    OP -->|"evaluate"| CB
    CB -->|"calls"| TRANS & GEOM & POSE & MOD
```

### Example: Transform Evaluation

```mermaid
sequenceDiagram
    participant DEG as Depsgraph
    participant Op as OperationNode
    participant BKE as BKE_object_*
    participant ObjCoW as Object (CoW)

    DEG->>Op: Execute TRANSFORM_LOCAL
    Op->>BKE: BKE_object_eval_local_transform(depsgraph, object)
    BKE->>ObjCoW: Update ob->loc/rot/scale
    BKE-->>Op: Done

    DEG->>Op: Execute TRANSFORM_PARENT
    Op->>BKE: BKE_object_eval_parent(depsgraph, object)
    BKE->>ObjCoW: Apply parent matrix
    BKE-->>Op: Done

    DEG->>Op: Execute TRANSFORM_CONSTRAINTS
    Op->>BKE: BKE_object_eval_constraints(depsgraph, object)
    BKE->>ObjCoW: Apply constraints
    BKE-->>Op: Done

    DEG->>Op: Execute TRANSFORM_FINAL
    Op->>BKE: BKE_object_eval_transform_final(depsgraph, object)
    BKE->>ObjCoW: Compute final ob->object_to_world
    BKE-->>Op: Done
```

## Runtime Backup System

Preserves runtime data across CoW updates:

```mermaid
flowchart TB
    subgraph Backup["Runtime Backup"]
        subgraph Before["Before CoW"]
            SAVE_OBJ[Save object runtime]
            SAVE_MESH[Save mesh runtime]
            SAVE_POSE[Save pose runtime]
        end
        
        COW[Perform CoW]
        
        subgraph After["After CoW"]
            RESTORE_OBJ[Restore object runtime]
            RESTORE_MESH[Restore mesh runtime]
            RESTORE_POSE[Restore pose runtime]
        end
    end

    SAVE_OBJ & SAVE_MESH & SAVE_POSE --> COW
    COW --> RESTORE_OBJ & RESTORE_MESH & RESTORE_POSE
```

### Backed Up Data Types

| Backup Class | Data Preserved |
|--------------|----------------|
| `ObjectRuntimeBackup` | Base flags, batch cache, curve cache |
| `AnimationBackup` | NLA state, action blending |
| `PoseRuntimeBackup` | Pose state, IK state |
| `ModifierRuntimeBackup` | Modifier cache |
| `MeshRuntimeBackup` | Evaluated mesh, batch cache |

## Performance Statistics

```mermaid
flowchart LR
    subgraph Stats["Evaluation Statistics"]
        NODE_TIME[Node execution time]
        TOTAL_TIME[Total evaluation time]
        CATEGORY[Per-category timing]
    end

    subgraph Output["Debug Output"]
        GNUPLOT[GNUplot data]
        CONSOLE[Console stats]
        DEBUG_VIS[Debug visualization]
    end

    NODE_TIME & TOTAL_TIME & CATEGORY --> GNUPLOT & CONSOLE & DEBUG_VIS
```

## Writeback System

Some evaluated data can sync back to original:

```mermaid
flowchart TB
    subgraph Writeback["Sync Writeback"]
        CHECK[Check sync_writeback mode]
        COLLECT[Collect writeback callbacks]
        EXECUTE_WB[Execute callbacks]
        TAG_ORIG[Tag original for update]
    end

    CHECK -->|"YES"| COLLECT --> EXECUTE_WB --> TAG_ORIG
    CHECK -->|"NO"| SKIP[Skip writeback]
```

### Writeback Use Cases

| Use Case | Data |
|----------|------|
| FCurve baking | Animation data |
| Simulation baking | Physics cache |
| Shape key from deform | Mesh data |

## Source Files

| File | Purpose |
|------|---------|
| `deg_eval.cc` | Main evaluation loop |
| `deg_eval.h` | Evaluation interface |
| `deg_eval_flush.cc` | Tag propagation |
| `deg_eval_copy_on_write.cc` | CoW management |
| `deg_eval_visibility.cc` | Visibility evaluation |
| `deg_eval_stats.cc` | Performance stats |
| `deg_eval_runtime_backup*.cc` | Runtime preservation |

## Key Functions

| Function | Purpose |
|----------|---------|
| `deg_evaluate_on_refresh()` | Main entry point |
| `deg_graph_flush_updates()` | Propagate tags |
| `deg_update_copy_on_write_datablock()` | Create/update CoW |
| `deg_graph_flush_visibility()` | Visibility updates |
| `evaluate_node()` | Execute single node |
| `schedule_children()` | Schedule ready dependents |
