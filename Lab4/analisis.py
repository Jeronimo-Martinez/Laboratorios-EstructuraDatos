"""
Cómo mide:
    - time.perf_counter para los tiempos.
    - El mismo conjunto de consultas para el árbol y para la fuerza bruta en cada N.
    - Muchas consultas por N (cientos) y se reporta el TIEMPO MEDIO por consulta.
    - Varias repeticiones por N y se usa la MEDIANA (se guardan además mínimo,
      máximo e IQR para distinguir una diferencia real del ruido del sistema).
    - La construcción del árbol se mide aparte.
    - Una pasada de calentamiento (que además verifica que ambos métodos
      devuelven lo mismo) antes de medir, y gc apagado durante la medición.

Qué varía:
    - N en escala logarítmica: 10, 20, 50, 100, 200, 500, 1000, 2000, 5000,
      10000, 50000, 100000 (más puntos abajo, donde está el cruce).
    - Dos formas de crecer N:
        * área fija: los N puntos caben siempre en la ciudad de 10000 x 10000 m,
          al subir N sube la densidad y un radio de 500 m captura cada vez más
          puntos (parte del trabajo del árbol es entregar resultados).
        * densidad fija: el área crece con N (lado = 10000 * sqrt(N/10000)) y el
          radio captura una cantidad casi constante de puntos: es la comparación
          más limpia de O(log N) contra O(N).
    - radio, capacidad por nodo, k y distribución: por defecto corre la
      configuración base (radio 500 m, capacidad 4, k 5, uniforme); con
      --radio/--capacidad/--k/--distribucion se cambia la base y con
      --barrido ... se corre el barrido completo de cada parámetro.

Métricas registradas por cada N (además de los tiempos):
    - puntos devueltos por consulta de radio (promedio y fracción de N) y la
      marca `saturado` cuando la consulta devuelve >= 90% de N: ahí el
      experimento no dice nada del árbol y ese N se excluye del cruce.
    - nodos visitados, hojas visitadas y distancias punto-punto calculadas por
      el árbol (versión instrumentada, jamás cronometrada), para separar el
      ahorro algorítmico de la sobrecarga de Python.

El cruce se exige ESTABLE: es el primer N a partir del cual el árbol gana en
todos los N válidos mayores; si las curvas se cruzan más de una vez se avisa.

Datos: ESTÁTICOS. Se generan una sola vez con semillas fijas y se reutilizan en todos los experimentos. Devuelven
TUPLAS, para que una mutación accidental falle enseguida y no corrompa la
caché de lru_cache.

Uso:
    python analisis.py                                  # corrida base completa
    python analisis.py --barrido radio capacidad k distribucion   # + barridos
    python analisis.py --rapido                         # escala corta (10..10000)
    python analisis.py --solo-figuras --barrido ...     # regenera figuras del CSV
    python analisis.py --radio 200 --capacidad 16 --k 20 --distribucion clusters
    python analisis.py --sin-figuras --reps 7 --consultas 300
    python analisis.py --solo densidad_fija

Salidas:
    - tablas, métricas y cruces por modo en consola
    - analisis_resultados.csv (se SOBRESCRIBE en cada corrida)
    - graficos_analisis/*.png: tiempo_radio_<modo>, tiempo_knn_<modo> y
      barridos.png (una sola imagen con todos los barridos pedidos:
      una fila por modo, una columna por parámetro barrido)
"""
import argparse
import csv
import gc
import math
import os
import random
import statistics
import sys
import time
from functools import lru_cache

from QuadTree import (
    Punto,
    Region,
    QuadTree,
    radio_fuerza_bruta,
    vecinos_fuerza_bruta,
)

# ----------------------------------------------------------------------
# Configuración (constantes: los datos y los parámetros no cambian)
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_GRAFICOS = os.path.join(BASE_DIR, "graficos_analisis")
RUTA_CSV = os.path.join(BASE_DIR, "analisis_resultados.csv")

AREA = 10000              # la ciudad es un cuadrado de 10000 x 10000 metros
N_REF = 10000             # 10.000 puntos de entrega en la ciudad (densidad de referencia)
MAX_N = 100000            # máximo N de la escala
SEMILLA_DATOS = 42        # datos uniformes (estáticos)
SEMILLA_CLUSTERS = 43     # datos con clusters (estáticos)
SEMILLA_CONSULTAS = 99    # centros de consulta (estáticos)
N_CLUSTERS = 8
SIGMA_REL = 0.03          # sigma de cada cluster = 3% del lado de la ciudad

NS = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 50000, 100000]
NS_RAPIDO = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
MODOS = ("area_fija", "densidad_fija")

RADIO = 500               # metros
CAPACIDAD = 4             # puntos por nodo hoja
K = 5                     # vecinos más cercanos
CONSULTAS = 200           # consultas por cada N (mismo conjunto para ambos métodos)
REPS = 5                  # repeticiones por N (se usa la mediana)
UMBRAL_SATURACION = 0.9   # fracción de N devuelta a partir de la cual un N se excluye

MARGEN_CONSULTAS = 500.0  # algunos centros caen fuera del área de los datos

# Barridos de parámetros: una curva por valor en la figura correspondiente
VALORES_BARRIDO = {
    "radio": [100, 500, 2000],
    "capacidad": [1, 4, 16, 64],
    "k": [1, 5, 20],
    "distribucion": ["uniforme", "clusters"],
}
PARAM_COLUMNA = {
    "radio": "radio",
    "capacidad": "capacidad",
    "k": "k",
    "distribucion": "distribucion",
}
TODAS_LAS_COLUMNAS = ["radio", "capacidad", "k", "distribucion"]

