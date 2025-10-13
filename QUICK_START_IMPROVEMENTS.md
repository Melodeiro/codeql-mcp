# 🚀 Быстрый Старт - Критичные Исправления

**Время выполнения**: ~1.5 часа  
**Приоритет**: ВЫСОКИЙ  
**Статус**: Ready to implement

> 💡 **Это краткий чеклист для критичных изменений**. Полный код и детали смотри в [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md)

---

## Что исправляем

1. ✅ Windows temp paths - **15 минут** → [Детали](#шаг-2-windows-temp-paths-15-мин)
2. ✅ Argument injection - **15 минут** → [Детали](#шаг-3-argument-injection-protection-15-мин)
3. ✅ Subprocess timeouts - **30 минут** → [Детали](#шаг-4-subprocess-timeouts-30-мин)
4. ✅ Type hints - **30 минут** → [Детали](#шаг-5-type-hints-30-мин)

---

## Шаг 1: Создать ветку (1 мин)

```bash
git checkout -b feature/critical-security-fixes
```

---

## Шаг 2: Windows Temp Paths (15 мин)

### Что делать

**Файл**: `server.py`

1. В начало добавить:
```python
import tempfile
from pathlib import Path
TEMP_DIR = Path(tempfile.gettempdir()) / "codeql-mcp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
```

2. Заменить `/tmp/` на `str(TEMP_DIR / ...)` в строках: 60, 118, 282, 339

📖 **Полный код**: [IMPROVEMENT_PLAN.md → Критичные исправления → 1](IMPROVEMENT_PLAN.md#1-windows-temp-paths-15-минут)

---

## Шаг 3: Argument Injection Protection (15 мин)

### Что делать

1. **Создать** `tools/constants.py` с `ALLOWED_LANGUAGES`, `LANGUAGE_TO_PACK`, timeouts
2. **Обновить** `tools/database.py`:
   - Импорт: `from .constants import ALLOWED_LANGUAGES, ...`
   - Валидация в `create_database_impl` (строка ~42)
3. **Обновить** `tools/discovery.py`:
   - Импорт: `from .constants import LANGUAGE_TO_PACK, ...`
   - Валидация в `discover_queries_impl` (строка ~118)

📖 **Полный код**: [IMPROVEMENT_PLAN.md → Критичные исправления → 2](IMPROVEMENT_PLAN.md#2-argument-injection-protection-15-минут)

---

## Шаг 4: Subprocess Timeouts (30 мин)

### Что делать

Добавить `timeout=TIMEOUT_*` во все `subprocess.run()` и обработку `TimeoutExpired`:

- **tools/database.py**: строки ~59, ~84, ~107
- **tools/analysis.py**: строки ~28, ~67
- **tools/discovery.py**: строки ~12, ~35, ~84, ~125
- **codeqlclient.py**: строка ~380

📖 **Полный код**: [IMPROVEMENT_PLAN.md → Критичные исправления → 3](IMPROVEMENT_PLAN.md#3-subprocess-timeouts-30-минут)

---

## Шаг 5: Type Hints (30 мин)

### Что делать

Добавить type hints во все функции:

- **tools/database.py**: `qs: 'CodeQLQueryServer'`, `-> str`, `-> dict[str, str | int]`
- **tools/query.py**: аналогично
- **tools/results.py**: добавить `Literal["json", "csv", "text"]`
- **tools/discovery.py**: аналогично
- **tools/analysis.py**: аналогично
- **validation.py**: добавить `TypedDict` для `ValidationResult`

Во всех использовать `TYPE_CHECKING` блок для импорта `CodeQLQueryServer`.

📖 **Полный код**: [IMPROVEMENT_PLAN.md → Критичные исправления → 4](IMPROVEMENT_PLAN.md#4-type-hints-1-час)

---

## Шаг 6: Тестирование (10 мин)

```bash
uv run pytest -v  # Должно быть: 82+ tests passed
```

Если ошибки → проверь импорты, timeouts, except блоки

---

## Шаг 7: Commit & Push (3 мин)

```bash
git add -A
git commit -m "Add critical security and compatibility improvements

- Fix Windows temp paths using tempfile.gettempdir()
- Add argument injection protection with language whitelist
- Add subprocess timeouts to prevent hangs
- Add comprehensive type hints

Tested: All 82 tests passing"

git push -u origin feature/critical-security-fixes
```

---

## ✅ Чеклист

- [ ] TEMP_DIR создан в server.py
- [ ] Все `/tmp/` пути заменены на `str(TEMP_DIR / ...)`
- [ ] tools/constants.py создан
- [ ] ALLOWED_LANGUAGES валидация в create_database_impl
- [ ] LANGUAGE_TO_PACK валидация в discover_queries_impl
- [ ] Все subprocess.run() имеют timeout
- [ ] Все subprocess вызовы обрабатывают TimeoutExpired
- [ ] Type hints добавлены во все tools/*.py
- [ ] Type hints добавлены в validation.py
- [ ] Все тесты проходят: `uv run pytest -v`
- [ ] Commit сделан
- [ ] Push выполнен

---

## 🎯 Ожидаемый результат

После этих изменений:
- ✅ Код работает на Windows
- ✅ Защита от argument injection
- ✅ Subprocess не зависают навсегда
- ✅ IDE показывает типы и автокомплит
- ✅ Все 82+ тестов проходят

---

## 📞 Если что-то пошло не так

1. **Тесты падают**
   - Проверь, что все импорты добавлены
   - Убедись, что timeout добавлен во все subprocess.run()
   - Проверь, что except блоки обновлены

2. **Import errors**
   - Убедись, что tools/constants.py создан
   - Проверь, что все from .constants import ... корректны

3. **Type errors**
   - Убедись, что TYPE_CHECKING блок есть
   - Проверь, что все 'CodeQLQueryServer' в кавычках

4. **Нужна помощь**
   - Посмотри полный план: `IMPROVEMENT_PLAN.md`
   - Посмотри guidelines: `CONTRIBUTING.md`

---

**Готово!** После этих изменений переходи к следующему этапу из `IMPROVEMENT_PLAN.md`.
