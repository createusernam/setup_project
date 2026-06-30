# Pipeline v2 — от ценностного предложения до релиза

Единый сквозной процесс. Sources of truth:
- Process — этот файл
- Prompt format + PCAM — `PROMPT-FORMAT.md`
- Cross-model compat — `COMPAT.md`
- GRACE markup — `templates/project/docs/knowledge-graph.xml`

**Три обязательных правила:**
1. **GRACE Lite mandatory** — MODULE_CONTRACT во всех файлах
2. **product_brief.md** — стартовый артефакт pipeline; заполняется в Phase -1 (или вручную)
3. **Collegium** — reviewer и implementer ДОЛЖНЫ быть разными моделями

---

## Когерентный флоу (9 фаз)

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE -1: PRODUCT DISCOVERY [/methodology or manual]        │
│  Fill product_brief.md using your product discovery methodology │
│  Criteria: PM approval required before entering Phase 0.        │
│  Gate: metamodel distortion check + PM review                │
│  Output: product_brief.md (status: pm-approved)              │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  INPUT: product_brief.md                                    │
│  ↓ metamodel distortion check (PROMPT-FORMAT.md §Metamodel) │
└─────────────────────────────────────────────────────────────┘
          │
          ▼  [gaps in product_brief.md?]
┌──────────────────────────────────┐
│  PHASE 0: /researcher            │
│  Model:  Workers=Flash,          │
│          Synth=Sonnet,           │
│          Orch=Opus               │
│  Output: research-state.json     │
│  → fill gaps in product_brief.md │
└──────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│  PHASE 1: /grill-with-docs       │
│  Model:  Opus/Sonnet             │
│  Input:  product_brief.md        │
│  Output: CONTEXT.md, domain.md,  │
│          docs/adr/               │
└──────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│  PHASE 2: /planning-with-files   │
│  Model:  Opus (PBS decomposition)│
│  Input:  product_brief.md        │
│  Output: task_plan.md, tasks ≤200│
│          lines each              │
│  ┌────────────────────────────┐  │
│  │ Architecture-first order:  │  │
│  │ 1. Layers (depth)          │  │
│  │ 2. Modules (width)         │  │
│  │ 3. Scenarios (SDD)         │  │
│  │ Each layer: RFC round       │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
          │
          ▼  [PM VALIDATION — GATE]
┌──────────────────────────────────┐
│  PHASE 2-PM: PM review           │
│  Agent: product-manager          │
│  Model: Opus (isolated context,  │
│         ≠ implementer model)     │
│  Input: task_plan.md +           │
│         product_brief.md         │
│  Check:                          │
│  · Arch layers trace to user     │
│    journey (product_brief §7)    │
│  · Each layer → success criterion│
│    (product_brief §8)            │
│  · Edge cases have tasks         │
│  · ≥3 arch options scored before │
│    selecting (superposition)     │
│  Output: pm-review.json          │
│  GATE: APPROVE required          │
└──────────────────────────────────┘
          │ GATE: PM APPROVE
          ▼  [GRACE Full? ≥2/4 criteria]
┌──────────────────────────────────┐
│  PHASE 2b: /grace-init           │
│  + /grace-plan                   │
│  Output: docs/knowledge-graph.xml│
│          docs/development-plan.xml│
│          docs/verification-plan.xml│
└──────────────────────────────────┘
          │
          ▼  [Frontend?]
┌──────────────────────────────────┐
│  PHASE 3: /design-first          │
│  Model:  Sonnet (wireframes),    │
│          Opus (gate approval)    │
│  Output: wireframe → APPROVE     │
│          → api-contract.json     │
└──────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│  PHASE 4: /contract              │
│  Model:  Opus                    │
│  Inherits: value_prop, api-contract│
│  Output: contract.json (sha256)  │
│  → /judge → GATE (PASS required) │
└──────────────────────────────────┘
          │ GATE: judge PASS
          ▼