# Columnas del CSV (orden fijo)
CAMPOS = [
    "modo", "distribucion", "radio", "capacidad", "k", "n", "consultas", "reps",
    "t_construccion_s", "t_construccion_s_min", "t_construccion_s_max",
    "t_arbol_radio_us", "t_arbol_radio_us_min", "t_arbol_radio_us_max",
    "t_arbol_radio_us_iqr",
    "t_fb_radio_us", "t_fb_radio_us_min", "t_fb_radio_us_max", "t_fb_radio_us_iqr",
    "t_arbol_knn_us", "t_arbol_knn_us_min", "t_arbol_knn_us_max",
    "t_arbol_knn_us_iqr",
    "t_fb_knn_us", "t_fb_knn_us_min", "t_fb_knn_us_max", "t_fb_knn_us_iqr",
    "devueltos_prom", "devueltos_fraccion", "saturado",
    "visitas_r_nodos", "visitas_r_hojas", "distancias_r", "prof_r_media",
    "prof_r_max",
    "visitas_k_nodos", "visitas_k_hojas", "distancias_k", "prof_k_media",
    "prof_k_max",
    "distancias_fb",
    "arbol_nodos", "arbol_hojas", "arbol_prof_max", "arbol_nodos_prof_max",
    "arbol_puntos_prof_max",
    "amort_radio", "amort_knn",
]
CAMPO_TEXTO = {"modo", "distribucion"}
CAMPO_BOOL = {"saturado"}
CAMPO_ENTERO = {
    "radio", "capacidad", "k", "n", "consultas", "reps",
    "prof_r_max", "prof_k_max", "distancias_fb",
    "arbol_nodos", "arbol_hojas", "arbol_prof_max", "arbol_nodos_prof_max",
    "arbol_puntos_prof_max",
}

def lado_para_n(n, modo):
    """Lado del cuadrado que ocupan los n puntos según el modo de crecimiento."""
    if modo == "area_fija":
        return float(AREA)
    if modo == "densidad_fija":
        # el área crece con N para mantener la densidad de referencia
        return AREA * math.sqrt(n / N_REF)
    raise ValueError(f"Modo desconocido: {modo!r} (use {MODOS})")


@lru_cache(maxsize=None)
def _dataset_base(distribucion):
    """Dataset base de MAX_N puntos en [0, AREA] x [0, AREA]. Generado una vez."""
    if distribucion == "uniforme":
        rng = random.Random(SEMILLA_DATOS)
        return tuple(
            Punto(rng.uniform(0, AREA), rng.uniform(0, AREA))
            for _ in range(MAX_N)
        )
    if distribucion == "clusters":
        rng = random.Random(SEMILLA_CLUSTERS)
        centros = [(rng.uniform(0, AREA), rng.uniform(0, AREA))
                   for _ in range(N_CLUSTERS)]
        sigma = AREA * SIGMA_REL
        puntos = []
        for _ in range(MAX_N):
            cx, cy = rng.choice(centros)
            x = min(max(rng.gauss(cx, sigma), 0.0), AREA)
            y = min(max(rng.gauss(cy, sigma), 0.0), AREA)
            puntos.append(Punto(x, y))
        return tuple(puntos)
    raise ValueError(f"Distribución desconocida: {distribucion!r}")


@lru_cache(maxsize=None)
def puntos_para_n(n, modo, distribucion="uniforme"):
    """Los n puntos  para el modo dado. Devuelve una TUPLA:
    no se debe mutar, porque lru_cache devuelve siempre el mismo objeto."""
    base = _dataset_base(distribucion)[:n]
    escala = lado_para_n(n, modo) / AREA
    if escala == 1.0:
        return base
    return tuple(Punto(p.x * escala, p.y * escala) for p in base)


@lru_cache(maxsize=None)
def consultas_para_n(n, modo, cantidad=CONSULTAS):
    """Los centros de consulta  para el modo dado.

    Se generan una sola vez con la misma semilla y son idénticos para el
    árbol y para la fuerza bruta. Devuelve una TUPLA (no mutar).
    """
    rng = random.Random(SEMILLA_CONSULTAS)
    base = tuple(
        Punto(rng.uniform(-MARGEN_CONSULTAS, AREA + MARGEN_CONSULTAS),
              rng.uniform(-MARGEN_CONSULTAS, AREA + MARGEN_CONSULTAS))
        for _ in range(cantidad)
    )
    escala = lado_para_n(n, modo) / AREA
    if escala == 1.0:
        return base
    return tuple(Punto(c.x * escala, c.y * escala) for c in base)


def region_para_n(n, modo):
    """Región raíz un poco mayor que los datos, para que nada quede fuera."""
    lado = lado_para_n(n, modo)
    margen = lado / AREA          # 1 m a escala de la ciudad
    return Region(Punto(-margen, -margen), lado + 2 * margen, lado + 2 * margen)


# ----------------------------------------------------------------------
# Construcción y medición
# ----------------------------------------------------------------------
def construir(puntos, capacidad, region):
    arbol = QuadTree(region, capacidad=capacidad)
    for p in puntos:
        assert arbol.insertar(p), f"No se pudo insertar el punto ({p.x}, {p.y})"
    return arbol


def _resumen_tiempos(tiempos):
    """Mediana, mínimo, máximo e IQR de una serie de tiempos."""
    if len(tiempos) >= 2:
        cuartiles = statistics.quantiles(tiempos, n=4)
        iqr = cuartiles[2] - cuartiles[0]
    else:
        iqr = 0.0
    return {
        "med": statistics.median(tiempos),
        "min": min(tiempos),
        "max": max(tiempos),
        "iqr": iqr,
    }


def medir_construccion(puntos, capacidad, region, reps):
    """Mediana/mín/máx del tiempo de construcción; devuelve también el árbol."""
    tiempos = []
    arbol = None
    for _ in range(reps):
        gc.collect()
        gc.disable()
        inicio = time.perf_counter()
        arbol = construir(puntos, capacidad, region)
        fin = time.perf_counter()
        gc.enable()
        tiempos.append(fin - inicio)
    return _resumen_tiempos(tiempos), arbol


def _claves(puntos):
    """Representación comparable (multiconjunto ordenado) de una lista de puntos."""
    return sorted((p.x, p.y) for p in puntos)


def calentar_y_verificar(arbol, puntos, consultas, radio, k):
    """Pasada de calentamiento SIN medir, que además verifica en cada consulta
    que el árbol y la fuerza bruta devuelven lo mismo."""
    for i, c in enumerate(consultas):
        arb_radio = arbol.buscar_radio(c, radio)
        fb_radio = radio_fuerza_bruta(puntos, c, radio)
        if _claves(arb_radio) != _claves(fb_radio):
            raise AssertionError(
                f"Verificación de radio falló en la consulta {i}: "
                f"centro=({c.x:.1f}, {c.y:.1f}), radio={radio}, "
                f"árbol={len(arb_radio)} puntos, fuerza bruta={len(fb_radio)} puntos"
            )

        arb_k = arbol.buscar_mas_cercanos(c, k)
        fb_k = vecinos_fuerza_bruta(puntos, c, k)
        d_arb = [c.distancia_punto(p) for p in arb_k]
        d_fb = [c.distancia_punto(p) for p in fb_k]
        if d_arb != d_fb or d_arb != sorted(d_arb):
            raise AssertionError(
                f"Verificación de vecinos falló en la consulta {i}: "
                f"consulta=({c.x:.1f}, {c.y:.1f}), k={k}\n"
                f"  árbol:        {d_arb}\n  fuerza bruta: {d_fb}"
            )


