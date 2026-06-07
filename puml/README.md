# Diagramming Conventions — k9x_studiox/puml

Source `.puml` + rendered `.png` live side by side here (e.g.
`k9_streams_architecture.puml` + `.png`). Render with:

```
plantuml -tpng <file>.puml
```

## Class diagrams

- **Abstract vs. concrete marking is a hard rule, not a style choice.**
  Any class with at least one method left unimplemented (an abstract
  contract method, e.g. `BaseAgent.execute()`, or a class that
  deliberately stays abstract like `K9SubAgentSpawner` — "mechanics
  only, no `execute()`") **must** be declared `abstract class` so
  PlantUML renders it with the **A** icon, not **C**. Mark the
  unimplemented method itself with `{abstract}`.

  ```
  abstract class BaseAgent {
    + {abstract} execute(payload: dict) : dict
  }

  abstract class K9SubAgentSpawner {
    + spawn_parallel(specs) : list
    + {abstract} execute(payload: dict) : dict
  }

  class SpecParserAgent {
    + execute(payload: dict) : dict   ' implements it — concrete (C)
  }
  ```

- Group agents that belong to the same squad inside a `package "<SquadName>"`
  block — it visually answers "where does this live?" without having to
  re-draw the whole architecture.

## Known PlantUML quirks (this version: 1.2025.9)

- **Don't mix `artifact` and `class` elements across separate `package`
  blocks** — it trips a parser bug (`Error line N`, often pointing at an
  unrelated line). Use a stereotyped `class "name.yaml" as Alias <<YAML>>`
  instead of `artifact "name.yaml" as Alias` to represent config/YAML
  files — renders identically, no parser issue.
- **Avoid `==` inside note text** (e.g. `governance.passed == true`) —
  PlantUML can parse it as a heading-separator marker. Write `is true`
  instead.
- **Avoid `{...}` annotations after a method signature** inside a class
  body (e.g. `spawn_parallel(specs) : list {ThreadPoolExecutor}`) — `{}`
  is reserved for member modifiers like `{abstract}`/`{static}` and can
  cause cascading parse errors reported on a later, unrelated line. Use
  parentheses instead: `spawn_parallel(specs) : list (ThreadPoolExecutor)`.
- **Activity-diagram swim lanes (`|Lane|`) are always vertical columns
  with top-down flow** — there is no skinparam or syntax to rotate them
  into horizontal BPMN-pool bands (the Blueworks/draw.io look). That
  layout requires a different tool (draw.io/diagrams.net, Visio, an
  actual BPMN modeler).

## Scope discipline

- A "light"/pattern-focused diagram should stay focused on the pattern.
  If you find yourself adding orchestrator → squad → frontend → backend
  to it, you're rebuilding the full architecture diagram inside the
  light one — stop, and point readers at the detailed diagram instead.
