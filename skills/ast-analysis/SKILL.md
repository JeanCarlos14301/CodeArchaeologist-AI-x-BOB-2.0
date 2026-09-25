---
name: ast-analysis
description: >
  Static syntax tree inspection, call graph reconstruction, and entity relationship mapping
  using Tree-sitter parsers and native AST engines. Enables multi-language dependency
  cartography and circular reference detection.
metadata:
  origin: CodeArchaeologist
---

# AST Analysis & Structural Cartography Workflow

A language-agnostic static analysis workflow to extract call graphs, cyclomatic complexity, and database schemas directly from source code AST without executing the code.

## When to Use

- When mapping dependencies across complex legacy codebases without tests.
- When generating visual Entity-Relationship (ER) diagrams from ORM models or SQL schemas.
- When detecting circular dependencies, dead code blocks, or high fan-in architectural bottlenecks.
- Before executing a Strangler Fig cut to determine all callers of a function.

## Static Inspection Process

```
┌────────────────────────────────────────┐
│ Phase 1: Source AST Parsing           │ ── Tree-sitter / Python AST grammar traversal
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 2: Symbol & Call Site Extraction │ ── Function definitions, class methods, invocations
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 3: Directed Call Graph Assembly  │ ── Adjacency matrix of callers and callees
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 4: ER Schema & Mermaid Synthesis │ ── Table relationships, foreign keys, cardinailty
└────────────────────────────────────────┘
```

### Parsing Multi-Language Codebases

1. **Python**: Uses `ast` standard library module or `tree-sitter-python`.
2. **TypeScript / JavaScript**: Uses `@babel/parser`, `ts-morph`, or `tree-sitter-typescript`.
3. **Java**: Uses `javaparser` or `tree-sitter-java`.
4. **Go**: Uses `go/parser` and `go/ast` or `tree-sitter-go`.

### Metrics & Deliverables
- **Call Graph**: JSON-formatted adjacency list representing all execution paths.
- **Mermaid Diagrams**: Visual flowcharts of call graphs and ER diagrams of data entities.
- **Architectural Bottleneck Matrix**: Identification of "God Objects" and single points of architectural failure.