def medir_par(func_arbol, func_fb, consultas, reps):
    """Tiempo MEDIO por consulta (µs) de cada método: dict con mediana, mínimo,
    máximo e IQR de las `reps` corridas.

    El orden árbol/fuerza bruta se alterna entre repeticiones para que el
    sesgo de caché no favorezca siempre al mismo.
    """
    tiempos = {"arbol": [], "fb": []}
    for rep in range(reps):
        orden = [("arbol", func_arbol), ("fb", func_fb)]
        if rep % 2 == 1:
            orden.reverse()
        for nombre, f in orden:
            gc.collect()
            gc.disable()
            inicio = time.perf_counter()
            for c in consultas:
                f(c)
            fin = time.perf_counter()
            gc.enable()
            tiempos[nombre].append((fin - inicio) / len(consultas) * 1e6)  # µs
    return _resumen_tiempos(tiempos["arbol"]), _resumen_tiempos(tiempos["fb"])


# ----------------------------------------------------------------------
# Instrumentación: nodos visitados, distancias calculadas, estructura
# ----------------------------------------------------------------------
class ContadorConsultas:
    """Versión instrumentada de las consultas del Quadtree.

    Cuenta nodos visitados (entradas a un nodo, que es donde se calcula la
    distancia a la región), hojas visitadas, distancias punto-punto calculadas
    y la profundidad recorrida.

    Se usa SOLO para estadísticas y nunca se cronometra: la medición de
    tiempos usa los métodos originales de QuadTree, para que el contador no
    contamine los tiempos. Devuelve exactamente los mismos resultados que el
    árbol original (se verifica en metricas_consulta).
    """

    def __init__(self, arbol):
        self.arbol = arbol

    def _reset(self):
        self.nodos_visitados = 0
        self.hojas_visitadas = 0
        self.distancias = 0          # distancias punto-punto calculadas
        self.prof_suma = 0
        self.prof_max = 0

    def buscar_radio(self, centro, radio):
        self._reset()
        resultados = []
        self._buscar_radio(self.arbol.raiz, centro, radio ** 2, resultados, 0)
        return resultados

    def _buscar_radio(self, nodo, centro, radio_cuadrado, resultados, prof):
        self.nodos_visitados += 1
        self.prof_suma += prof
        if prof > self.prof_max:
            self.prof_max = prof
        if nodo.region.distancia_min(centro) > radio_cuadrado:
            return
        if nodo.es_hoja():
            self.hojas_visitadas += 1
            for p in nodo.puntos:
                self.distancias += 1
                if centro.distancia_punto(p) <= radio_cuadrado:
                    resultados.append(p)
        else:
            for hijo in nodo.hijos:
                self._buscar_radio(hijo, centro, radio_cuadrado, resultados, prof + 1)

    def buscar_mas_cercanos(self, punto, k=1):
        if k <= 0:
            return []
        self._reset()
        candidatos = []
        self._buscar_mas_cercanos(self.arbol.raiz, punto, k, candidatos, 0)
        return [p for d, p in candidatos]

    def _buscar_mas_cercanos(self, nodo, punto, k, candidatos, prof):
        self.nodos_visitados += 1
        self.prof_suma += prof
        if prof > self.prof_max:
            self.prof_max = prof
        limite = candidatos[-1][0] if len(candidatos) == k else float("inf")
        if nodo.region.distancia_min(punto) > limite:
            return
        if nodo.es_hoja():
            self.hojas_visitadas += 1
            for p in nodo.puntos:
                self.distancias += 1
                d = punto.distancia_punto(p)
                if len(candidatos) < k or d < candidatos[-1][0]:
                    candidatos.append((d, p))
                    candidatos.sort(key=lambda c: c[0])
                    if len(candidatos) > k:
                        candidatos.pop()
        else:
            hijos = sorted(nodo.hijos, key=lambda h: h.region.distancia_min(punto))
            for hijo in hijos:
                self._buscar_mas_cercanos(hijo, punto, k, candidatos, prof + 1)


def estadisticas_arbol(raiz):
    """Estructura del árbol: nodos, hojas, profundidad máxima alcanzada y
    cuántos nodos/puntos quedaron en esa profundidad máxima (con clusters ahí
    se acumulan los puntos repetidos recortados al borde del área)."""
    nodos = hojas = 0
    prof_max = nodos_prof_max = puntos_prof_max = 0
    pila = [(raiz, 0)]
    while pila:
        nodo, prof = pila.pop()
        nodos += 1
        if prof > prof_max:
            prof_max = prof
            nodos_prof_max = 1
            puntos_prof_max = len(nodo.puntos) if nodo.es_hoja() else 0
        elif prof == prof_max:
            nodos_prof_max += 1
            if nodo.es_hoja():
                puntos_prof_max += len(nodo.puntos)
        if nodo.es_hoja():
            hojas += 1
        else:
            for hijo in nodo.hijos:
                pila.append((hijo, prof + 1))
    return {
        "arbol_nodos": nodos,
        "arbol_hojas": hojas,
        "arbol_prof_max": prof_max,
        "arbol_nodos_prof_max": nodos_prof_max,
        "arbol_puntos_prof_max": puntos_prof_max,
    }


