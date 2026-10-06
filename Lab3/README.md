## Laboratorio 3 

###  Hardware / software de las mediciones

- CPU: AMD Ryzen 7 6800HS (8 núcleos) - RAM: 16 GB - OS: Windows 11
- Python 3.14.3 - matplotlib 3.11.1 - scipy 1.17.1

Resultado esperado:

| Estructura | Archivo | Búsqueda puntual | Búsqueda por rango | Listado ordenado |
|---|---|---|---|---|
| Lista nativa (Python `list`) | — (built-in) | Scan `O(N)` | Scan + filtro `O(N)` | `sorted()` `O(N log N)` |
| ABB (binario, sin balancear) | `ArboolABB.py` | `O(log N)` promedio, `O(N)` degenerado | Inorden con poda | Inorden `O(N)` |
| Árbol B+ (`t=3`) | `ArbolBplus.py` | `O(log N)` siempre | Baja a hoja + hojas enlazadas | Recorre hojas `O(N)` |

El caso crítico es el ABB con datosordenado ya que se degenera a
una lista enlazada (`O(N)` por operación y construcción `O(N²)`), mientras el
B+ mantiene tiempo logaritmico.

### ***Explicación archivos***

- ***generar_estudiantes.py***: genera `n` estudiantes con ids únicos .
- ***ArboolABB.py***, ***ArbolBplus.py*** : Algoritmos implementados para el arbol ABB y B+ respectivamente.
- ***Experimentos.py***: ejecuta los experimentos y exporta los resultados.
- ***test_normalidad.py*** : test de Shapiro-Wilk sobre las repeticiones. Justifica el uso de mediana sobre media para el analisis.
- ***Resultados*** — CSV y gráficas generadas.
- ***PruebaN***` — muestras crudas + resultado del test de normalidad.

## **Código de honor:**
#### Uso de ia: se usaron herramientas de ia para la generación de ciertas secciones de codigo, el cual fue revisado,comentado y modificado por mi antes de la implemtacion final. 
#### Este readme fue cocreado con gen ai, principalmente para las tablas y la estructura general, fue revisado y modificado por mi. 

## Parámetros (`CONFIG`)

| Parámetro | Valor             | Significado |
|---|-------------------|---|
| `N_BASE` | 1000              | `n`; tamaños `N = n·k` con `k` en `MULTIPLOS` (etiquetas `"kn"`) |
| `MULTIPLOS` | 5..20             | N = 5000, 6000, …, 20000 (se descartan N chicos: warm-up del sistema) |
| `N_BUSQUEDAS` | 1000              | búsquedas puntuales por medición (recortado a `min(N_BUSQUEDAS, N)`) |
| `REPETICIONES` | 30                | repeticiones por punto (mediana ± dispersión) |
| `RANGO_FRACCIONES` | 1%, 5%, 10%, 25%  | tamaños de rango evaluados |
| `T_BPLUS` | 3                 | grado mínimo del B+ |
| `SEED` | 42                | reproducibilidad |
| `BATCH_RANGO_LISTAR` | 20                | llamadas internas por repetición en rango/listar (se normaliza por llamada) |
| `M_VALORES` / `N_FIJO_M` | [10..5000] / 5000 | experimento variar-M con `N` fijo |

Experimentos, en orden: `busqueda_sin_build`, `busqueda_con_build`
(reconstruye dentro del timer: costo inserción + búsqueda),
`rango_{1,5,10,25}pct`, `listar_ordenado`, y variar-M (`N` fijo).


### Estadística

- Por punto se reportan mediana, media, stdev muestral, min, max, p25/p75.
- Las gráficas usan **mediana con barras de rango intercuartílico** (asimétricas)
  en escala logarítmica, porque las repeticiones no siempre son normales
  . Shapiro-Wilk
  (`p < 0.05` = se rechaza normalidad).

### 6. Hallazgos - completar 

-  ¿se comporta como predice la teoría? Compara `busqueda_sin_build`
  desordenados (las 3 deben escalar suave) vs ordenados (ABB se dispara, B+ no).]
-  ¿cuándo deja el ABB de ser `O(log N)`? Usa el factor `t(10n)/t(n)`
  de `resultados.csv` y las referencias del resumen.]
-  ¿qué muestra `busqueda_con_build`? (domina el costo de inserción:
  ABB ordenado `O(N²)`).]
-  resultado del test de normalidad (`PruebaN/normalidad.csv`):
  ¿qué % rechaza normalidad? En humo de verificación salió ~65% rechazo,
  lo que respalda usar mediana — reporta tu número real.]
-  variar-M — ¿el tiempo crece lineal con M para las 3? (esperado:
  sí, con pendiente `O(N)` en Lista y `O(log N)` en árboles).]

### Conclusion: 
