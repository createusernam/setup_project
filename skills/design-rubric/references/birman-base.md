# Birman / Bureau Gorbunov — base rubric

Source: Илья Бирман и Бюро Горбунова. Реконструкция принципов в проверяемом виде.

## Принципы

1. **Near-black, never pure black.** Текст `#1a1a1a..#2d2d2d`. Pure `#000` — оптическая ошибка.
2. **20% opacity underlines.** Underline под ссылками — `currentColor` с alpha 0.2. Не `text-decoration-thickness: 2px` сине-яркие.
3. **Серый = много значений.** Не один `--color-muted`, а несколько: text-secondary, border, surface-elevated. Минимум 4 оттенка серого.
4. **Цвет — акцент, не дизайн-язык.** Один accent color на проект (брендовый). Остальное — оттенки серого/чёрного. Радуга функциональных цветов (зелёный success / красный error / жёлтый warning) допустима, но компактно.
5. **Типографика — иерархия размером, не весом.** Один вес (regular), различия через size. Bold только для очень редких акцентов.
6. **Картинки без рамок.** Изображения сами по себе — без border, без radius. Если нужно отделить — отделяй пространством.

## Criteria for design-contract.json

```json
[
  {
    "id": "birman-text-color",
    "category": "design",
    "weight": 3,
    "check": "Text color #1a1a1a..#2d2d2d или var(--color-text), не pure #000",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE 'color:\\s*(#000|#000000|black)\\s*[;}]' src/ --include='*.css'"
    }
  },
  {
    "id": "birman-underline-opacity",
    "category": "design",
    "weight": 2,
    "check": "Link underline opacity 0.2, currentColor",
    "verify": {
      "method": "playwright",
      "steps": "find an anchor with href; getComputedStyle.textDecorationColor parsed → alpha ≈ 0.2 (±0.05)"
    }
  },
  {
    "id": "birman-grey-palette",
    "category": "design",
    "weight": 2,
    "check": "≥4 named grey tokens (text, text-secondary, border, surface, surface-elevated)",
    "verify": {
      "method": "grep",
      "command": "grep -hE '--color-(text|text-secondary|border|surface|surface-elevated|grey-[0-9])' src/styles/tokens.css | sort -u | wc -l | awk '{ exit ($1 >= 4) ? 0 : 1 }'"
    }
  },
  {
    "id": "birman-one-accent",
    "category": "design",
    "weight": 2,
    "check": "Один accent color (var(--color-action-primary)); функциональные цвета (success/error/warning) ≤3",
    "verify": {
      "method": "manual",
      "prompt": "Inspect tokens.css. Count distinct chromatic colors (not greyscale, not white, not near-black). Expected: 1 accent + ≤3 functional. Score: 1.0 if ≤4 chromatic, 0.5 if 5-6, 0 if more. List the offending colors if any."
    }
  },
  {
    "id": "birman-typography-size-not-weight",
    "category": "design",
    "weight": 2,
    "check": "Type hierarchy uses font-size, not font-weight. Bold only on rare deliberate emphasis",
    "verify": {
      "method": "grep",
      "command": "BOLD_COUNT=$(grep -rE 'font-weight:\\s*(bold|[6-9][0-9][0-9])' src/ --include='*.css' | wc -l); REGULAR_COUNT=$(grep -rE 'font-weight:\\s*(normal|[34][0-9][0-9])' src/ --include='*.css' | wc -l); [ \"$BOLD_COUNT\" -lt \"$REGULAR_COUNT\" ]"
    }
  },
  {
    "id": "birman-images-no-border",
    "category": "design",
    "weight": 1,
    "check": "img elements have no border, no border-radius (unless avatar/decorative)",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE 'img\\s*\\{[^}]*(border:|border-radius:)' src/ --include='*.css'"
    }
  }
]
```
