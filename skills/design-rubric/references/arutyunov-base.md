# Arutyunov IDS — base rubric

Source: Артемий Арутюнов, Internet Design System (IDS). Условный пересказ принципов под `design-contract.json`.

## Принципы

1. **Density-based spacing.** Пять токенов — `xs, sm, md, lg, xl`. Magic numbers (`padding: 12px`) запрещены — всегда `var(--space-*)`.
2. **Один breakpoint.** `@media (min-width: 768px)` — desktop. Всё ниже — mobile by default. Никаких 480/640/1024/1280.
3. **Минимум визуальных слоёв.** Карточки без shadows, no border-radius на полях форм (border-radius только на pill-кнопках), no gradients.
4. **Контент-first.** UI хром (хедеры, навигация) ≤15% высоты экрана. Контент занимает остальное.
5. **Сетка без сетки.** Container max-width 720px (mobile-first reading width). На desktop расширяется до 960px (для side-by-side контента).
6. **Кнопки — текст с подложкой, не иконки.** Иконки только усиление (трейлинг/леад), не замена текста.

## Criteria for design-contract.json

```json
[
  {
    "id": "ids-spacing-token",
    "category": "design",
    "weight": 3,
    "check": "padding/margin from --space-*, no magic numbers",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE '(padding|margin):\\s*[0-9]+(px|rem)' src/ --include='*.css' | grep -v 'var(--space-'"
    }
  },
  {
    "id": "ids-breakpoint-single",
    "category": "design",
    "weight": 3,
    "check": "Only @media (min-width: 768px)",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE '@media[^{]*(min|max)-width:\\s*(?!768px)[0-9]+px' src/ --include='*.css'"
    }
  },
  {
    "id": "ids-no-shadows",
    "category": "design",
    "weight": 2,
    "check": "No box-shadows on content cards",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE 'box-shadow:\\s*[^n]' src/ --include='*.css' | grep -v 'box-shadow:\\s*none'"
    }
  },
  {
    "id": "ids-no-gradients",
    "category": "design",
    "weight": 2,
    "check": "No CSS gradients (background uses solid colors)",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE '(linear|radial|conic)-gradient' src/ --include='*.css'"
    }
  },
  {
    "id": "ids-button-text-first",
    "category": "design",
    "weight": 2,
    "check": "Buttons render visible text — never icon-only without aria-label",
    "verify": {
      "method": "playwright",
      "steps": "for each <button>: if it has no text content, expect aria-label attribute non-empty"
    }
  },
  {
    "id": "ids-container-width",
    "category": "design",
    "weight": 1,
    "check": "Main content container max-width 720px mobile / 960px desktop",
    "verify": {
      "method": "playwright",
      "steps": "viewport 1440×900; locate main; getBoundingClientRect.width ≤ 960. viewport 375×812; getBoundingClientRect.width ≤ 720"
    }
  }
]
```
