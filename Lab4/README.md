## Laboratorio 4

###  Hardware / software de las mediciones

- CPU: AMD Ryzen 7 6800HS (8 núcleos) - RAM: 16 GB - OS: Windows 11
- Python 3.14.3 - matplotlib 3.11.1 - scipy 1.17.1

Resultado esperado:

| Estructura | Archivo | Búsqueda por radio | `k` vecinos más cercanos | Construcción |
|---|---|---|---|---|
| Lista nativa (fuerza bruta) | — (built-in) | Scan `O(N)` | Scan `O(N)` manteniendo los `k` mejores | — |
| Quadtree (2D, capacidad por nodo) | `Quadtreetree.py` | `O(log N + m)` promedio (`m` = puntos devueltos), `O(N)` degenerado | `O(log N + k)` promedio, `O(N)` degenerado | `O(N log N)` |


El Quadtree gana porque **poda regiones enteras**: si la región de un nodo no toca el círculo de búsqueda 
(o está más lejos que el peor candidato actual), no se visita ninguno de sus puntos. El caso crítico sería
un conjunto de puntos casi idénticos, que obliga a profundizar sin dividir el espacio; la profundidad máxima 
evita la recursión infinita, pero esa hoja se recorrería de forma lineal.


### ***Explicación archivos***
 
- ***Quadtreetree.py***: Algoritmos implementados para el QuadTree en 2d, tiene usa las siguientes clases: `Punto`, `Region`, `Nodo` y `QuadTree` .Tambien contiene las funciones sueltas de fuerza bruta que se usan como referencia.
- ***test.py***: pruebas unitarias (árbol contra fuerza bruta, casos borde) y generación de las figuras de verificación visual.
- ***analisis.py***: mediciones de rendimiento, cálculo del punto de cruce y gráficas.
- - ***figuras***: gráficas de verificación visual generadas en test.py. 
- ***graficos_analisis***: gráficas del análisis generado en analisis.py.



## **Código de honor:**
#### Uso de ia: se usaron herramientas de ia para la generación del código de las graficas y pruebas unitarias, el cual fue revisado,comentado y modificado por mi antes de la implemtacion final. 
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


### Estadística

- Cada tiempo es el **tiempo medio por consulta**  y se reporta la **mediana de 5 repeticiones**, junto con el mínimo, el máximo y el rango intercuartílico (columnas del CSV).
- Se usa mediana y no media por robustez frente a valores atípicos . Las gráficas muestran la mediana y una banda mínimo-máximo.

- **Punto de cruce:** primer `N` en que el árbol es más rápido, interpolado en escala log-log. Como cerca del cruce las diferencias caen dentro del ruido, se reporta también el **primer `N` desde el cual la ventaja es inequívoca**: aquel en que el máximo de las 5 repeticiones del árbol es menor que el mínimo de la fuerza bruta, para ese `N` y todos los mayores.


### Hallazgos

**¿Para qué tamaño de datos el Quadtree comienza a ser más rápido que la fuerza bruta?**
 
Con la configuración base (área fija, radio 500 m, capacidad 4, `k = 5`, datos uniformes):
 
| Consulta | Cruce (interpolado) | Ventaja inequívoca desde |
|---|---|---|
| Radio de 500 m | `N ≈ 19` | `N = 100` |
| 5 vecinos más cercanos | `N ≈ 81` | `N = 200` |
 
En densidad fija el cruce del radio sube a `N ≈ 260` (inequívoco desde 500), porque con `N` pequeño el círculo cubre toda la ciudad; en vecinos se mantiene en `N ≈ 85` (inequívoco desde 100). **Es decir, el Quadtree supera a la fuerza bruta a partir de unas decenas de puntos en radio y de un centenar en vecinos.**
 
Tiempo medio por consulta en área fija (µs; `×` = veces que el árbol es más rápido):
 
