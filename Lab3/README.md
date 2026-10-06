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

### Hallazgos

**¿Los resultados se comportan como predice la complejidad teórica?**

Sí. En `busqueda_sin_build` con datos **desordenados**, ABB y B+
permanecen casi planos al pasar de N=5000 a N=20000 (factor ×4 en N): ABB pasa de
1.03 ms a 1.19 ms (factor ×1.16) y B+ de 0.73 ms a 0.91 ms (factor ×1.25). El
crecimiento esperado para O(log N) en ese rango es
`log(20000)/log(5000) ≈ 1.16` — coincide casi exactamente con el ABB aleatorio.
En el mismo experimento con datos **ordenados**, el ABB pasa de 340.3 ms a
1696.9 ms (factor ×4.99, pendiente log-log ≈1.16, se aproxima a O(N)), mientras
B+ mantine el mismo resultado (0.77 ms -> 1.0 ms).

**¿En qué situación el árbol binario deja de comportarse como O(log N)?**

El arbol ABB deja de ser logarítmico cuando se construye desde datos ordenados, no importa el N.
cada nodo nuevo es insertado como hijo derecho del anterior, es esencialmente una lista enlazada de tamaño N. 


**¿Qué ocurre cuando los datos se insertan ordenadamente? ¿Qué muestra
`busqueda_con_build`?**

En `busqueda_con_build`
(mide  inserción + búsqueda), el ABB con datos
ordenados pasa de 2016.8 ms en N=5000 a 31858.7 ms en N=20000 - factor de 
×15.8 para un aumento de N de solo ×4. Calculando la pendiente en escala
log-log: `log(15.8) / log(4) = 1.99` - se aproxima a un exponente de **2.0**,
coincidiendo casi exactamente con O(N²). Esto confirma que el costo dominante
no es la búsqueda (O(N) degenerado), sino la
construcción: cada una de las N inserciones baja por una rama de longitud
creciente (1, 2, 3, ..., N), `1+2+...+N = O(N²)`. El B+ en el mismo
experimento se mantiene lineal 2.1 ms → 20.1 ms).

**¿Qué diferencias aparecen entre los casos aleatorio y ordenado?**

Son de orden de magnitud, no solo de pendiente. En N=20000,
`busqueda_sin_build` tarda 1.19 ms (ABB aleatorio) vs 1696.9 ms (ABB ordenado) - ~1400 veces más lento por el solo cambiar el orden de los datos
de entrada.

** Tratamiento de valores atípicos**

Se identificaron repeticiones individuales muy por encima de la mediana en dos
puntos: `rango_10pct, desordenados, Lista nativa, N=20000` (mediana=1.53 ms,
media=2.15 ms, máximo=3.96 ms - una repetición ~2.6× la mediana) y
`rango_10pct, ordenados, Lista nativa, N=8000` (mediana=0.39 ms, máximo=2.71 ms - ~7× la mediana). Ambos casos son consistentes con pausas puntuales del
recolector de basura o del planificador del sistema operativo, no con el
comportamiento real del algoritmo. 


**Variar M con N fijo**

Con N=`N_FIJO_M` fijo y M variando en `[COMPLETAR: rango real usado]`, el
tiempo de búsqueda crece **[COMPLETAR: linealmente / con qué pendiente]** en
la lista nativa, y de forma **[COMPLETAR]** en ABB/B+. *(Pega aquí el factor
`t(M_max)/t(M_min)` que te da tu propio CSV de este experimento — no incluí
estos datos porque no vinieron en el archivo que me compartiste.)*

---

### Conclusión

Las tres estructuras implementan correctamente las tres operaciones
 (búsqueda, inserción, listado ordenado).

 Con datos aleatorios, el ABB
y el B+ se comportan de manera muy similar (ambos
O(log N)), y la diferencia entre ellos es solo una constante multiplicativa
(B+ es ~1.3-1.5× más rápido en promedio). Con datos ordenados, el ABB colapsa:
la búsqueda pasa a O(N) y la construcción completa a O(N²), mientras que el
B+ no se ve afectado, porque su `insertar()` mantiene el árbol
balanceado por construcción (vía `_dividir_hijo`), independientemente del
orden de los datos de entrada.

Si una aplicación no puede
garantizar que los IDs lleguen en orden aleatorio (por ejemplo, un sistema
donde los estudiantes se matriculan y los IDs son secuenciales por
matrícula), un ABB sin balanceo presenta riesgo de degenerarse y fallar catastróficamente
. El árbol B+ paga un costo constante ligeramente mayor en el
caso promedio pero elimina completamente el riesgo de degenerarse a O(n) eliminar por completo ese riesgo.

En cuanto a las operaciones por rango y el listado completo, ambas son
operaciones inherentemente O(N) o cercanas (el costo está dominado por el
tamaño del resultado, no por la estructura), y ahí la ventaja del B+ es de
constante el recorrido secuencial de hojas enlazadas evita la recursión y
el overhead de punteros que paga el ABB, y evita el costo de ordenar que paga
la lista nativa.


