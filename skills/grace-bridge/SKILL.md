---
name: grace-bridge
description: Decision guide and integration map between our Matt-Pocock pipeline and the GRACE framework. Use when starting an architecturally complex task and deciding whether to introduce GRACE XML scaffolding alongside our existing /grill-with-docs → /planning-with-files → /tdd flow. Triggers — 'apply grace', 'grace pipeline', 'should I use grace', 'grace for this task', 'hybrid pipeline', 'mix grace with our skills', 'грейс'.
---

# GRACE bridge — когда и как интегрировать с нашим pipeline

Skill — **гид принятия решения**, не исполнитель. Отвечает на (a) **стоит ли** вводить GRACE на этой задаче и (b) **как** встроить grace-* skills в существующий flow без дублирования.

## Когда использовать GRACE

Применять GRACE-артефакты (`docs/requirements.xml`, `docs/development-plan.xml` и т.д.) **только** если выполнены хотя бы два условия:

- Модулей ≥ 5 с кросс-ссылками; навигация grep'ом становится шумной
- Multi-session работа, переживающая `/clear` и `/compact`; нужны стабильные семантические координаты вместо номеров строк
- Long-context модель (Opus 1M, Gemini) будет читать 50k+ токенов кода; XML-маркеры помогают sparse attention
- Несколько агентов будут править одни и те же файлы; нужна контрактная поверхность от конфликтов

**Пропустить GRACE** для: багфиксов, рефакторов одного модуля, обновлений документации, простых добавлений фич.

## Карта pipeline

Существующий pipeline уже покрывает большинство GRACE. Вставлять grace-* только в пробелах:

| Фаза | Наш скилл | GRACE скилл | Когда вставлять GRACE |
|------|-----------|-------------|----------------------|
| Доменный язык | `/grill-with-docs` (термины → CONTEXT.md + ADR) | — | Всегда начинать здесь. GRACE этого не заменяет. |
| Bootstrap проекта | (вручную) | `/grace-init` | Первый раз на новом архитектурно-сложном модуле |
| Планирование | `/planning-with-files` (task_plan.md) | `/grace-plan` (development-plan.xml) | Использовать оба: task_plan операционный, development-plan — контракты |
| Дизайн верификации | (в TDD) | `/grace-verification` | Когда тестов недостаточно (нужны trace markers, log invariants) |
| Декомпозиция | `/to-issues` (GitHub) | — | Всегда наш скилл; vertical slices в issues |
| Реализация | `/tdd` (red-green-refactor) | — | Всегда наш скилл, не `/build-loop` |
| Ревью | `/code-review-expert`, `/review` | — | Всегда наши |
| Дебаг | `/diagnose` | — | Всегда наш |
| Архитектурное углубление | `/improve-codebase-architecture` | `/grace-refactor` | grace-refactor когда rename затрагивает много модулей и контракты двигаются с кодом |
| Drift check | (вручную) | `/grace-refresh` | После multi-session работы, перед возвратом в кодовую базу |
| Q&A по архитектуре | (вручную `Read`) | `/grace-ask` | Быстрее повторного чтения документов когда артефакты уже есть |
| Health check | (вручную) | `/grace-status` | Периодически между сессиями |

## Двухуровневая модель артефактов

GRACE разделяет **shared public docs** и **file-local private markup**:

**Уровень 1: Shared (в `<project>/docs/`)**
- `requirements.xml` — use cases (Actor-Action-Goal), дополняет ADR
- `technology.xml` — стек, версии, ограничения. Рядом с `<project>/CLAUDE.md` (где правила для агента)
- `development-plan.xml` — контракты модулей, фазы, зависимости
- `verification-plan.xml` — тестовые команды, сценарии, trace markers
- `knowledge-graph.xml` — карта модулей с LINKS; "содержание" для агента
- `operational-packets.xml` (опц.) — шаблоны execution/delta/failure packet

**Уровень 2: File-local (в исходниках)**
- `MODULE_CONTRACT` — XML-блок в шапке файла: PURPOSE/SCOPE/DEPENDS/LINKS
- `START_BLOCK_<NAME>` / `END_BLOCK_<NAME>` — семантические якоря для навигации и патчей
- `START_CONTRACT:` / `END_CONTRACT:` — контракт на функцию
- `LINKS:` — обратные ссылки на shared артефакты

См. `templates/module-contract-stub.md` для шаблона.

## Правило гранулярности (Proportional Granularity)

Один семантический блок ≈ **одно sliding window** (~500 токенов). Если блок растёт — дробить.

Связь с нашими лимитами:
- Memory: MEMORY.md ≤ 200 строк, memory-file ≤ 300 строк, CLAUDE.md ≤ 200 строк
- GRACE code: семантический блок ≤ ~500 токенов (≈ 30–60 строк в зависимости от языка)

## Что НЕ брать из GRACE (и почему)

- `/build-loop` / `/build-loop` — `/tdd` — наш execution loop. GRACE-execute дженерик, TDD опинионированный и работает.
- `/diagnose` → `/tdd` — `/diagnose` уже делает reproduce → minimise → hypothesise → fix.
- `/grace-reviewer` — `/code-review-expert` откалиброван под наши стандарты.
- `grace-cli` (Bun-based линтер) — не скопирован. Не нужен Bun runtime; ручные проверки `grep`+`Read` достаточны на нашем масштабе.
- `/grace-setup-subagents` — у нас уже 16 ролевых агентов в `~/.claude/agents/`.
- Habr-style attention hacks (CAPS-LOCK, профанити) — вне scope, перпендикулярно нашей design-дисциплине.

## Шаги развёртывания GRACE на проекте

Когда `/grace-bridge` решил "да, применять", типичный путь:

1. `/grill-with-docs` — сначала подтвердить доменные термины (CONTEXT.md + ADR)
2. `/grace-init` — скаффолд `docs/requirements.xml`, `docs/technology.xml`, `docs/development-plan.xml`, `docs/verification-plan.xml`, `docs/knowledge-graph.xml` из шаблонов
3. `/grace-plan` — заполнить `development-plan.xml` модулями, контрактами, зависимостями
4. `/grace-verification` — log-driven trace markers для критичных переходов состояния
5. Добавить `MODULE_CONTRACT` хедеры в критичные файлы (шаблон в `templates/module-contract-stub.md`)
6. Продолжить с `/to-issues` → `/tdd` как обычно
7. После волны изменений — `/grace-refresh` для drift check

## PCAM — родственный подход

PCAM (Purpose Centric Agent Methodology) — за goal-oriented контроль агента вместо жёстких скриптов. Большинство наших skills уже PCAM-совместимы (SKILL.md описывает goal + рекомендованные шаги, агент свободен внутри). Принципы для опоры:

- **Примат цели над инструкцией** — заявить *зачем*, не только *что*. Уже в `/grill-with-docs`.
- **Гайды, не скрипты** — наши skills — гайды. Не пересепечивать.
- **Self-healing** — агент может выбрать альтернативный путь при сбое. Поощрять в `/loop` циклах.
- **Plugin/service архитектура** — не применимо к нашему monorepo стилю.
- **Feedback loop** — `/triage` state machine — наш обратный цикл "user ↔ agent".

## Sources

- https://github.com/osovv/grace-marketplace (osovv, v3.11.0, MIT)
- https://habr.com/ru/articles/993896/ (Habr: GRACE + PCAM)
- VK / TurboPlanner — оригинальные статьи: GRACE framework spec, PCAM spec
