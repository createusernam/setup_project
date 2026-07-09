# UI copy rubric

Job-to-be-done и Voice-of-customer формулировки в UI: копирайтинг говорит языком
пользователя, а не языком системы.

## Принципы

1. **JTBD-формулировки, не feature-описания.** Кнопка не «Создать цель» — а «Накопить на путешествие». Empty state не «Нет данных» — а «Здесь появятся ваши тренировки».
2. **Voice of customer.** Лексика взята из живой речи пользователей (CJM/интервью), не из IT-документации.
3. **Active voice.** «Сохраните прогресс», не «Прогресс будет сохранён».
4. **Конкретные числа в empty state.** Не «начните тренироваться» — а «начните с 3 тренировок в неделю».
5. **Никаких system-side abstractions в UI.** Без «item», «entity», «record». Доменные термины проекта.
6. **Negative framing допустимо только для destructive actions.** «Удалить навсегда» — да. «Ошибка валидации» — нет, пиши что именно не так.

## Criteria for design-contract.json

```json
[
  {
    "id": "copy-jtbd-button-labels",
    "category": "design",
    "weight": 3,
    "check": "Button labels formulate user job, not system action",
    "verify": {
      "method": "manual",
      "prompt": "Extract all visible button text from modified screens. For each: classify as JTBD ('Накопить...', 'Записать тренировку') or system-action ('Создать', 'Сохранить', 'Удалить'). Score: 1.0 if ≥80% JTBD on primary actions (destructive can be system-action). List offenders."
    }
  },
  {
    "id": "copy-empty-state-specific",
    "category": "design",
    "weight": 2,
    "check": "Empty states use concrete numbers and JTBD framing",
    "verify": {
      "method": "manual",
      "prompt": "For each visible empty state: does it tell user (a) what will appear, (b) how to get the first item, (c) ideally a concrete number? Score: 1.0 all three, 0.7 (a+b), 0.3 (a only), 0 generic 'no data'."
    }
  },
  {
    "id": "copy-no-system-abstractions",
    "category": "design",
    "weight": 2,
    "check": "No 'item', 'entity', 'record', 'данные' in UI strings — domain terms only",
    "verify": {
      "method": "grep",
      "command": "! grep -rnE \"['\\\"](item|entity|record|данные|запись|элемент)['\\\"]\\)?\" src/ --include='*.tsx' --include='*.ts' | grep -v test"
    }
  },
  {
    "id": "copy-active-voice",
    "category": "design",
    "weight": 1,
    "must_pass": false,
    "check": "Active voice; no 'будет сохранён', 'не удалось обработать'",
    "verify": {
      "method": "manual",
      "prompt": "Scan visible Russian strings for passive-voice constructions ('будет', 'не удалось', 'был выполнен'). Score: 1.0 if zero, 0.5 if ≤2 occurrences in non-error states, 0 if 3+. Allow passive in destructive confirmation if it reads better."
    }
  },
  {
    "id": "copy-error-specific",
    "category": "design",
    "weight": 2,
    "check": "Error messages tell what's wrong AND how to fix",
    "verify": {
      "method": "manual",
      "prompt": "Trigger every error path in the modified flow. For each error message: does it explain what (specifically, not 'Ошибка валидации') AND how to recover? Score: 1.0 all do, linear down."
    }
  }
]
```