| N | Radio: árbol | Radio: fuerza bruta | × | Vecinos: árbol | Vecinos: fuerza bruta | × |
|---|---|---|---|---|---|---|
| 10 | 3.3 | 2.3 | 0.7 | 11.0 | 6.1 | 0.5 |
| 100 | 8.3 | 20.9 | 2.5 | 33.2 | 36.0 | 1.1 |
| 1000 | 21.1 | 202.6 | 9.6 | 44.5 | 245.6 | 5.5 |
| 10000 | 118.1 | 2065.5 | 17.5 | 66.9 | 2406.5 | 36.0 |
| 100000 | 917.4 | 20149.2 | 22.0 | 75.0 | 22634.5 | 301.7 |
 
Con los 10000 puntos el árbol es unas 17.5 veces más rápido en radio y unas 36 en vecinos. En densidad fija (mismos datos en N = 10000, otra corrida) salen 22.6 y 42.8 veces; en N = 100000 la ventaja llega a 156.1 veces en radio y 320.8 en vecinos.


**¿Los resultados se comportan como predice la complejidad teórica?**
 
Sí. Al pasar de N = 10000 a N = 100000 (factor x10 en N):
 
| Operación | Esperado | Observado |
|---|---|---|
| Fuerza bruta, radio | `O(N)`: x10 | x9.76 (de N = 100 a 100000: x964 frente a x1000) |
| Fuerza bruta, vecinos | `O(N)`: x10 | x9.41 |
| Quadtree, vecinos | `O(log N + k)`: ≈ x1.25 | x1.12 de tiempo (x1.39 en la otra corrida); nodos visitados 39.7 → 51.6 (x1.3); profundidad media 4.2 → 5.4 |
| Quadtree, radio | `O(log N + m)` | densidad fija (`m` ≈ 67 constante): x1.52 de tiempo y nodos 114.6 → 125.3 (+9 %); área fija (`m` pasa de 67 a 669): x7.77 |
| Construcción | `O(N log N)`: ≈ x12.5 | x14.3 (la construcción de N = 100000 tarda 496 ms) |
 
- En **área fija** el árbol de radio *parece* lineal, pero no contradice la teoría: devuelve 10 veces más puntos y entregar resultados cuesta. Un ajuste sobre los datos da `nodos visitados ≈ 39 + 0.96 · puntos devueltos`: una parte casi constante (la logarítmica) más una proporcional al resultado, que es justo `O(log N + m)`.
- Los **contadores** confirman la teoría con más limpieza que los tiempos: en N = 10000 el árbol visita ≈ 115 nodos y calcula ≈ 93 distancias, contra 10000 de la fuerza bruta.
- **La ventaja real (17.5x) es menor que la algorítmica (≈ 87x menos trabajo)** por las constantes de Python: cada nodo visitado cuesta ≈ 1.03 µs y cada punto de la fuerza bruta ≈ 0.21 µs (estimación: tiempo medio dividido entre unidades de trabajo), unas 5 veces más. Por eso el cruce no está en `N` = 1, sino en decenas o centenas de puntos.


### Conclusión

El Quadtree implementa correctamente la búsqueda por radio y por `k` vecinos más cercanos: coincide con la fuerza bruta en todas las pruebas, incluidos los casos borde. En el escenario del enunciado (10000 puntos en una ciudad de 10 km x 10 km) el árbol es unas 17 a 23 veces más rápido en radio de 500 m y 36 a 43 veces en vecinos, y comienza a ganar con `N ≈ 19` puntos en radio y `N ≈ 81` en vecinos. El comportamiento asintótico medido coincide con el teórico: la fuerza bruta es lineal, la búsqueda de vecinos con el árbol casi no crece con `N` (logarítmica), y la de radio crece con el número de puntos devueltos (`O(log N + m)`).
 
La ventaja real es menor que la que sugiere el conteo de operaciones por la sobrecarga constante de cada nodo en Python (≈ 5 veces más por unidad de trabajo), y se reduce cuando el radio devuelve una fracción grande de los puntos (de 99.5x con 100 m a 2.7x con 2000 m). La capacidad por nodo es el parámetro más influyente: con 16 puntos por hoja las consultas son más rápidas que con 4 (30.5x contra 17.5x en radio) y la construcción cuesta menos. Los datos agrupados en clusters no degradan el rendimiento, aunque el árbol se hace más profundo.
