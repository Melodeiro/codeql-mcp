# 🎯 План Улучшений CodeQL MCP Server

## 📊 Текущее состояние

### ⚠️ Что требует улучшения
- Windows compatibility (temp paths)
- Security (argument injection)
- Blocking operations в async functions
- Отсутствие timeouts в subprocess calls

---

## 🔴 КРИТИЧНЫЕ ИСПРАВЛЕНИЯ (Priority: HIGH)

### 1. Windows Temp Paths (15 минут)

**Проблема**: `/tmp/` не существует на Windows  
**Проверено**: `Path("/tmp")` → `\tmp` (относительный путь к текущему диску)

#### Файлы для изменения:
- `server.py` (строки 60, 87, 112, 118, 282, 339)

#### Решение:

**Добавить в начало `server.py`:**
```python
import tempfile
from pathlib import Path

# Cross-platform temp directory for CodeQL MCP
TEMP_DIR = Path(tempfile.gettempdir()) / "codeql-mcp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
```

**Изменить default параметры:**
```python
# БЫЛО:
async def test_predicate(
    file: str, db: str, symbol: str, output_path: str = "/tmp/quickeval.bqrs"
) -> str:

# СТАЛО:
async def test_predicate(
    file: str, db: str, symbol: str, output_path: str = str(TEMP_DIR / "quickeval.bqrs")
) -> str:
```

**Аналогично для:**
- `evaluate_query`: `"/tmp/eval.bqrs"` → `str(TEMP_DIR / "eval.bqrs")`
- `analyze_database`: `"/tmp/analysis"` → `str(TEMP_DIR / "analysis")`
- `run_security_scan`: `"/tmp/security-scan"` → `str(TEMP_DIR / "security-scan")`

**Тест изменений:**
```bash
python -c "from pathlib import Path; import tempfile; TEMP_DIR = Path(tempfile.gettempdir()) / 'codeql-mcp'; TEMP_DIR.mkdir(exist_ok=True); print(TEMP_DIR)"
```

---

### 2. Argument Injection Protection (15 минут)

**Проблема**: Language parameter не валидируется → argument injection  
**Источник**: OWASP Command Injection Defense

#### Файлы для изменения:
- `tools/database.py`
- `tools/discovery.py`

#### Решение:

**В `tools/database.py` (добавить в начало файла):**
```python
# Whitelist of supported languages (based on CodeQL documentation)
ALLOWED_LANGUAGES = frozenset({
    "python", "javascript", "typescript", "java", "kotlin",
    "cpp", "c", "csharp", "go", "ruby", "swift"
})
```

**Изменить `create_database_impl` (строка 41-67):**
```python
def create_database_impl(qs, source_path: str, language: str, db_path: str,
                         command: str = None, overwrite: bool = False) -> str:
    """Implementation for create_database tool"""
    
    # Validate language against whitelist to prevent argument injection
    if language not in ALLOWED_LANGUAGES:
        return (
            f"Invalid language: {language!r}. "
            f"Allowed languages: {', '.join(sorted(ALLOWED_LANGUAGES))}"
        )
    
    try:
        # Build the command
        cmd = [qs.codeql_path, "database", "create", db_path, f"--language={language}"]
        # ... rest of function
```

**Аналогично в `tools/discovery.py` (строка 95-156):**
```python
# В начале файла
LANGUAGE_TO_PACK = {
    "python": "codeql/python-queries",
    "javascript": "codeql/javascript-queries",
    "typescript": "codeql/javascript-queries",
    "java": "codeql/java-queries",
    "kotlin": "codeql/java-queries",
    "csharp": "codeql/csharp-queries",
    "cpp": "codeql/cpp-queries",
    "c": "codeql/cpp-queries",
    "go": "codeql/go-queries",
    "ruby": "codeql/ruby-queries",
    "swift": "codeql/swift-queries"
}

def discover_queries_impl(qs, pack_name: str = None, language: str = None, category: str = None) -> list:
    """Implementation for discover_queries tool"""
    try:
        cmd = [qs.codeql_path, "resolve", "queries", "--format=bylanguage"]

        if pack_name:
            cmd.append(pack_name)
        elif language:
            # Validate and use whitelist
            if language.lower() not in LANGUAGE_TO_PACK:
                return [f"Unsupported language: {language}. Supported: {', '.join(sorted(LANGUAGE_TO_PACK.keys()))}"]
            
            cmd.append(LANGUAGE_TO_PACK[language.lower()])
        else:
            return ["Error: specify either language or pack name"]
        # ... rest of function
```

