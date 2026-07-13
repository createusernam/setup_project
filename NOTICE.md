# Third-party attribution

## GRACE skills

These skills are derived from [osovv/grace-marketplace](https://github.com/osovv/grace-marketplace)
(v3.11.0), distributed under the MIT License:

`grace-ask` · `grace-explainer` · `grace-init` · `grace-plan` · `grace-refactor` · `grace-refresh` ·
`grace-status` · `grace-verification`

They are adapted for this harness rather than vendored verbatim: references to the optional
`@osovv/grace-cli` binary, and to skills that do not exist here (`$grace-execute`,
`$grace-multiagent-execute`, `$grace-fix`), are repointed at this setup's own gates —
`scripts/grace-lint.sh`, `/build-loop`, `/tdd`, `/diagnose`, `/grace-ask`.

`grace-bridge`, `grace-ontology` and `scaffold` were written for this repository.

The GRACE methodology itself (Graph-RAG Anchored Code Engineering) is the work of its author,
published via VK / TurboPlanner. This repository implements the published methodology; it does not
redistribute the author's proprietary material.

### MIT License (as carried by the upstream project)

```
MIT License

Copyright (c) 2026 GRACE Framework Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Design references

The design rubrics under `skills/design-rubric/references/` restate publicly published design
principles (Arutyunov IDS; Birman / Bureau Gorbunov) as machine-checkable criteria. They paraphrase;
they do not reproduce the source texts.