┌──────────────────────────────────┐
│  PHASE 5: /to-issues             │
│  Output: GitHub issues           │
│  Each issue = PBS leaf task      │
│  Size: ≤200 lines implementation │
└──────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 6: BUILD LOOP (per task, per wave)                    │
│                                                              │
│  [IMPLEMENTER: DeepSeek V4 / GLM 5.2]                       │
│    ↓ reads task + contract.json + GRACE anchors              │
│    ↓ PLAN_CONFIRM before coding                              │
│    ↓ writes code with GRACE Lite markup                      │
│    ↓ writes handoff.json                                     │
│                                                              │
│  [TEST-OWNER: GLM 5.2] ← DIFFERENT MODEL than implementer   │
│    ↓ reads handoff.json + code                               │
│    ↓ writes/runs tests                                       │
│    ↓ AGREE/DISAGREE verdict on implementation                │
│                                                              │
│  [ACCEPTOR: Opus]                                            │
│    ↓ reads test results + handoff                            │
│    ↓ accept → next task OR reject → implementer loop         │
│                                                              │
│  /build-loop (autonomous) OR /tdd (human-paced)             │
└──────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│  PHASE 7: /judge feature         │
│  Model:  Opus (isolated context) │
│  → /code-review-expert           │
│  → ship                          │
└──────────────────────────────────┘

State files at each transition:
  [methodology/value_proposition_mk.md] → product_brief.md (Phase -1, private)
  product_brief.md → research-state.json → CONTEXT.md
  → task_plan.md → pm-review.json → contract.json → handoff.json → judge-report.json
