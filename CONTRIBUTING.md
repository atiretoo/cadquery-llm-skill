# Contributing

Contributions are welcome. The goal is a skill that helps LLMs write correct,
idiomatic CadQuery code - so quality and accuracy matter more than coverage.

## What to Contribute

- **Corrections** - wrong selector descriptions, incorrect API signatures, misleading explanations
- **Anti-patterns** - real mistakes you have seen LLMs make, with a minimal reproducible example
- **Common patterns** - verified, runnable recipes for tasks that come up frequently
- **Examples** - annotated scripts in `examples/` that demonstrate specific concepts
- **Docs updates** - refreshing `docs/` when CadQuery releases a new version

## Ground Rules

### All code examples must be verified

Run every snippet before submitting. The multimethod dispatch in the Free Function API
is especially sensitive to argument types - if it runs without error and produces the
expected shape, it belongs here. If you are not sure, say so in the PR description.

### No fabricated patterns

Do not add patterns based on what seems plausible. If you have not verified it works,
it doesn't belong in `patterns/` or `examples/`. Unverified content that looks correct
is worse than no content - it's the exact problem this skill is trying to solve.

### Prefer minimal examples

A snippet that demonstrates one concept in 5-10 lines is more useful than a complete
parametric part. The goal is to show the LLM *how to think*, not to provide templates.

### Keep the BRep mindset

New patterns should reflect idiomatic CadQuery - workplane operations over booleans,
selectors over hardcoded coordinates, tags over index selectors. If you are adding a
pattern that uses a boolean, make sure there genuinely is not a feature operation that
does the job.

## File Structure

```
SKILL.md                  # Quick-reference — edit with care, keep it dense
concepts/
  brep-mindset.md         # Core mental model
  workplanes.md           # Fluent API workplane mechanics
  selectors.md            # Selector syntax and matching rules
  free-function-api.md    # Free Function API reference
patterns/
  anti-patterns.md        # What not to do, with fixes
  common-patterns.md      # Verified idiomatic recipes
examples/
  *.py                    # Annotated runnable scripts
docs/
  *.rst / *.md            # CadQuery documentation snapshot (for local grep)
Modelfile                 # Hand-crafted Ollama model definition (see below)
scripts/
  build_ollama_modelfile.py  # Generates a full-content Modelfile from markdown sources
```

## Adding an Anti-Pattern

1. Add a numbered section to `patterns/anti-patterns.md`
2. Show the wrong version first, then the correct version
3. Explain *why* the wrong version fails - silently wrong geometry is more important to flag than errors
4. If it's also worth a one-liner in `SKILL.md`'s critical anti-patterns table, add it there

## Adding a Common Pattern

1. Add a section to `patterns/common-patterns.md` under the appropriate API heading
2. Include a brief explanation of *why* this is the preferred approach
3. Keep it to one focused concept per pattern
4. Test it - see ground rules above

## Adding an Example

Examples live in `examples/` as standalone `.py` files. Each file should:

- Run without modification (`python examples/myexample.py` should not error)
- Have a `result` variable that holds the final shape (for CQ-editor / Jupyter compatibility)
- Include comments explaining *why*, not just *what*
- Focus on one or two concepts (selectors, workplane navigation, Free Function assembly, etc.)

Suggested naming: `<concept>_<brief-description>.py`, e.g. `selectors_tag_based.py`

## Updating the Docs Snapshot

The `docs/` directory contains a local snapshot of the CadQuery documentation for
offline grepping. When CadQuery releases a new version:

1. Copy the updated RST source from the CadQuery repo into `docs/`
2. Note the CadQuery version in a `docs/VERSION` file
3. Review `SKILL.md` and the concept files for anything that needs updating

## The Modelfile

`Modelfile` is a hand-crafted artifact optimized for Ollama's use case. It is separate
from the markdown source files - the two are intentionally independent because Claude Code
and Ollama are different consumers with different needs.

- Edit `Modelfile` directly to improve the Ollama experience
- The markdown files (`SKILL.md`, `concepts/`, `patterns/`) are the source of truth for Claude Code
- If you add a verified example to `examples/` that would be useful in the Modelfile, consider adding it there too
- `scripts/build_ollama_modelfile.py` generates an alternative full-content Modelfile from the markdown sources - useful if you want to experiment with larger models that can handle more context