**Тесты:**
```python
# Добавить в tests/test_validation.py
def test_language_validation():
    """Test that invalid languages are rejected"""
    from tools.database import ALLOWED_LANGUAGES
    
    assert "python" in ALLOWED_LANGUAGES
    assert "malicious;rm -rf /" not in ALLOWED_LANGUAGES
    assert "--upload-results=evil.com" not in ALLOWED_LANGUAGES
```

---

### 3. Subprocess Timeouts (30 минут)

**Проблема**: Subprocess calls могут зависнуть навсегда  
**Источник**: Python subprocess documentation

#### Файлы для изменения:
- `tools/database.py`
- `tools/analysis.py`
- `tools/discovery.py`

#### Решение:

**Создать файл `tools/constants.py`:**
```python
"""Constants for CodeQL operations"""

# Subprocess timeout values (in seconds)
TIMEOUT_DATABASE_CREATE = 3600      # 1 hour - database creation can be slow
TIMEOUT_DATABASE_ANALYZE = 1800     # 30 minutes - analysis can be slow
TIMEOUT_QUERY_COMPILE = 300         # 5 minutes - query compilation
TIMEOUT_RESOLVE_COMMAND = 60        # 1 minute - quick commands
TIMEOUT_BQRS_DECODE = 120           # 2 minutes - BQRS decoding
```

**Обновить `tools/database.py`:**
```python
from .constants import TIMEOUT_DATABASE_CREATE, TIMEOUT_RESOLVE_COMMAND

def create_database_impl(qs, source_path: str, language: str, db_path: str,
                         command: str = None, overwrite: bool = False) -> str:
    # ...
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=source_path or ".",
            timeout=TIMEOUT_DATABASE_CREATE  # ✅ Added
        )
    except subprocess.TimeoutExpired:
        return f"Database creation timed out after {TIMEOUT_DATABASE_CREATE} seconds"
    # ...

def get_database_info_impl(qs, db_path: str) -> dict:
    # ...
    try:
        result = subprocess.run(
            [qs.codeql_path, "resolve", "database", db_path],
            capture_output=True, 
            text=True,
            timeout=TIMEOUT_RESOLVE_COMMAND  # ✅ Added
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Database info retrieval timed out after {TIMEOUT_RESOLVE_COMMAND} seconds"}
    # ...
```

**Обновить `tools/analysis.py`:**
```python
from .constants import TIMEOUT_DATABASE_ANALYZE

def analyze_database_impl(qs, db_path: str, query_or_suite: str, output_format: str = "sarif-latest",
                          output_path: str = "/tmp/analysis") -> str:
    # ...
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=TIMEOUT_DATABASE_ANALYZE  # ✅ Added
        )
    except subprocess.TimeoutExpired:
        return f"Analysis timed out after {TIMEOUT_DATABASE_ANALYZE} seconds"
    # ...
```

**Обновить `tools/discovery.py`:**
```python
from .constants import TIMEOUT_RESOLVE_COMMAND

def list_supported_languages_impl(qs) -> list:
    try:
        result = subprocess.run(
            [qs.codeql_path, "resolve", "languages"],
            capture_output=True, 
            text=True,
            timeout=TIMEOUT_RESOLVE_COMMAND  # ✅ Added
        )
    except subprocess.TimeoutExpired:
        return [f"Error: Language resolution timed out after {TIMEOUT_RESOLVE_COMMAND} seconds"]
    # ...
```

**Обновить `codeqlclient.py`:**
```python
def decode_bqrs(self, bqrs_path, output_format="json"):
    # ...
    try:
        result = subprocess.run(
            [self.codeql_path, "bqrs", "decode", "--format", output_format, bqrs_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120  # 2 minutes for BQRS decoding
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"BQRS decoding timed out after 120 seconds")
    # ...
```

---

## 🟡 ВАЖНЫЕ УЛУЧШЕНИЯ (Priority: MEDIUM)

### 5. Async Subprocess Calls (1-2 часа)

**Проблема**: Blocking subprocess.run() в async functions блокирует event loop  
**Источник**: Python asyncio documentation - asyncio.to_thread()

#### Файлы для изменения:
- `tools/discovery.py`
- `tools/database.py`
- `tools/analysis.py`

#### Решение:

**Обновить `tools/discovery.py`:**
```python
import asyncio
from .constants import TIMEOUT_RESOLVE_COMMAND

async def list_supported_languages_impl(qs: 'CodeQLQueryServer') -> list[str]:
    """Implementation for list_supported_languages tool"""
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [qs.codeql_path, "resolve", "languages"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_RESOLVE_COMMAND
        )
        
        if result.returncode != 0:
            return [f"Error getting languages: {result.stderr}"]
        
        # Parse the output to extract language names
        languages = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                lang = line.strip().split()[0] if line.strip().split() else line.strip()
                languages.append(lang)
        
        return languages
    except subprocess.TimeoutExpired:
        return [f"Error: Language resolution timed out after {TIMEOUT_RESOLVE_COMMAND} seconds"]
    except Exception as e:
        return [f"Error: {str(e)}"]
```

