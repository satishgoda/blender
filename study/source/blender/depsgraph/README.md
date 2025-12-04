# Blender Dependency Graph (Depsgraph) Architecture Study

This document provides a comprehensive analysis of Blender's Dependency Graph system using C4 diagrams and detailed explanations.

## Overview

The Dependency Graph (depsgraph) is a core subsystem in Blender that:

1. **Tracks relationships** between data blocks (IDs) in a Blender file
2. **Determines update order** when data changes
3. **Manages evaluation** of scene data for viewport and rendering
4. **Implements Copy-on-Evaluation (CoW)** for thread-safe data access

## Document Index

| Document | Description |
|----------|-------------|
| [C4 Context Diagram](./c4-context.md) | System-level view showing how depsgraph fits in Blender |
| [C4 Container Diagram](./c4-container.md) | Major components within the depsgraph system |
| [C4 Component Diagram](./c4-component.md) | Detailed internal structure and interactions |
| [Data Flow Diagram](./data-flow.md) | How data flows through the depsgraph |
| [Node Hierarchy](./node-hierarchy.md) | The node type system explained |
| [Build Process](./build-process.md) | How the graph is constructed |
| [Evaluation Process](./evaluation-process.md) | How the graph is evaluated |

## Quick Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Blender Application                            │
├─────────────────────────────────────────────────────────────────────────┤
│  Editors (3D View, Properties, Outliner, etc.)                          │
│  ↕ tag updates                                              ↕ query     │
├─────────────────────────────────────────────────────────────────────────┤
│                     DEG Public API (DEG_depsgraph*.hh)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│   │   Builder   │───▶│  Depsgraph  │◀───│  Evaluator  │                │
│   │   System    │    │    Core     │    │   System    │                │
│   └─────────────┘    └─────────────┘    └─────────────┘                │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│   ┌─────────────────────────────────────────────────────┐              │
│   │                    Node System                       │              │
│   │  (IDNode, ComponentNode, OperationNode, Relations)  │              │
│   └─────────────────────────────────────────────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Data System (DNA/BKE)                               │
│            (Scenes, Objects, Meshes, Materials, etc.)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. Copy-on-Evaluation (CoW)
The depsgraph maintains **evaluated copies** of data blocks separate from original data. This allows:
- Thread-safe evaluation
- Non-destructive editing
- Multiple evaluation contexts (viewport vs render)

### 2. Three-Level Node Hierarchy
```
IDNode (per data-block)
  └── ComponentNode (per aspect: Transform, Geometry, Animation, etc.)
        └── OperationNode (per atomic operation)
```

### 3. Relations
Directed edges between nodes that define:
- Data dependencies
- Evaluation order
- Update propagation paths

### 4. Tagging System
When data changes:
1. The ID is **tagged** for update
2. Tags **flush** through relations to dependent nodes
3. Only tagged nodes are **evaluated**

## Source Code Location

The depsgraph source code is located at:
```
source/blender/depsgraph/
├── DEG_depsgraph*.hh      # Public API headers
└── intern/
    ├── depsgraph*.cc/hh   # Core implementation
    ├── builder/           # Graph construction
    ├── eval/              # Evaluation engine
    ├── node/              # Node types
    └── debug/             # Debugging/visualization
```