def metricas_consulta(arbol, consultas, radio, k, n):
    """Promedios por consulta del trabajo real: puntos devueltos, nodos
    visitados, hojas visitadas, distancias calculadas y profundidad.

    Verifica que la versión instrumentada devuelva lo mismo que el árbol
    original en cada consulta. Los contadores se reinician en cada consulta,
    así que se acumulan aquí los totales antes de promediar.
    """
    contador_r = ContadorConsultas(arbol)
    contador_k = ContadorConsultas(arbol)
    tot = {
        "devueltos": 0,
        "r_nodos": 0, "r_hojas": 0, "r_dist": 0, "r_prof_suma": 0, "r_prof_max": 0,
        "k_nodos": 0, "k_hojas": 0, "k_dist": 0, "k_prof_suma": 0, "k_prof_max": 0,
    }
    for i, c in enumerate(consultas):
        contado = contador_r.buscar_radio(c, radio)
        original = arbol.buscar_radio(c, radio)
        if _claves(contado) != _claves(original):
            raise AssertionError(
                f"El contador de radio difiere del árbol original en la consulta {i}")
        tot["devueltos"] += len(contado)
        tot["r_nodos"] += contador_r.nodos_visitados
        tot["r_hojas"] += contador_r.hojas_visitadas
        tot["r_dist"] += contador_r.distancias
        tot["r_prof_suma"] += contador_r.prof_suma
        tot["r_prof_max"] = max(tot["r_prof_max"], contador_r.prof_max)

        contado_k = contador_k.buscar_mas_cercanos(c, k)
        original_k = arbol.buscar_mas_cercanos(c, k)
        if [c.distancia_punto(p) for p in contado_k] != \
           [c.distancia_punto(p) for p in original_k]:
            raise AssertionError(
                f"El contador de vecinos difiere del árbol original en la consulta {i}")
        tot["k_nodos"] += contador_k.nodos_visitados
        tot["k_hojas"] += contador_k.hojas_visitadas
        tot["k_dist"] += contador_k.distancias
        tot["k_prof_suma"] += contador_k.prof_suma
        tot["k_prof_max"] = max(tot["k_prof_max"], contador_k.prof_max)

    nh = len(consultas)
    devueltos_prom = tot["devueltos"] / nh
    return {
        "devueltos_prom": devueltos_prom,
        "devueltos_fraccion": devueltos_prom / n,
        "visitas_r_nodos": tot["r_nodos"] / nh,
        "visitas_r_hojas": tot["r_hojas"] / nh,
        "distancias_r": tot["r_dist"] / nh,
        "prof_r_media": (tot["r_prof_suma"] / tot["r_nodos"]
                         if tot["r_nodos"] else 0.0),
        "prof_r_max": tot["r_prof_max"],
        "visitas_k_nodos": tot["k_nodos"] / nh,
        "visitas_k_hojas": tot["k_hojas"] / nh,
        "distancias_k": tot["k_dist"] / nh,
        "prof_k_media": (tot["k_prof_suma"] / tot["k_nodos"]
                         if tot["k_nodos"] else 0.0),
        "prof_k_max": tot["k_prof_max"],
        # la fuerza bruta calcula exactamente N distancias por consulta
        "distancias_fb": n,
    }


# ----------------------------------------------------------------------
# Cruce y amortización
# ----------------------------------------------------------------------
def _interpol_cruce(n0, n1, ta0, tf0, ta1, tf1):
    """Interpolación lineal en log-log del punto donde t_árbol = t_fuerza bruta."""
    y0 = math.log10(ta0) - math.log10(tf0)
    y1 = math.log10(ta1) - math.log10(tf1)
    if y0 == y1:
        return float(n1)
    fraccion = y0 / (y0 - y1)
    x0, x1 = math.log10(n0), math.log10(n1)
    return 10 ** (x0 + fraccion * (x1 - x0))


def encontrar_cruce(ns, t_arbol, t_fb, validos=None):
    """Cruce ESTABLE: el primer N a partir del cual el árbol gana en TODOS los
    N válidos mayores (se evalúa desde el final, de modo que un N donde el
    árbol gana por ruido, para después volver a perder, no cuente como cruce).

    Devuelve (cruce, cambios):
      - cruce: N interpolado en log-log, o None si el árbol no termina ganando;
      - cambios: todos los cruces interpolados, para avisar si las curvas se
        cruzan y vuelven a cruzarse.
    """
    if validos is None:
        validos = [True] * len(ns)
    idx = [i for i in range(len(ns)) if validos[i]]
    if len(idx) < 2:
        return None, []
    gana = [t_arbol[i] < t_fb[i] for i in idx]

    cambios = []
    for j in range(1, len(idx)):
        a, b = idx[j - 1], idx[j]
        if gana[j] != gana[j - 1]:
            cambios.append(_interpol_cruce(ns[a], ns[b],
                                           t_arbol[a], t_fb[a],
                                           t_arbol[b], t_fb[b]))
    if not gana[-1]:
        # en el N más grande medido el árbol todavía no gana
        return None, cambios
    if not cambios:
        # gana desde el primer N válido de la escala
        return float(ns[idx[0]]), cambios
    # el último cambio es la entrada a la racha final de victorias del árbol
    return cambios[-1], cambios


def consultas_para_amortizar(t_construccion_s, t_arbol_us, t_fb_us):
    """Consultas que hacen falta para amortizar la construcción del árbol."""
    ahorro_us = t_fb_us - t_arbol_us
    if ahorro_us <= 0:
        return None
    return (t_construccion_s * 1e6) / ahorro_us


def formato_cruce(cruce):
    if cruce is None:
        return "el árbol nunca gana en esta escala"
    if cruce < 1000:
        return f"N* ≈ {cruce:.0f}"
    return f"N* ≈ {cruce:,.0f}".replace(",", ".")


def formato_num(x, decimales=0):
    return f"{x:,.{decimales}f}".replace(",", ".")