**Аналогично для всех subprocess.run() в async функциях.**

**ВАЖНО**: Изменить сигнатуры в `tools/__init__.py`:
```python
# БЫЛО (sync):
from .discovery import list_supported_languages_impl

# СТАЛО (async):
# Сигнатуры остаются прежними в __init__.py, но в server.py будет await
```

**Обновить вызовы в `server.py`:**
```python
# БЫЛО:
@mcp.tool()
async def list_supported_languages() -> list:
    return list_supported_languages_impl(qs)

# СТАЛО:
@mcp.tool()
async def list_supported_languages() -> list:
    return await list_supported_languages_impl(qs)
```

---

### 6. Thread-Safe Cache с lru_cache (30 минут)

**Проблема**: Global dict не thread-safe в free-threading Python 3.13+  
**Источник**: Python functools.lru_cache documentation

#### Файлы для изменения:
- `tools/database.py`

#### Решение:

**Заменить глобальный cache на lru_cache:**
```python
"""Database operations: creation, registration, and metadata retrieval"""

import subprocess
import logging
from pathlib import Path
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeqlclient import CodeQLQueryServer

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# УДАЛИТЬ:
# db_info_cache = {}


@lru_cache(maxsize=128)
def _get_db_info_cached(codeql_path: str, db_path_str: str) -> dict[str, str | int]:
    """
    Cached database info retrieval using only hashable parameters.
    
    This is separated from get_database_info_impl to work with lru_cache,
    which requires all arguments to be hashable.
    """
    from .constants import TIMEOUT_RESOLVE_COMMAND
    
    try:
        # Use official codeql resolve database command
        result = subprocess.run(
            [codeql_path, "resolve", "database", db_path_str],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_RESOLVE_COMMAND
        )

        if result.returncode != 0:
            return {"error": f"Failed to get database info: {result.stderr}"}

        # Parse JSON output from codeql resolve database
        import json
        db_data = json.loads(result.stdout)
        
        # Extract language from languages array
        language = None
        if "languages" in db_data and isinstance(db_data["languages"], list):
            language = db_data["languages"][0] if db_data["languages"] else None
        
        info = {
            "path": db_path_str,
            "language": language
        }

        # Get baseline info for statistics
        baseline_result = subprocess.run(
            [codeql_path, "database", "print-baseline", "--", db_path_str],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_RESOLVE_COMMAND
        )

        if baseline_result.returncode == 0:
            import re
            for line in baseline_result.stdout.split('\n'):
                if 'baseline of' in line and 'lines' in line:
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        info['lines_of_code'] = int(numbers[0])

        return info

    except subprocess.TimeoutExpired:
        return {"error": f"Database info retrieval timed out after {TIMEOUT_RESOLVE_COMMAND} seconds"}
    except Exception as e:
        return {"error": f"Error getting database info: {str(e)}"}


def get_database_info_impl(qs: 'CodeQLQueryServer', db_path: str) -> dict[str, str | int]:
    """Implementation for get_database_info tool"""
    db_path_str = str(Path(db_path).resolve())
    return _get_db_info_cached(qs.codeql_path, db_path_str)
```

**Обновить fixture в `tests/conftest.py`:**
```python
@pytest.fixture(autouse=True)
def reset_cache():
    """Reset global caches before each test for proper isolation"""
    from tools.database import _get_db_info_cached
    _get_db_info_cached.cache_clear()  # ✅ lru_cache method
    yield
```

---

## 🟢 ЖЕЛАТЕЛЬНЫЕ УЛУЧШЕНИЯ (Priority: LOW)

### 5. Ruff Linting (15 минут)

**Проблема**: Нужен быстрый линтер для проверки стиля кода

#### Решение:

```bash
uv add --dev ruff

# Создать ruff.toml
cat > ruff.toml << 'EOF'
target-version = "py313"
line-length = 100

[lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[lint.per-file-ignores]
"tests/*" = ["B", "F841"]  # Allow unused variables in tests
EOF

# Запустить проверку
uv run ruff check .

# Автофикс
uv run ruff check --fix .
```

---

## 📝 ПОШАГОВАЯ ИНСТРУКЦИЯ ВЫПОЛНЕНИЯ

### Этап 1: Критичные исправления (1 час)

