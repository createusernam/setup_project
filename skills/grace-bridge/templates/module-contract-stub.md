# MODULE_CONTRACT и семантические блоки — шаблон

Готовые формы для добавления GRACE-разметки в существующий код. Использовать когда `/grace-plan` подтвердил контракт модуля и пора материализовать его в файле.

## 1. MODULE_CONTRACT (шапка файла)

```ts
// START_MODULE_CONTRACT
//   PURPOSE: [Что делает модуль — одно предложение]
//   SCOPE: [Какие операции включены, какие НЕ включены]
//   DEPENDS: [Список зависимостей: M-001 (UserRepo), M-014 (ClockService)]
//   LINKS: [Узлы knowledge-graph: KG/api/auth, KG/domain/User]
// END_MODULE_CONTRACT

import { ... } from '...'
```

Пример (домен-агностичный):

```ts
// START_MODULE_CONTRACT
//   PURPOSE: Build the dependency tree for a session based on incoming events.
//   SCOPE: Tree construction, node weighting, pruning. NOT: rendering, persistence, side effects.
//   DEPENDS: M-021 (ScoringService), M-022 (EventOracle), M-030 (SessionMemory)
//   LINKS: KG/core/dep-tree, KG/core/scoring-balance
// END_MODULE_CONTRACT
```

## 2. START_CONTRACT (контракт функции)

```ts
// START_CONTRACT: buildTree
//   PURPOSE: Construct a dependency tree given a session seed and scoring snapshot.
//   INPUTS: { seed: SessionSeed, balance: ScoreBalance }
//   OUTPUTS: { tree: DepTree — root + nodes with weights, pruned to depth 5 }
//   SIDE_EFFECTS: none
//   LINKS: KG/core/dep-tree-algorithm
// END_CONTRACT: buildTree
export function buildTree(seed: SessionSeed, balance: ScoreBalance): DepTree {
  // ...
}
```

## 3. START_BLOCK_ / END_BLOCK_ (семантические якоря внутри функции)

```ts
export function buildTree(seed, balance) {
  // START_BLOCK_ROOT_SELECTION
  const rootEvent = oracle.castFromSeed(seed)
  const rootNode = createNode(rootEvent, balance)
  // END_BLOCK_ROOT_SELECTION

  // START_BLOCK_BRANCH_EXPANSION
  const branches = expandBranches(rootNode, depth: 5)
  // END_BLOCK_BRANCH_EXPANSION

  // START_BLOCK_PRUNING
  return pruneByWeight(branches, threshold: 0.3)
  // END_BLOCK_PRUNING
}
```

Правила:
- Имена блоков **уникальны в файле** (можно повторяться между файлами)
- Размер блока ≤ ~500 токенов (≈ 30–60 строк) — Proportional Granularity
- Парные теги обязательны — не оставлять открытых блоков
- Имена семантичны (`ROOT_SELECTION`, не `BLOCK_1`)

## 4. Структурированный лог (привязка к якорю)

```ts
// START_BLOCK_PRUNING
log.info('dep-tree.pruning.start', {
  block: 'PRUNING',
  module: 'M-040-dep-tree',
  branchCount: branches.length,
  threshold: 0.3,
})
const result = pruneByWeight(branches, threshold: 0.3)
log.info('dep-tree.pruning.done', {
  block: 'PRUNING',
  keptCount: result.nodes.length,
  prunedCount: branches.length - result.nodes.length,
})
return result
// END_BLOCK_PRUNING
```

Это даёт RAG-агенту координату: от строки лога → к точке в коде через `block:` поле + grep по `START_BLOCK_PRUNING`.

## 5. Когда НЕ добавлять разметку

- Файл утилитарный (<100 строк), одна экспортируемая функция — достаточно JSDoc
- Тестовый файл — контракт виден из имён describe/it
- Конфиг или фикстура — это данные, не код

GRACE-разметка — для **архитектурно-нагруженных** модулей (бизнес-логика, нарративная механика, графовые алгоритмы). Не размечать всё подряд — это создаёт шум.

## 6. Ссылки на оригинал

- `~/.claude/skills/grace-explainer/references/contract-driven-dev.md`
- `~/.claude/skills/grace-explainer/references/semantic-markup.md`
- `~/.claude/skills/grace-explainer/references/unique-tag-convention.md`