# ----------------------------------------------------------------------
# Experimento principal
# ----------------------------------------------------------------------
def experimento(modo, distribucion="uniforme", radio=RADIO, capacidad=CAPACIDAD,
                k=K, ns=None, n_consultas=CONSULTAS, reps=REPS, verbose=True):
    """Corre la escala de N para un modo de crecimiento y devuelve las filas."""
    if ns is None:
        ns = NS
    filas = []
    if verbose:
        print(f"\n=== Modo: {modo} · distribución: {distribucion} · radio: {radio} m · "
              f"capacidad: {capacidad} · k: {k} ===")
        print(f"{'N':>7} | {'constr (ms)':>11} | {'árbol r (µs)':>12} | {'FB r (µs)':>10} "
              f"| {'razón r':>8} | {'árbol k (µs)':>12} | {'FB k (µs)':>10} "
              f"| {'razón k':>8} | est.")
        print("-" * 116)

    for n in ns:
        puntos = puntos_para_n(n, modo, distribucion)
        consultas = consultas_para_n(n, modo, n_consultas)
        region = region_para_n(n, modo)

        # construcción medida aparte (mediana de reps); el último árbol queda listo
        t_constr, arbol = medir_construccion(puntos, capacidad, region, reps)

        # calentamiento + verificación de igualdad antes de cronometrar
        calentar_y_verificar(arbol, puntos, consultas, radio, k)

        arb_r, fb_r = medir_par(
            lambda c: arbol.buscar_radio(c, radio),
            lambda c: radio_fuerza_bruta(puntos, c, radio),
            consultas, reps,
        )
        arb_k, fb_k = medir_par(
            lambda c: arbol.buscar_mas_cercanos(c, k),
            lambda c: vecinos_fuerza_bruta(puntos, c, k),
            consultas, reps,
        )

        # métricas de trabajo real (sin cronometrar) y estructura del árbol
        met = metricas_consulta(arbol, consultas, radio, k, n)
        estructura = estadisticas_arbol(arbol.raiz)
        saturado = met["devueltos_fraccion"] >= UMBRAL_SATURACION

        amort_r = consultas_para_amortizar(t_constr["med"], arb_r["med"], fb_r["med"])
        amort_k = consultas_para_amortizar(t_constr["med"], arb_k["med"], fb_k["med"])

        fila = {
            "modo": modo,
            "distribucion": distribucion,
            "radio": radio,
            "capacidad": capacidad,
            "k": k,
            "n": n,
            "consultas": n_consultas,
            "reps": reps,
            "t_construccion_s": t_constr["med"],
            "t_construccion_s_min": t_constr["min"],
            "t_construccion_s_max": t_constr["max"],
            "t_arbol_radio_us": arb_r["med"],
            "t_arbol_radio_us_min": arb_r["min"],
            "t_arbol_radio_us_max": arb_r["max"],
            "t_arbol_radio_us_iqr": arb_r["iqr"],
            "t_fb_radio_us": fb_r["med"],
            "t_fb_radio_us_min": fb_r["min"],
            "t_fb_radio_us_max": fb_r["max"],
            "t_fb_radio_us_iqr": fb_r["iqr"],
            "t_arbol_knn_us": arb_k["med"],
            "t_arbol_knn_us_min": arb_k["min"],
            "t_arbol_knn_us_max": arb_k["max"],
            "t_arbol_knn_us_iqr": arb_k["iqr"],
            "t_fb_knn_us": fb_k["med"],
            "t_fb_knn_us_min": fb_k["min"],
            "t_fb_knn_us_max": fb_k["max"],
            "t_fb_knn_us_iqr": fb_k["iqr"],
            "devueltos_prom": met["devueltos_prom"],
            "devueltos_fraccion": met["devueltos_fraccion"],
            "saturado": saturado,
            "visitas_r_nodos": met["visitas_r_nodos"],
            "visitas_r_hojas": met["visitas_r_hojas"],
            "distancias_r": met["distancias_r"],
            "prof_r_media": met["prof_r_media"],
            "prof_r_max": met["prof_r_max"],
            "visitas_k_nodos": met["visitas_k_nodos"],
            "visitas_k_hojas": met["visitas_k_hojas"],
            "distancias_k": met["distancias_k"],
            "prof_k_media": met["prof_k_media"],
            "prof_k_max": met["prof_k_max"],
            "distancias_fb": met["distancias_fb"],
            "amort_radio": amort_r,
            "amort_knn": amort_k,
        }
        fila.update(estructura)
        filas.append(fila)

        if verbose:
            estado = "SAT" if saturado else "OK"
            print(f"{n:>7} | {t_constr['med'] * 1e3:>11.2f} | {arb_r['med']:>12.2f} "
                  f"| {fb_r['med']:>10.2f} | {fb_r['med'] / arb_r['med']:>8.2f} "
                  f"| {arb_k['med']:>12.2f} | {fb_k['med']:>10.2f} "
                  f"| {fb_k['med'] / arb_k['med']:>8.2f} | {estado}")
    if verbose:
        _print_tabla_metricas(filas)
    return filas


def _print_tabla_metricas(filas):
    """Segunda tabla: el trabajo real por consulta y la estructura del árbol."""
    print("  Trabajo por consulta y estructura del árbol (mismo orden de N):")
    print(f"  {'N':>7} | {'devueltos':>10} | {'% de N':>7} | {'nodos vis. r':>12} "
          f"| {'dist. r':>9} | {'nodos vis. k':>12} | {'dist. k':>9} "
          f"| {'nodos árbol':>11} | {'prof. máx':>9} | {'nodos prof. máx':>15}")
    print("  " + "-" * 122)
    for f in filas:
        print(f"  {f['n']:>7} | {f['devueltos_prom']:>10.1f} "
              f"| {f['devueltos_fraccion'] * 100:>6.1f}% "
              f"| {f['visitas_r_nodos']:>12.1f} | {f['distancias_r']:>9.1f} "
              f"| {f['visitas_k_nodos']:>12.1f} | {f['distancias_k']:>9.1f} "
              f"| {f['arbol_nodos']:>11} | {f['arbol_prof_max']:>9} "
              f"| {f['arbol_nodos_prof_max']:>15}")
    print()


def _aviso_cruces(etiqueta, cruce, cambios):
    if cruce is None and cambios:
        print(f"  AVISO ({etiqueta}): las curvas se cruzan {len(cambios)} veces pero el "
              f"árbol NO termina ganando en la escala medida; no se reporta cruce.")
    elif len(cambios) > 1:
        lista = ", ".join(f"{c:.0f}" for c in cambios)
        print(f"  AVISO ({etiqueta}): las curvas se cruzan {len(cambios)} veces "
              f"(en {lista}). Se reporta el último, es decir el punto a partir del "
              f"cuál el árbol gana y no vuelve a perder.")


def _objetivos_amortizacion(filas):
    ns = sorted({f["n"] for f in filas})
    if not ns:
        return []
    objetivos = [min(ns, key=lambda x: abs(x - N_REF))]
    if max(ns) not in objetivos:
        objetivos.append(max(ns))
    return objetivos