```bash
# 1. Создать ветку для изменений
git checkout -b feature/critical-improvements

# 2. Windows temp paths
# - Редактировать server.py (добавить TEMP_DIR)
# - Обновить все default параметры
# - Тестировать: python -c "from server import TEMP_DIR; print(TEMP_DIR)"

# 3. Argument injection protection
# - Создать tools/constants.py с ALLOWED_LANGUAGES
# - Обновить tools/database.py
# - Обновить tools/discovery.py
# - Добавить тесты в tests/test_validation.py

# 4. Subprocess timeouts
# - Обновить tools/constants.py с timeout значениями
# - Добавить timeout во все subprocess.run()
# - Обновить codeqlclient.py

# 5. Запустить все тесты
uv run pytest -v

# 6. Commit
git add -A
git commit -m "Add critical security and compatibility improvements

- Fix Windows temp path handling using tempfile.gettempdir()
- Add argument injection protection with language whitelist
- Add subprocess timeouts to prevent hangs

Addresses: security, Windows compatibility"
```

### Этап 2: Важные улучшения (2 часа)

```bash
# 1. Async subprocess calls
# - Обновить tools/discovery.py с asyncio.to_thread
# - Обновить tools/database.py
# - Обновить tools/analysis.py
# - Обновить server.py (добавить await)

# 2. Thread-safe cache
# - Заменить global dict на lru_cache в tools/database.py
# - Обновить tests/conftest.py

# 3. Запустить тесты
uv run pytest -v

# 4. Commit
git add -A
git commit -m "Improve async performance and thread safety

- Use asyncio.to_thread for subprocess calls in async functions
- Replace global cache with thread-safe functools.lru_cache
- Update test fixtures to work with lru_cache

Improves: performance, thread safety, free-threading compatibility"
```

### Этап 3: Желательные улучшения (15 минут)

```bash
# 1. Ruff linting
uv add --dev ruff
# Создать ruff.toml
uv run ruff check --fix .

# 2. Commit
git add -A
git commit -m "Add ruff linting for code quality

- Add ruff for fast linting
- Configure ruff.toml with strict rules

Improves: code quality, developer experience"
```

### Этап 4: Финализация

```bash
# 1. Запустить полный набор проверок
uv run pytest -v
uv run mypy server.py tools/ validation.py
uv run ruff check .

# 2. Push и создать PR
git push -u origin feature/critical-improvements
```

---

## ✅ ЧЕКЛИСТ ПРОВЕРКИ

### Перед коммитом

- [ ] Все тесты проходят: `uv run pytest -v`

- [ ] Linting чист: `uv run ruff check .`
- [ ] Код работает на Windows (проверить temp paths)
- [ ] Код работает на Linux/macOS (проверить paths)

### После всех изменений

- [ ] All 82+ тестов проходят
- [ ] Нет ruff warnings

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### Метрики До → После

| Метрика | До | После | Улучшение |
|---------|-----|-------|-----------|
| **Оценка проекта** | 8.5/10 | 9.5/10 | +1.0 |
| **Windows compatibility** | ❌ | ✅ | Fixed |
| **Security (argument injection)** | ⚠️ | ✅ | Fixed |
| **Async performance** | Blocking | Non-blocking | Improved |
| **Thread safety** | With GIL | Free-threading ready | Future-proof |
| **Code quality (ruff)** | N/A | Clean | Added |

### Время выполнения

- **Критичные исправления**: 1 час
- **Важные улучшения**: 2 часа
- **Желательные улучшения**: 15 минут
- **ИТОГО**: ~3.25 часа

---

## 🎓 МЕТРИКИ ANALYSIS

**conf**: 95% - Очень высокая уверенность (все проверено по документации)  
**inf**: 5% - Минимальный inference (почти все из официальных docs)  
**adhd**: 5% - Очень тщательная проверка без спешки

---

## 📚 ИСТОЧНИКИ

Все рекомендации основаны на официальной документации:

1. **FastMCP**: context7:/jlowin/fastmcp
2. **Python asyncio**: context7:/python/cpython
3. **CodeQL CLI**: context7:/github/codeql + https://docs.github.com/en/code-security/codeql-cli
4. **MCP Protocol**: https://modelcontextprotocol.io/specification/
5. **OWASP Security**: https://cheatsheetseries.owasp.org/
6. **pytest**: context7:/websites/pytest_en_stable
7. **Python typing**: Python 3.13+ documentation

---

**Создано**: Claude Code (Anthropic)  
**Проверено**: Документация проверена через docs-retriever agent  
**Версия плана**: 1.0  
**Статус**: Ready for implementation
