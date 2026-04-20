# Deep Object Traversal Audit

Tracking issue: [#162](https://github.com/D-sorganization/OpenSim_Models/issues/162)

## Scope

Static audit of the `src/` tree (and `scripts/`) for attribute-chain expressions
matching the regex `\w+\.\w+\.\w+\.\w+` — i.e. anything that dereferences at
least four dotted names in a row. Long chains frequently mask Law-of-Demeter
(LoD) violations: a caller reaching through intermediate objects to touch a
grandchild's state, which tightly couples consumers to internal layout.

## Methodology

```bash
grep -rEn '\w+\.\w+\.\w+\.\w+' src/ scripts/
```

Each hit was classified as one of:

- **Import idiom** — `from opensim_models.a.b.c import X`. Not a traversal; the
  package hierarchy is namespace metadata and does not constitute runtime
  object-graph walking.
- **Framework idiom** — `logging.getLogger(__name__)`, `np.linalg.norm(...)`,
  `xml.etree.ElementTree.SubElement(...)` and similar calls through a stable
  library namespace. These are API-surface calls, not LoD violations.
- **Real LoD** — Production code reaching through 3+ intermediate object
  attributes to touch internal state (e.g. `model.body.joint.parent.frame`).

## Findings

### Headline result

**No real LoD violations found in `src/`.**

All 49 hits in `src/` are **import idiom** — every match is a
`from opensim_models.<subpkg>.<module> import ...` statement, produced by the
repo's deliberately shallow-but-namespaced package layout (e.g. the four-level
path `opensim_models.shared.utils.xml_helpers`). These are compile-time
namespace references, not runtime attribute chains.

`scripts/` and root-level modules produced zero non-import matches.

### Distribution of the 49 import hits

| Subpackage path                           | Hits |
| ----------------------------------------- | ---- |
| `opensim_models.shared.utils.*`           | 14   |
| `opensim_models.shared.body.*`            | 10   |
| `opensim_models.shared.contracts.*`       | 6    |
| `opensim_models.shared.parity.*`          | 1    |
| `opensim_models.shared.barbell.*`         | 2    |
| `opensim_models.exercises.<name>.<mod>`   | 16   |

### Why there are no runtime LoD hotspots

1. The model builders use **local variables** for bodies/joints (`humerus_body`,
   `elbow_joint`) rather than traversing an aggregate model tree. Attribute
   chains stop at depth 2 (`body.mass`, `joint.coordinates[0]`).
2. XML construction goes through `shared/utils/xml_helpers.py` helper
   functions that accept and return leaf elements — callers never walk the
   ElementTree.
3. Contract helpers (`require_positive`, postcondition assertions) operate on
   leaf values passed in by the caller; they don't drill into nested objects.

## Recommendations

- **No refactor required.** The `src/` tree is already LoD-compliant by the
  >=3-hop heuristic.
- **Future drift guard (optional):** add a lightweight lint rule or a
  `pytest` static check that flags any non-`from`/`import` line containing
  `\w+\.\w+\.\w+\.\w+` inside `src/opensim_models/`. The current baseline
  (zero hits) makes this a cheap ratchet.
- Re-run this audit whenever the builder classes grow helper properties, as
  property-chain accessors (`self.model.rig.state.x`) are the most common way
  LoD creeps back in.

## Reproduction

```bash
# Full scan (includes imports)
grep -rEn '\w+\.\w+\.\w+\.\w+' src/

# Non-import traversals only (expected: empty)
grep -rEn '\w+\.\w+\.\w+\.\w+' src/ | grep -vE ':\s*(from |import )'
```

## Related audits

Parallel deep-traversal audits ran across the fleet as part of wave 33 (see
`MuJoCo_Models`, `Drake_Models`, `Pinocchio_Models`, and `UpstreamDrift`).