def _reportar_amortizacion(filas):
    for objetivo in _objetivos_amortizacion(filas):
        fila = next(f for f in filas if f["n"] == objetivo)
        etiqueta = ("N = 10000 (el caso del enunciado)"
                    if objetivo == N_REF else f"N = {objetivo} (el más grande medido)")
        print(f"  Amortización en {etiqueta}:")
        for tipo, campo_am in (("radio", "amort_radio"), ("kNN", "amort_knn")):
            amort = fila[campo_am]
            if amort is None:
                print(f"    {tipo:>5}: el árbol no gana en este N, no hay ahorro que amortizar")
                continue
            print(f"    {tipo:>5}: {formato_num(amort)} consultas "
                  f"(construcción {fila['t_construccion_s'] * 1e3:.1f} ms, ahorro "
                  f"{fila['t_fb_' + ('radio' if tipo == 'radio' else 'knn') + '_us'] - fila['t_arbol_' + ('radio' if tipo == 'radio' else 'knn') + '_us']:.1f} µs/consulta)")


def resumen(filas, modo, detallado=True):
    """Cruces estables (radio y kNN), avisos de re-cruces y amortización."""
    ns = [f["n"] for f in filas]
    validos_r = [not f["saturado"] for f in filas]
    n_sat = sum(1 for v in validos_r if not v)

    cruce_r, cambios_r = encontrar_cruce(
        ns, [f["t_arbol_radio_us"] for f in filas],
        [f["t_fb_radio_us"] for f in filas], validos_r)
    cruce_k, cambios_k = encontrar_cruce(
        ns, [f["t_arbol_knn_us"] for f in filas],
        [f["t_fb_knn_us"] for f in filas])

    print(f"\n--- Cruces ({modo}) ---")
    sat_txt = (f"  [excluidos del cruce: {n_sat} N saturados, la consulta devuelve ≥ "
               f"{int(UMBRAL_SATURACION * 100)}% de N]" if n_sat else "")
    print(f"  Radio {filas[0]['radio']} m, solo consulta: "
          f"{formato_cruce(cruce_r)}{sat_txt}")
    print(f"  Vecinos k={filas[0]['k']}, solo consulta: {formato_cruce(cruce_k)}")
    _aviso_cruces("radio", cruce_r, cambios_r)
    _aviso_cruces("kNN", cruce_k, cambios_k)

    if detallado:
        _reportar_amortizacion(filas)
        print("  Amortización por N (consultas necesarias para amortizar la construcción):")
        for f in filas:
            r = "—" if f["amort_radio"] is None else formato_num(f["amort_radio"])
            kk = "—" if f["amort_knn"] is None else formato_num(f["amort_knn"])
            print(f"    N={f['n']:>6}: radio {r:>10} · kNN {kk:>10}")

    return {"radio": cruce_r, "knn": cruce_k,
            "cambios_radio": cambios_r, "cambios_knn": cambios_k,
            "saturados": n_sat}


# ----------------------------------------------------------------------
# CSV (se SOBRESCRIBE en cada corrida) y lectura para rehacer figuras
# ----------------------------------------------------------------------
def escribir_csv(filas, ruta=RUTA_CSV):
    """Escribe todas las filas de la corrida, sobrescribiendo el archivo."""
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS, extrasaction="ignore")
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
    return ruta


def leer_csv(ruta=RUTA_CSV):
    """Lee el CSV y devuelve las filas con los tipos correctos ({} si no existe)."""
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8") as archivo:
        crudo = list(csv.DictReader(archivo))
    filas = []
    for original in crudo:
        fila = {}
        for campo in CAMPOS:
            valor = original.get(campo, "")
            if valor == "":
                fila[campo] = None
            elif campo in CAMPO_TEXTO:
                fila[campo] = valor
            elif campo in CAMPO_BOOL:
                fila[campo] = valor == "True"
            elif campo in CAMPO_ENTERO:
                fila[campo] = int(float(valor))
            else:
                fila[campo] = float(valor)
        filas.append(fila)
    return filas

def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")                      # sin ventana: solo guarda archivos
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("matplotlib no está instalado: se omiten las figuras (pip install matplotlib).")
        return None


def _params_fijos(fila, omitir=None):
    """Lista con los parámetros de la configuración base (sin repetir el
    parámetro que se barre en una figura de barrido)."""
    partes = []
    if omitir != "radio":
        partes.append(f"radio {fila['radio']:g} m")
    if omitir != "capacidad":
        partes.append(f"capacidad {fila['capacidad']}")
    if omitir != "k":
        partes.append(f"k = {fila['k']}")
    if omitir != "distribucion":
        partes.append(f"datos {fila['distribucion']}")
    return partes


def _titulo_base(fila, omitir=None):
    """Subtítulo fijo de las figuras: parámetros de la configuración base
    (sin repetir el parámetro que se barre) más el tamaño de la muestra."""
    partes = _params_fijos(fila, omitir)
    partes.append(f"mediana de {fila['reps']} corridas")
    partes.append(f"{fila['consultas']} consultas por N")
    return " · ".join(partes)


