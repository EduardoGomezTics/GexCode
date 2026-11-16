# GexCode (PyOptiX)

**Transpilador y optimizador fuente-a-fuente en Python basado en Árboles de Sintaxis Abstracta (AST)**, diseñado para detectar y refactorizar automáticamente patrones ineficientes en soluciones de programación competitiva y scripts de alto rendimiento, validando la equivalencia semántica y midiendo la aceleración real obtenida.

> Sin dependencias externas: construido íntegramente sobre la biblioteca estándar de Python (`ast`, `subprocess`, `timeit`, `argparse`, `dataclasses`).

---

## Tabla de contenidos

- [Descripción general y propósito](#-descripción-general-y-propósito)
- [Arquitectura y funcionamiento](#-arquitectura-y-funcionamiento)
- [Reglas de optimización implementadas](#-reglas-de-optimización-implementadas)
- [Ejemplo de uso y Benchmark](#-ejemplo-de-uso-y-benchmark)
- [Instalación y ejecución](#-instalación-y-ejecución)
- [Estructura del proyecto](#-estructura-del-proyecto)

---

## Descripción general y propósito

En programación competitiva, Python ofrece gran expresividad, pero ciertos modismos habituales (como contar caracteres manualmente en un bucle, construir listas con `.append()` o iterar con `range(len(...))`) introducen una sobrecarga significativa en el intérprete que puede provocar veredictos de **Time Limit Exceeded (TLE)**.

**GexCode (PyOptiX)** resuelve este problema analizando el código fuente mediante su **AST**, aplicando transformaciones automáticas que delegan el trabajo pesado a primitivas optimizadas en C dentro de CPython (como `str.count()`, *list comprehensions* e iteración directa), y verificando en un sandbox aislado que la salida del programa optimizado sea **100% idéntica** a la original.

---

## Arquitectura y funcionamiento

El motor sigue un diseño desacoplado basado en el contrato abstracto `OptimizationRule` (`optimization/base_rule.py`), que separa la **detección** (`detect`), la **transformación** (`transform`) y la **validación** (`validate`), apoyándose en los modelos de datos de `core/models.py` (`Finding`, `Optimization`, `AnalysisReport`, `BenchmarkResult`).

```
Archivo .py ──▶ ast.parse() ──▶ [ Bucle Multi-Pasada ] ──▶ ast.unparse() ──▶ *_optimized.py
                                   │             ▲                                │
                                   ▼             │                                ▼
                           Detección por   ASTReplacer +                  Sandbox (subprocess)
                            prioridad    fix_missing_locations             stdin/stdout check
                                                                                  │
                                                                                  ▼
                                                                          Benchmark (timeit)
```

### 1. Pipeline Multi-Pasada (`run_pipeline.py`)
En lugar de aplicar una sola pasada, `run_full_pipeline` ejecuta un ciclo iterativo (`while True`) que reevalúa el AST después de cada transformación hasta alcanzar un punto fijo (cuando ninguna regla reporta hallazgos):
- **Orden de prioridad de reglas:** `DeadCodeRule` → `StringCountRule` → `ListCompRule` → `RangeLenRule`.
- **Reescritura segura:** `ASTReplacer` (subclase de `ast.NodeTransformer`) reemplaza nodos transformados o elimina sentencias obsoletas (`nodes_to_remove`), y `ast.fix_missing_locations(tree)` resincroniza los números de línea y columna antes de la siguiente pasada.
- **Generación de código:** Al finalizar, reconstruye el código fuente mediante `ast.unparse(tree)` en `<archivo>_optimized.py`.

### 2. Sandbox de Validación (`subprocess`)
Antes de aceptar cualquier optimización, `run_pipeline.py` ejecuta tanto el script original como el optimizado en subprocesos aislados mediante `subprocess.run(..., input=mock_input, capture_output=True)` con una entrada masiva de prueba por `stdin` (4,000,000 de caracteres):
- Verifica que ambos procesos finalicen con `returncode == 0`.
- Compara byte a byte `orig_proc.stdout == opt_proc.stdout`.
- Si la salida difiere, la validación falla, se elimina automáticamente el archivo `*_optimized.py` y se aborta el proceso.

### 3. Motor de Benchmarking (`timeit`)
Superada la validación semántica, ambos scripts se ejecutan mediante `timeit.timeit` (`iterations = 3`) invocando sus respectivos subprocesos. Los promedios en milisegundos y el factor de aceleración (`speedup = original_time_ms / optimized_time_ms`) se consolidan en `BenchmarkResult` y se imprimen en el reporte final.

---

## Reglas de optimización implementadas

| ID | Regla | Riesgo | Descripción |
| :--- | :--- | :--- | :--- |
| `OPT_001` | [`RangeLenRule`](optimization/rules/range_len_rule.py) | `Safe` | Detecta bucles `for i in range(len(lista)):` y los reescribe a iteración directa `for item in lista:`, sustituyendo los accesos `lista[i]` dentro del cuerpo mediante `RangeLenBodyTransformer`. |
| `OPT_002` | [`StringCountRule`](optimization/rules/string_count_rule.py) | `Safe` | Detecta bucles `for c in cadena:` cuyo cuerpo es una cadena `if` / `elif` de comparaciones de igualdad (`==`) con asignaciones aumentadas (`+=` / `-=`), reemplazando el bucle por llamadas nativas `.count()`. |
| `OPT_003` | [`ListCompRule`](optimization/rules/list_comp_rule.py) | `Safe` | Detecta el patrón `res = []` seguido de un bucle `for` con asignaciones temporales previas a un `.append(...)` final; realiza *inlining* de dichas variables (`Inliner`) y transforma el bloque en una *list comprehension*. |
| `OPT_004` | [`DeadCodeRule`](optimization/rules/dead_code_rule.py) | `Medium` | Analiza funciones (`ast.FunctionDef`) comparando variables escritas (`ast.Store` en `Assign` / `AugAssign`) contra variables leídas (`ast.Load`), eliminando asignaciones a variables nunca leídas (respeta variables con prefijo `_`). |

---

## Ejemplo de uso y Benchmark

### Antes vs. Después (`OPT_002` — `StringCountRule`)

Ejemplo real ejecutado sobre [`examples/test_string_count.py`](examples/test_string_count.py) procesando una cadena de **4,000,000** de movimientos por `stdin`:

**Antes (`examples/test_string_count.py`):**
```python
if __name__ == "__main__":
    n = int(input())
    moves = input()
    x = 0
    y = 0
    for move in moves:
        if move == 'R':
            x += 1
        elif move == 'L':
            x -= 1
        elif move == 'F':
            y += 1
        elif move == 'B':
            y -= 1
    print(f"{x} {y}")
```

**Después (`examples/test_string_count_optimized.py`):**
```python
if __name__ == '__main__':
    n = int(input())
    moves = input()
    x = 0
    y = 0
    x += moves.count('R')
    x -= moves.count('L')
    y += moves.count('F')
    y -= moves.count('B')
    print(f'{x} {y}')
```

### Resultados de Benchmark (`timeit`, 3 iteraciones)

| Archivo objetivo | Regla aplicada | Tiempo Original | Tiempo Optimizado | Aceleración |
| :--- | :--- | :---: | :---: | :---: |
| `examples/test_string_count.py` | `OPT_002` (`StringCountRule`) | `525.29 ms` | `71.12 ms` | **7.39x faster** |

---

## Instalación y ejecución

### Requisitos
- **Python 3.9 o superior** (requerido por `ast.unparse`; probado en Python 3.12).
- No requiere `pip install` ni paquetes de terceros.

```bash
git clone <url-del-repositorio>
cd Gex
```

### Comandos CLI

Puedes invocar la CLI mediante `python -m cli.main` (o directamente con `./pyoptix` en entornos Unix/macOS):

1. **Analizar un archivo sin modificarlo** (detecta ineficiencias y muestra línea e ID de regla):
   ```bash
   python -m cli.main analyze examples/test_string_count.py
   ```

2. **Optimizar un archivo** (genera `<archivo>_optimized.py`):
   ```bash
   python -m cli.main optimize examples/test_string_count.py
   ```

3. **Ejecutar el pipeline completo** (optimización multi-pasada + validación en sandbox + benchmark con `timeit`):
   ```bash
   python -m cli.main benchmark examples/test_string_count.py
   ```
   O directamente mediante el script del pipeline:
   ```bash
   python run_pipeline.py examples/test_string_count.py
   ```

4. **Ejecutar el analizador independiente (`PyOptixEngine`)**:
   ```bash
   python run_analyzer.py
   ```

### Ejecución de tests

El proyecto incluye pruebas de idempotencia del round-trip AST (`ast.parse` → `ast.unparse` → `ast.parse`) y pruebas de transformación de nodos:

```bash
# Verifica que el AST se mantiene estructuralmente idéntico tras ast.unparse()
python test_idempotency.py

# Verifica detección y transformación visual de nodos AST
python test_transform.py
```

---

## Estructura del proyecto

```text
Gex/
├── cli/
│   └── main.py                         # Interfaz CLI (analyze, optimize, benchmark)
├── core/
│   └── models.py                       # Dataclasses: Finding, Optimization, AnalysisReport, BenchmarkResult
├── examples/
│   ├── test_string_count.py            # Ejemplo de entrada con conteo manual en bucle
│   └── test_string_count_optimized.py  # Salida optimizada usando .count()
├── optimization/
│   ├── base_rule.py                    # Clase base abstracta OptimizationRule
│   └── rules/
│       ├── range_len_rule.py           # OPT_001: range(len(...)) -> iteración directa
│       ├── string_count_rule.py        # OPT_002: conteo en bucle -> .count()
│       ├── list_comp_rule.py           # OPT_003: append en bucle -> list comprehension
│       └── dead_code_rule.py           # OPT_004: eliminación de asignaciones no leídas
├── .gitignore                          # Reglas de exclusión estándar para Python
├── pyoptix                             # Script ejecutable de entrada a la CLI
├── README.md                           # Documentación principal del proyecto
├── run_pipeline.py                     # Orquestador multi-pasada, sandbox y benchmark
├── run_analyzer.py                     # Motor PyOptixEngine para análisis estático
├── test_idempotency.py                 # Test de round-trip estructural del AST
└── test_transform.py                   # Test unitario de transformación AST
```