```

---

## PBS — Purpose Breakdown Structure

Декомпозировать цели от корня до листьев. Каждый лист = одна задача ≤200 строк / ≤2000 токенов.

```
GOAL_ROOT (из product_brief.md §1 — creator's intent)
  ├── GOAL_1: Архитектурный слой (depth)
  │   ├── PBS_LEAF_1a: auth layer scaffold (≤200 lines, DeepSeek V4)
  │   └── PBS_LEAF_1b: auth tests (≤150 lines, GLM)
  └── GOAL_2: UI слой (width)
      ├── PBS_LEAF_2a: login form component (≤180 lines, GLM)
      └── PBS_LEAF_2b: form tests (≤100 lines, GLM)
```

**Почему ≤200 строк?** SFT = "вырванные страницы из книги". Модель связывает страницы через goal alignment, не через позицию в файле. Большие задачи вызывают strategic blindness (атрибуция пропадает после ~800 строк). Маленькие листья + явная цель = надёжный результат.

**Порядок декомпозиции:**
1. Архитектурные слои (depth) — defines coupling/cohesion
2. Модули по объёму (width) — defines complexity bounds
3. Сценарии/SDD (leaf) — actual implementation

RFC-раунд между слоями: Opus генерирует RFC → GLM/Sonnet review → human approval.

---

## Ветки решений

### Branch 0 — Research нужен?

| Условие | Действие |
|---------|----------|
| product_brief.md заполнен (status: pm-approved) | Пропустить `/researcher` |
| product_brief.md есть, но есть gaps | `/researcher` → заполнить gaps (market/technical/user mode) |
| product_brief.md не заполнен | Запустить Phase -1: `/methodology` (private) или заполнить вручную |
| Только багфикс | Короткий путь: `/triage → /diagnose → /tdd → commit` |

> **Encapsulation**: `/researcher --mode mk` используется только внутри `/methodology` (Phase -1).
> В фазах 0–7 МК-терминология не появляется.

### Branch A — GRACE Full или Lite?

**GRACE Lite** (обязателен везде, без исключений):
- MODULE_CONTRACT в каждом файле
- START_BLOCK/END_BLOCK для логических блоков
- Логи привязаны к блокам

**GRACE Full** (если ≥ 2 из 4 критериев):

| Критерий | True когда |
|----------|-----------|
| Модулей ≥5 с кросс-ссылками | Сложная feature surface |
| Multi-session | Переживёт `/clear` и `/compact` |
| Long-context | LLM читает 50k+ токенов |
| Multi-agent | Несколько агентов редактируют одни файлы |

GRACE Full добавляет: `docs/knowledge-graph.xml`, `docs/development-plan.xml`, `docs/verification-plan.xml`.

### Branch B — Frontend?

| Решение | Действие |
|---------|----------|
| NO | Пропустить `/design-first`, `is_frontend=false` в contract |
| YES, первая UI-фича | `/design-first` → wireframe → одобрение → api-contract → `/design-rubric` |
| YES, design-contract.json есть | `/contract` inherits автоматически |

**Порядок для frontend:**
1. `/design-first` → wireframe → человеческое одобрение (HARD STOP)
2. API проектируется из wireframe (выход: `api-contract.json`)
3. `/design-rubric` (если впервые) → `design-contract.json`
4. `/contract` → inherits оба контракта

### Branch C — autonomous или human-paced?

| Решение | Skill | Когда |
|---------|-------|-------|
| Autonomous | `/build-loop` | Greenfield, полный contract, Playwright MCP |
| Human-paced | `/tdd` v2 | Backend, сложная логика |
| Bugfix | `/tdd` без contract | Issue = spec |

---

## Collegium Protocol

**Проблема**: кодер и ревьюер из одной модели договариваются не замечать ошибки. Без судьи коллегия плохо выбирает.

**Требование**: каждая роль — РАЗНАЯ модель.

```
IMPLEMENTER (DeepSeek V4)
    ↓ code + handoff.json
TEST-OWNER (GLM 5.2) ← обязательно другая модель
    ↓ AGREE/DISAGREE verdict
ACCEPTOR / JUDGE (Opus, isolated context)
    ↓ final verdict
```

Если TEST-OWNER соглашается с IMPLEMENTER автоматически — это красный флаг. Хорошая коллегия = обнаруженные разногласия, объяснённые в handoff.

Полная командная конфигурация: `agents/team.md`.

---

## GRACE Lite — обязательные правила

Применяются **ко всем проектам без исключений**.

### 1. MODULE_CONTRACT в каждом файле

```
// FILE: path/to/file.ext
// START_MODULE_CONTRACT
//   PURPOSE: [Что делает модуль — одно предложение]
//   SCOPE: [Что включено]
//   DEPENDS: [Зависимости]
//   BLOCK_LIMIT: 200 lines / 2000 tokens
// END_MODULE_CONTRACT
```

### 2. Функциональные контракты

```
// START_CONTRACT: functionName
//   PURPOSE: [Что делает]
//   INPUTS: { param: Type }
//   OUTPUTS: { ReturnType }
//   SIDE_EFFECTS: [или "none"]
// END_CONTRACT: functionName
```

### 3. Логические блоки

```
// START_BLOCK_VALIDATE_INPUT
...
// END_BLOCK_VALIDATE_INPUT
```

### 4. Логи привязаны к блокам

```
logger.info("[Module][function][BLOCK_NAME] message", { correlationId });
```

### 5. Блок-лимит

Каждый MODULE_CONTRACT block ≤2000 токенов. Большие модули → разбить на под-блоки через START_BLOCK/END_BLOCK. Это же ограничение применяется к PBS_LEAF задачам.

---

## State-First Principle

Все скиллы: читают state → производят следующий state → сохраняют в файл.

```
Agent reads current state → produces next state → saves to file
```

LLM мыслит переходами состояний (Belief State в residual stream), а не событийными потоками. State-файлы — это якоря Belief State между хода агентов.

**Верификация = чтение state dump**, не трейс кода.

Цепочка state-файлов:
```
[methodology/value_proposition_mk.md]  — private, Phase -1 only
product_brief.md                       — pipeline entry (pm-approved)
  → research-state.json (после /researcher, если gaps)
  → CONTEXT.md (после /grill-with-docs)
  → task_plan.md (после /planning-with-files)
  → pm-review.json (после Phase 2-PM — GATE)
  → contract.json (после /contract)
  → handoff.json (после каждого BUILD шага)
  → judge-report.json (после /judge)
```

---

## Structured Output Format

Все агентские скиллы возвращают JSON:

```json
{
  "status": "success | error | needs_info | needs_approval",
  "goal_achieved": true,
  "data": {},
  "confidence": 0.0,
  "hypotheses": [
    { "id": "h1", "description": "...", "score": 0.0, "evidence": [] }
  ],
  "selected_hypothesis": "h1",
  "handoff": {
    "done": [],
    "files_touched": [],
    "uncertain_about": [],
    "test_status": "pass|fail|not_run",
    "next_agent": ""
  },
  "issues": [],
  "trace": [],
  "next_action": ""
}
```

**Superposition principle**: перед коллапсом агент явно перечисляет ≥3 гипотезы, оценивает, выбирает. Обязательно для: research outputs, architecture decisions, design decisions, judge verdicts.

---

## LLM-as-Judge (`/judge`)

Изолированный evaluator — другая модель или отдельный контекст (не связан с generator).

Запускать:
- После `product_brief.md` → тип `product-brief`
- После `/contract` → тип `contract`
- После `/planning-with-files` → тип `plan`
- После завершения фичи → тип `feature`

Подробная рубрика: `skills/judge/SKILL.md`.

---

## Фазы × Skills × Models

| Фаза | Skill | Model | Артефакты |
|------|-------|-------|-----------|
| -1. Discovery | `/methodology` (private) | Flash→Sonnet→Opus | `product_brief.md`, `methodology/*.json` |
| 0. Research | `/researcher` | Flash→Sonnet→Opus | `research-state.json` |
| 1. Discovery | `/grill-with-docs` | Opus/Sonnet | `CONTEXT.md`, `docs/adr/` |
| 2. Planning | `/planning-with-files` | Opus (PBS) | `task_plan.md` |
| 2-PM. PM gate | PM agent | Opus (isolated) | `pm-review.json` |
| 2b. GRACE Full | `/grace-init`, `/grace-plan` | Opus | `docs/*.xml` |
| 3. Design | `/design-first` | Sonnet + Opus gate | `api-contract.json` |
| 4. Contract | `/contract` | Opus | `contract.json` |
| 4b. Judge gate | `/judge` | Opus (isolated) | `judge-report.json` |
| 5. Issues | `/to-issues` | Sonnet | GitHub issues |
| 6. Build | `/tdd` / `/build-loop` | DeepSeek V4 + GLM | commits + `handoff.json` |
| 7. Verify | `/judge feature` | Opus (isolated) | `judge-report.json` |
| 8. Review | `/code-review-expert` | Sonnet/Opus | review report |

---

## Антипаттерны

| ❌ Не делай | ✅ Вместо |
|-----------|----------|
| Пропускать `product_brief.md` | Заполни через `/methodology` или вручную (см. шаблон) |
| МК-термины в фазах 0–7 | Encapsulation: вся терминология методологии — только в Phase -1 |
| Пропускать PM validation в Phase 2 | Архитектура ДОЛЖНА трассироваться до user journey из product_brief §7 |
| Пропускать MODULE_CONTRACT | GRACE Lite обязателен везде |
| Пропускать metamodel distortion check | Проверь входные данные перед исследованием |
| Проектировать API без wireframe | Сначала `/design-first` → одобрение → API |
| Задачи > 200 строк | PBS: декомпозируй до листьев |
| Reviewer = та же модель что Implementer | Collegium: разные модели (agents/team.md) |
| Одна гипотеза без альтернатив | Superposition: ≥3 гипотезы в output |
| Agent output без JSON схемы | Structured format везде |
| Кодировать сразу без PLAN_CONFIRM | Агент строит план → APPROVE → code |
| Большой spec → один context | PBS: small leaf tasks, goal alignment |

---

## Bugfix Path

```
/triage (state machine: needs-triage → needs-info → ready-for-agent → ...)
  → /diagnose
  → /tdd (issue = spec, без contract.json)
  → commit
```

---

## One-time setup

```bash
# Claude Code:
git clone https://github.com/createusernam/setup.git ~/.setup
bash ~/.setup/install.sh   # symlinks skills, checks deps

# OpenCode:
git clone https://github.com/createusernam/setup.git ~/.setup
# Add PIPELINE.md + COMPAT.md reference to ~/.config/opencode/opencode.json
# See COMPAT.md §OpenCode

# Новый проект:
/startup <project-name>    # Claude Code
# или вручную: скопировать templates/project/ в новую папку
```