def _guardar(fig, plt, carpeta, nombre):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    fig.savefig(ruta, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return ruta


def figura_tiempo(filas, modo, tipo, carpeta=CARPETA_GRAFICOS):
    """Tiempo medio por consulta vs N (log-log), con banda de mín/máx y cruce."""
    plt = _plt()
    if plt is None:
        return None
    sufijo = "radio" if tipo == "radio" else "knn"
    ns = [f["n"] for f in filas]

    def serie(prefijo):
        return [f[f"{prefijo}_{sufijo}_us"] for f in filas]

    arb, fb = serie("t_arbol"), serie("t_fb")
    validos = [not f["saturado"] for f in filas] if tipo == "radio" else None
    cruce, cambios = encontrar_cruce(ns, arb, fb, validos)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(ns, arb, "o-", label="Quadtree")
    ax.fill_between(ns, [f[f"t_arbol_{sufijo}_us_min"] for f in filas],
                    [f[f"t_arbol_{sufijo}_us_max"] for f in filas],
                    alpha=0.18)
    ax.loglog(ns, fb, "s-", label="Fuerza bruta")
    ax.fill_between(ns, [f[f"t_fb_{sufijo}_us_min"] for f in filas],
                    [f[f"t_fb_{sufijo}_us_max"] for f in filas],
                    alpha=0.18)

    if cruce is not None:
        ax.axvline(cruce, color="tab:red", ls="--", lw=1.2,
                   label=f"cruce: {formato_cruce(cruce)}")
    if len(cambios) > 1:
        ax.annotate(f"re-cruces: {len(cambios)} (se reporta el último)",
                    xy=(0.02, 0.02), xycoords="axes fraction", fontsize=8,
                    color="tab:red")

    modo_legible = modo.replace("_", " ")
    if tipo == "radio":
        etiqueta_tipo = f"consulta de radio ({filas[0]['radio']:g} m)"
        subtitulo = _titulo_base(filas[0], omitir="radio")
    else:
        etiqueta_tipo = f"vecinos más cercanos (k={filas[0]['k']})"
        subtitulo = _titulo_base(filas[0])
    ax.set_xlabel("N (puntos)")
    ax.set_ylabel("tiempo medio por consulta (µs)")
    ax.set_title(f"{etiqueta_tipo} — Quadtree vs fuerza bruta — modo {modo_legible}\n"
                 f"{subtitulo} · banda = mín..máx de las repeticiones")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return _guardar(fig, plt, carpeta, f"tiempo_{sufijo}_{modo}.png")


def filas_barrido(filas, param, valor, modo, cfg):
    """Filas de un valor de un barrido: varía SOLO ese parámetro."""
    columna = PARAM_COLUMNA[param]
    salida = []
    for f in filas:
        if f["modo"] != modo or f[columna] != valor:
            continue
        if any(f[c] != cfg[c] for c in TODAS_LAS_COLUMNAS if c != columna):
            continue
        salida.append(f)
    salida.sort(key=lambda f: f["n"])
    return salida


def figura_barridos(filas, cfg, params_barrido, modos, carpeta=CARPETA_GRAFICOS):
    """Una sola imagen con TODOS los barridos pedidos: una fila por modo de
    crecimiento y una columna por parámetro barrido. Cada celda es la razón
    de tiempos (fuerza bruta ÷ Quadtree) contra N, con una curva por valor
    del parámetro y el resto de parámetros fijos en la configuración base."""
    plt = _plt()
    if plt is None:
        return None
    params = [p for p in VALORES_BARRIDO if p in params_barrido]
    if not params or not modos:
        return None
    n_filas, n_cols = len(modos), len(params)
    # fila de la config base (cfg): sirve para el rótulo general
    muestra = next((f for f in filas
                    if all(f[c] == cfg[c] for c in TODAS_LAS_COLUMNAS)), filas[0])
    fig, ejes = plt.subplots(n_filas, n_cols,
                             figsize=(4.9 * n_cols, 4.3 * n_filas),
                             squeeze=False, sharey=True)
    for i, modo in enumerate(modos):
        for j, param in enumerate(params):
            ax = ejes[i][j]
            es_knn = param == "k"
            valores = [v for v in VALORES_BARRIDO[param]
                       if filas_barrido(filas, param, v, modo, cfg)]
            for valor in valores:
                sub = filas_barrido(filas, param, valor, modo, cfg)
                if es_knn:
                    y = [f["t_fb_knn_us"] / f["t_arbol_knn_us"] for f in sub]
                else:
                    y = [f["t_fb_radio_us"] / f["t_arbol_radio_us"] for f in sub]
                if param == "radio":
                    leyenda = f"radio {valor:g} m"
                elif param == "distribucion":
                    leyenda = f"datos {valor}"
                else:
                    leyenda = f"{param} = {valor}"
                ax.loglog([f["n"] for f in sub], y, "o-", label=leyenda,
                          markersize=4)
            if not valores:
                ax.text(0.5, 0.5, "sin datos en el CSV", ha="center",
                        va="center", transform=ax.transAxes, fontsize=9,
                        color="gray")
            ax.axhline(1.0, color="gray", ls=":", lw=1.0)
            efecto = {"radio": "efecto del radio",
                      "capacidad": "efecto de la capacidad",
                      "k": "efecto de k",
                      "distribucion": "efecto de la distribución"}[param]
            if es_knn:
                consulta = "consulta kNN (k variable)"
            elif param == "radio":
                consulta = "consulta de radio (cada curva, un radio)"
            else:
                consulta = f"consulta radio {cfg['radio']:g} m"
            # título corto: el parámetro que varía y SOLO los fijos (la
            # muestra —repeticiones y consultas— se explica en el rótulo
            # general, que es común a todas las celdas)
            ax.set_title(f"{efecto} — {consulta}\n"
                         f"{' · '.join(_params_fijos(muestra, omitir=param))}",
                         fontsize=9)
            ax.grid(True, which="both", ls=":", alpha=0.5)
            ax.legend(loc="best", fontsize=7)
            if j == 0:
                # el modo de la fila viaja DENTRO de la etiqueta del eje Y:
                # así no choca con el rótulo y no se corta al recortar
                ax.set_ylabel(f"modo {modo.replace('_', ' ')}\n"
                              f"fuerza bruta ÷ Quadtree\n"
                              f"(× = veces más rápido el árbol)")
            if i == n_filas - 1:
                ax.set_xlabel("N (puntos)")
    fig.suptitle(
        "Barridos de parámetros — Quadtree vs fuerza bruta (una fila por modo)\n"
        f"razón > 1 → el árbol es más rápido · 1× (punteado) = empate · "
        f"{_titulo_base(muestra)}",
        fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _guardar(fig, plt, carpeta, "barridos.png")


def generar_figuras(filas, cfg, params_barrido=()):
    """Genera todas las figuras a partir de las filas (las del CSV leído)."""
    if not filas:
        print("No hay filas en el CSV: no hay figuras que generar.")
        return []
    rutas = []
    modos = [m for m in MODOS if any(f["modo"] == m for f in filas)]
    if not modos:
        modos = sorted({f["modo"] for f in filas})

    for modo in modos:
        base = [f for f in filas
                if f["modo"] == modo
                and f["radio"] == cfg["radio"]
                and f["capacidad"] == cfg["capacidad"]
                and f["k"] == cfg["k"]
                and f["distribucion"] == cfg["distribucion"]]
        base.sort(key=lambda f: f["n"])
        if not base:
            print(f"  (sin filas de la configuración base para {modo}: se omiten "
                  f"sus figuras; revise --radio/--capacidad/--k/--distribucion)")
            continue
        for tipo in ("radio", "knn"):
            ruta = figura_tiempo(base, modo, tipo)
            if ruta:
                rutas.append(ruta)

    if params_barrido:
        ruta = figura_barridos(filas, cfg, params_barrido, modos)
        if ruta:
            rutas.append(ruta)
    return rutas


# ----------------------------------------------------------------------
# Principal
# ----------------------------------------------------------------------
def _parsear_args():
    parser = argparse.ArgumentParser(
        description="Análisis de rendimiento: Quadtree vs fuerza bruta.")
    parser.add_argument("--rapido", action="store_true",
                        help="escala de N corta y menos consultas/repeticiones")
    parser.add_argument("--sin-figuras", action="store_true",
                        help="no genera las gráficas")
    parser.add_argument("--solo-figuras", action="store_true",
                        help="no mide: regenera las figuras leyendo el CSV")
    parser.add_argument("--reps", type=int, default=REPS,
                        help=f"repeticiones por N (default {REPS})")
    parser.add_argument("--consultas", type=int, default=CONSULTAS,
                        help=f"consultas por N (default {CONSULTAS})")
    parser.add_argument("--radio", type=float, default=RADIO,
                        help=f"radio de búsqueda en metros (default {RADIO})")
    parser.add_argument("--capacidad", type=int, default=CAPACIDAD,
                        help=f"puntos por nodo hoja (default {CAPACIDAD})")
    parser.add_argument("--k", type=int, default=K,
                        help=f"vecinos más cercanos (default {K})")
    parser.add_argument("--distribucion", choices=("uniforme", "clusters"),
                        default="uniforme", help="distribución de los datos")
    parser.add_argument("--barrido", nargs="+",
                        choices=tuple(VALORES_BARRIDO), metavar="PARAM",
                        help=("barridos a correr (además de la corrida base): "
                              + ", ".join(VALORES_BARRIDO)))
    parser.add_argument("--solo", choices=MODOS,
                        help="corre solo un modo de crecimiento de N")
    return parser.parse_args()


def main():
    # la consola de Windows puede ser cp1252 y no tiene todos los símbolos (≈, →)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = _parsear_args()
    cfg = {"radio": args.radio, "capacidad": args.capacidad, "k": args.k,
           "distribucion": args.distribucion}
    params_barrido = tuple(args.barrido or ())
    modos = (args.solo,) if args.solo else MODOS

    # --- solo regenerar figuras desde el CSV ---------------------------------
    if args.solo_figuras:
        filas = leer_csv()
        if not filas:
            print(f"No existe {RUTA_CSV}: no hay medidas que graficar.")
            return 1
        print(f"Leyendo {len(filas)} filas de {RUTA_CSV} para regenerar las figuras "
              f"(sin repetir mediciones).")
        rutas = generar_figuras(filas, cfg, params_barrido)
        for ruta in rutas:
            print(f"  guardada: {ruta}")
        return 0

    # --- corrida de medición --------------------------------------------------
    ns = NS_RAPIDO if args.rapido else NS
    reps = 3 if args.rapido else args.reps
    n_consultas = 50 if args.rapido else args.consultas
    if args.rapido and params_barrido:
        print("Aviso: --rapido omite los barridos (--barrido) para mantener la corrida corta.")
        params_barrido = ()

    print("Análisis de rendimiento: Quadtree vs fuerza bruta")
    print(f"Datos ESTÁTICOS: {MAX_N} puntos base, semillas fijas "
          f"({SEMILLA_DATOS} uniforme / {SEMILLA_CLUSTERS} clusters / "
          f"{SEMILLA_CONSULTAS} consultas).")
    print(f"Ciudad de {AREA} x {AREA} m · NRef = {N_REF} puntos · escala de N: "
          f"{', '.join(str(n) for n in ns)}")
    print(f"Medición: mediana de {reps} corridas (con mín/máx/IQR), {n_consultas} "
          f"consultas por N, calentamiento + verificación antes de medir, gc apagado.")
    print("\nModos de crecimiento de N:")
    print("  - área fija: los N puntos siempre en la ciudad; sube la densidad y un")
    print("    radio de 500 m captura cada vez más puntos (la ventaja del árbol baja).")
    print("  - densidad fija: el área crece con N y el radio captura una cantidad")
    print("    casi constante de puntos: la comparación más limpia de O(log N) vs O(N).")

    todas = []
    cruces = {}
    for modo in modos:
        filas = experimento(modo, distribucion=cfg["distribucion"],
                            radio=cfg["radio"], capacidad=cfg["capacidad"],
                            k=cfg["k"], ns=ns, n_consultas=n_consultas, reps=reps)
        todas.extend(filas)
        cruces[modo] = resumen(filas, modo)

    # CSV y figuras de la corrida base (parciales si luego vienen los barridos)
    ruta_csv = escribir_csv(todas)
    if not args.sin_figuras:
        for ruta in generar_figuras(leer_csv(ruta_csv), cfg, params_barrido):
            print(f"  guardada: {ruta}")

    # --- barridos de parámetros ----------------------------------------------
    for param in params_barrido:
        columna = PARAM_COLUMNA[param]
        print(f"\n########## Barrido de {param} "
              f"({', '.join(str(v) for v in VALORES_BARRIDO[param])}) ##########")
        for valor in VALORES_BARRIDO[param]:
            if valor == cfg[columna]:
                print(f"  {param} = {valor}: ya medido en la corrida base, se reutiliza.")
                continue
            for modo in modos:
                print(f"  {param} = {valor} · {modo} ...")
                kwargs = dict(cfg)
                kwargs[columna] = valor
                filas = experimento(modo, ns=ns, n_consultas=n_consultas,
                                    reps=reps, verbose=False, **kwargs)
                todas.extend(filas)
                resumen(filas, modo, detallado=False)
        ruta_csv = escribir_csv(todas)
        if not args.sin_figuras:
            for ruta in generar_figuras(leer_csv(ruta_csv), cfg, params_barrido):
                print(f"  guardada: {ruta}")

    print(f"\nResultados crudos guardados en: {ruta_csv} "
          f"({len(todas)} filas, se sobrescriben en cada corrida).")
    if args.sin_figuras:
        print("Figuras omitidas (--sin-figuras); se pueden regenerar con "
              "--solo-figuras [--barrido ...].")

    print("\nRespuesta a la pregunta central (varía con radio, k, capacidad y")
    print("distribución; una sola cifra sería engañosa):")
    for modo in modos:
        c = cruces[modo]
        print(f"  {modo}: radio → {formato_cruce(c['radio'])} · "
              f"kNN → {formato_cruce(c['knn'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
