"""
test.py: pruebas de corrección y verificación visual del Quadtree.

Uso:
    python test.py                 # corre las pruebas y, si todas pasan, genera las figuras
    python test.py --sin-figuras   # solo las pruebas

Las pruebas son funciones 'test_*' con assert, sin unittest. El corredor del
final las ejecuta una por una, informa cuáles pasan y cuáles fallan, y
termina con código 1 si alguna falla.

Las figuras se guardan en la carpeta 'figuras/' (requiere matplotlib).
Unidades: todas las coordenadas están en metros.
"""
import math
import os
import random
import sys

from QuadTree import (
    Punto,
    Region,
    QuadTree,
    radio_fuerza_bruta,
    vecinos_fuerza_bruta,
)

AREA = 10000          # la ciudad es un cuadrado de AREA x AREA metros
CARPETA_FIGURAS = "figuras"

# Contador de consultas ejecutadas, para el resumen final
RESUMEN = {"consultas_radio": 0, "consultas_vecinos": 0}


# ----------------------------------------------------------------------
# Datos y utilidades
# ----------------------------------------------------------------------
def generar_puntos_uniformes(n, area=AREA, semilla=42):
    """n puntos distribuidos uniformemente en [0, area] x [0, area]."""
    rng = random.Random(semilla)
    return [Punto(rng.uniform(0, area), rng.uniform(0, area)) for _ in range(n)]


def generar_puntos_clusters(n, area=AREA, semilla=42, n_clusters=8, sigma_rel=0.03):
    """n puntos agrupados alrededor de n_clusters centros (zonas densas)."""
    rng = random.Random(semilla)
    centros = [(rng.uniform(0, area), rng.uniform(0, area)) for _ in range(n_clusters)]
    sigma = area * sigma_rel
    puntos = []
    for _ in range(n):
        cx, cy = rng.choice(centros)
        x = min(max(rng.gauss(cx, sigma), 0), area)
        y = min(max(rng.gauss(cy, sigma), 0), area)
        puntos.append(Punto(x, y))
    return puntos


def region_raiz(area=AREA):
    """Región raíz un poco mayor que los datos, para que ningún borde quede fuera."""
    margen = 1
    return Region(Punto(-margen, -margen), area + 2 * margen, area + 2 * margen)


def construir_arbol(puntos, capacidad=4, area=AREA):
    arbol = QuadTree(region_raiz(area), capacidad=capacidad)
    for p in puntos:
        assert arbol.insertar(p), f"No se pudo insertar el punto ({p.x}, {p.y})"
    return arbol


def claves(puntos):
    """Representación comparable (multiconjunto ordenado) de una lista de puntos."""
    return sorted((p.x, p.y) for p in puntos)


def distancias(consulta, puntos):
    return [consulta.distancia_punto(p) for p in puntos]


def contar_puntos(nodo):
    if nodo.es_hoja():
        return len(nodo.puntos)
    return sum(contar_puntos(h) for h in nodo.hijos)


def verificar_estructura(nodo):
    """Cada punto está dentro de la región de su hoja y los nodos internos no guardan puntos."""
    if nodo.es_hoja():
        for p in nodo.puntos:
            assert nodo.region.contiene_punto(p), (
                f"El punto ({p.x}, {p.y}) está fuera de la región de su hoja"
            )
    else:
        assert len(nodo.hijos) == 4, "Un nodo interno debe tener exactamente 4 hijos"
        assert len(nodo.puntos) == 0, "Un nodo interno no debe guardar puntos"
        for h in nodo.hijos:
            verificar_estructura(h)


def comparar_radio(arbol, puntos, centro, radio):
    """Compara el Quadtree con la fuerza bruta; lanza AssertionError si difieren."""
    RESUMEN["consultas_radio"] += 1
    obtenido = arbol.buscar_radio(centro, radio)
    esperado = radio_fuerza_bruta(puntos, centro, radio)
    assert claves(obtenido) == claves(esperado), (
        f"Radio distinto: centro=({centro.x:.1f}, {centro.y:.1f}), radio={radio}, "
        f"árbol={len(obtenido)} puntos, fuerza bruta={len(esperado)} puntos"
    )


def comparar_vecinos(arbol, puntos, consulta, k):
    """Compara por distancias (los empates pueden resolverse con puntos distintos)."""
    RESUMEN["consultas_vecinos"] += 1
    obtenido = arbol.buscar_mas_cercanos(consulta, k)
    esperado = vecinos_fuerza_bruta(puntos, consulta, k)
    assert len(obtenido) == len(esperado), (
        f"Cantidad distinta de vecinos: árbol={len(obtenido)}, fuerza bruta={len(esperado)}"
    )
    d_obtenido = distancias(consulta, obtenido)
    d_esperado = distancias(consulta, esperado)
    assert d_obtenido == d_esperado, (
        f"Distancias distintas: consulta=({consulta.x:.1f}, {consulta.y:.1f}), k={k}\n"
        f"  árbol:        {d_obtenido}\n  fuerza bruta: {d_esperado}"
    )
    assert d_obtenido == sorted(d_obtenido), "Los vecinos no vienen ordenados de menor a mayor distancia"


# ----------------------------------------------------------------------
# Pruebas de construcción
# ----------------------------------------------------------------------
def test_es_hoja_es_propiedad():
    arbol = QuadTree(region_raiz())
    assert isinstance(arbol.raiz.es_hoja(), bool), (
        "es_hoja debe ser una propiedad (@property), no un método"
    )


def test_construccion_conserva_todos_los_puntos():
    puntos = generar_puntos_uniformes(10000)
    arbol = construir_arbol(puntos)
    assert contar_puntos(arbol.raiz) == 10000


def test_construccion_estructura_valida():
    for puntos in (generar_puntos_uniformes(3000), generar_puntos_clusters(3000)):
        arbol = construir_arbol(puntos)
        verificar_estructura(arbol.raiz)


def test_insertar_fuera_de_la_region():
    arbol = QuadTree(region_raiz())
    assert arbol.insertar(Punto(AREA * 5, AREA * 5)) is False
    assert contar_puntos(arbol.raiz) == 0


def test_capacidades_distintas():
    puntos = generar_puntos_uniformes(1000)
    for capacidad in (1, 2, 4, 16, 64):
        arbol = construir_arbol(puntos, capacidad=capacidad)
        assert contar_puntos(arbol.raiz) == 1000, f"capacidad={capacidad}"
        verificar_estructura(arbol.raiz)


# ----------------------------------------------------------------------
# Caso hecho a mano (el mismo de la visualización paso a paso)
# ----------------------------------------------------------------------
def _arbol_a_mano():
    coords = {
        "A": (3, 3), "B": (7, 6), "K": (5, 7), "C": (12, 4), "D": (14, 2),
        "E": (3, 12), "F": (5, 14), "G": (9, 9), "H": (13, 10),
        "I": (10, 14), "J": (14, 14),
    }
    puntos = {nombre: Punto(x, y) for nombre, (x, y) in coords.items()}
    arbol = QuadTree(Region(Punto(0, 0), 16, 16), capacidad=4)
    for p in puntos.values():
        assert arbol.insertar(p)
    return arbol, puntos


def test_caso_a_mano_radio():
    arbol, p = _arbol_a_mano()
    encontrados = arbol.buscar_radio(Punto(6, 5), 2.5)
    assert claves(encontrados) == claves([p["B"], p["K"]]), (
        f"Se esperaban B y K, se obtuvo {claves(encontrados)}"
    )


def test_caso_a_mano_vecinos():
    arbol, p = _arbol_a_mano()
    vecinos = arbol.buscar_mas_cercanos(Punto(6, 5), 2)
    assert distancias(Punto(6, 5), vecinos) == [2, 5], "Distancias² esperadas: 2 (B) y 5 (K)"
    assert claves(vecinos) == claves([p["B"], p["K"]])


# ----------------------------------------------------------------------
# Radio: árbol contra fuerza bruta
# ----------------------------------------------------------------------
def _consultas_aleatorias(rng, n, margen=500):
    """Centros aleatorios, algunos fuera del área de los datos."""
    return [
        Punto(rng.uniform(-margen, AREA + margen), rng.uniform(-margen, AREA + margen))
        for _ in range(n)
    ]


def test_radio_uniforme_aleatorio():
    puntos = generar_puntos_uniformes(3000, semilla=1)
    arbol = construir_arbol(puntos)
    rng = random.Random(10)
    for centro in _consultas_aleatorias(rng, 300):
        comparar_radio(arbol, puntos, centro, rng.choice([0, 50, 200, 500, 1000, 3000]))


def test_radio_clusters_aleatorio():
    puntos = generar_puntos_clusters(3000, semilla=2)
    arbol = construir_arbol(puntos)
    rng = random.Random(11)
    for centro in _consultas_aleatorias(rng, 300):
        comparar_radio(arbol, puntos, centro, rng.choice([0, 50, 200, 500, 1000, 3000]))


def test_radio_con_capacidades_distintas():
    puntos = generar_puntos_uniformes(1500, semilla=3)
    rng = random.Random(12)
    consultas = _consultas_aleatorias(rng, 60)
    for capacidad in (1, 4, 32):
        arbol = construir_arbol(puntos, capacidad=capacidad)
        for centro in consultas:
            comparar_radio(arbol, puntos, centro, 700)


def test_radio_cero_sobre_un_punto_existente():
    puntos = generar_puntos_uniformes(500, semilla=4)
    arbol = construir_arbol(puntos)
    objetivo = puntos[123]
    encontrados = arbol.buscar_radio(Punto(objetivo.x, objetivo.y), 0)
    assert (objetivo.x, objetivo.y) in claves(encontrados)
    comparar_radio(arbol, puntos, Punto(objetivo.x, objetivo.y), 0)


def test_radio_gigante_devuelve_todos():
    puntos = generar_puntos_uniformes(800, semilla=5)
    arbol = construir_arbol(puntos)
    assert len(arbol.buscar_radio(Punto(AREA / 2, AREA / 2), AREA * 10)) == 800


def test_radio_consulta_fuera_del_area():
    puntos = generar_puntos_uniformes(800, semilla=6)
    arbol = construir_arbol(puntos)
    lejos = Punto(AREA * 3, AREA * 3)
    assert arbol.buscar_radio(lejos, 500) == []
    comparar_radio(arbol, puntos, lejos, AREA * 3)    # radio enorme desde afuera


def test_radio_arbol_vacio():
    arbol = QuadTree(region_raiz())
    assert arbol.buscar_radio(Punto(100, 100), 500) == []


def test_radio_tangente_incluye_el_borde():
    arbol = QuadTree(region_raiz(), capacidad=1)
    arbol.insertar(Punto(100, 0))
    encontrados = arbol.buscar_radio(Punto(0, 0), 100)   # el punto está a exactamente 100
    assert len(encontrados) == 1, "Un punto a distancia exactamente igual al radio debe incluirse"


# ----------------------------------------------------------------------
# Vecinos más cercanos: árbol contra fuerza bruta
# ----------------------------------------------------------------------
def test_vecinos_uniforme_aleatorio():
    puntos = generar_puntos_uniformes(3000, semilla=7)
    arbol = construir_arbol(puntos)
    rng = random.Random(20)
    for consulta in _consultas_aleatorias(rng, 200):
        comparar_vecinos(arbol, puntos, consulta, rng.choice([1, 3, 5, 20]))


def test_vecinos_clusters_aleatorio():
    puntos = generar_puntos_clusters(3000, semilla=8)
    arbol = construir_arbol(puntos)
    rng = random.Random(21)
    for consulta in _consultas_aleatorias(rng, 200):
        comparar_vecinos(arbol, puntos, consulta, rng.choice([1, 3, 5, 20]))


def test_vecinos_con_capacidades_distintas():
    puntos = generar_puntos_uniformes(1500, semilla=9)
    rng = random.Random(22)
    consultas = _consultas_aleatorias(rng, 60)
    for capacidad in (1, 4, 32):
        arbol = construir_arbol(puntos, capacidad=capacidad)
        for consulta in consultas:
            comparar_vecinos(arbol, puntos, consulta, 7)


def test_vecinos_k_uno():
    puntos = generar_puntos_uniformes(1000, semilla=10)
    arbol = construir_arbol(puntos)
    rng = random.Random(23)
    for consulta in _consultas_aleatorias(rng, 100):
        resultado = arbol.buscar_mas_cercanos(consulta, 1)
        assert len(resultado) == 1
        comparar_vecinos(arbol, puntos, consulta, 1)


def test_vecinos_k_mayor_que_n():
    puntos = generar_puntos_uniformes(50, semilla=11)
    arbol = construir_arbol(puntos)
    resultado = arbol.buscar_mas_cercanos(Punto(AREA / 2, AREA / 2), 500)
    assert len(resultado) == 50
    comparar_vecinos(arbol, puntos, Punto(AREA / 2, AREA / 2), 500)


def test_vecinos_k_invalido():
    puntos = generar_puntos_uniformes(50, semilla=12)
    arbol = construir_arbol(puntos)
    assert arbol.buscar_mas_cercanos(Punto(0, 0), 0) == []
    assert arbol.buscar_mas_cercanos(Punto(0, 0), -3) == []


def test_vecinos_consulta_sobre_un_punto_existente():
    puntos = generar_puntos_uniformes(500, semilla=13)
    arbol = construir_arbol(puntos)
    objetivo = puntos[77]
    consulta = Punto(objetivo.x, objetivo.y)
    resultado = arbol.buscar_mas_cercanos(consulta, 1)
    assert consulta.distancia_punto(resultado[0]) == 0


def test_vecinos_arbol_vacio():
    arbol = QuadTree(region_raiz())
    assert arbol.buscar_mas_cercanos(Punto(100, 100), 3) == []


def test_vecinos_consulta_fuera_del_area():
    puntos = generar_puntos_uniformes(800, semilla=14)
    arbol = construir_arbol(puntos)
    for consulta in (Punto(-5000, -5000), Punto(AREA * 2, AREA / 2), Punto(AREA / 2, AREA * 4)):
        comparar_vecinos(arbol, puntos, consulta, 5)


# ----------------------------------------------------------------------
# Casos borde de la estructura
# ----------------------------------------------------------------------
def test_puntos_duplicados_no_causan_recursion_infinita():
    arbol = QuadTree(region_raiz(), capacidad=4, profundidad_max=20)
    for _ in range(30):
        assert arbol.insertar(Punto(1234.5, 6789.0))
    assert contar_puntos(arbol.raiz) == 30
    assert len(arbol.buscar_radio(Punto(1234.5, 6789.0), 1)) == 30
    assert len(arbol.buscar_mas_cercanos(Punto(0, 0), 5)) == 5


def test_punto_en_el_centro_de_una_region():
    region = Region(Punto(0, 0), 16, 16)
    assert region.cuadrante(Punto(8, 8)) == 3, "El centro exacto va a arriba-derecha"
    arbol = QuadTree(region, capacidad=1)
    for p in (Punto(8, 8), Punto(1, 1), Punto(15, 15), Punto(8, 1), Punto(1, 8)):
        assert arbol.insertar(p)
    assert contar_puntos(arbol.raiz) == 5
    verificar_estructura(arbol.raiz)
    assert len(arbol.buscar_radio(Punto(8, 8), 0)) == 1


def test_puntos_en_el_borde_maximo_de_la_raiz():
    arbol = QuadTree(Region(Punto(0, 0), 16, 16), capacidad=1)
    for p in (Punto(16, 16), Punto(0, 0), Punto(16, 0), Punto(0, 16)):
        assert arbol.insertar(p), f"No se insertó ({p.x}, {p.y})"
    assert contar_puntos(arbol.raiz) == 4
    verificar_estructura(arbol.raiz)


def test_cuadrante_convencion_de_bits():
    region = Region(Punto(0, 0), 10, 10)
    assert region.cuadrante(Punto(2, 3)) == 0   # abajo-izquierda
    assert region.cuadrante(Punto(7, 3)) == 1   # abajo-derecha
    assert region.cuadrante(Punto(2, 8)) == 2   # arriba-izquierda
    assert region.cuadrante(Punto(7, 8)) == 3   # arriba-derecha


def test_distancia_min_de_region():
    region = Region(Punto(0, 0), 10, 10)
    assert region.distancia_min(Punto(3, 4)) == 0       # dentro
    assert region.distancia_min(Punto(13, 5)) == 9      # a 3 del borde derecho
    assert region.distancia_min(Punto(13, 14)) == 25    # diagonal: 3 y 4
    assert region.distancia_min(Punto(-2, 5)) == 4      # a 2 del borde izquierdo


# ----------------------------------------------------------------------
# Visualizaciones
# ----------------------------------------------------------------------
def zona_mas_vacia(puntos, rng, intentos=200):
    """Entre varias ubicaciones aleatorias, la más alejada de cualquier punto."""
    mejor, mejor_d = None, -1
    for _ in range(intentos):
        c = Punto(rng.uniform(0, AREA), rng.uniform(0, AREA))
        d = min(c.distancia_punto(p) for p in puntos)
        if d > mejor_d:
            mejor, mejor_d = c, d
    return mejor


def generar_figuras():
    try:
        import matplotlib
        matplotlib.use("Agg")                     # sin ventana: solo guarda archivos
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle, Rectangle
    except ImportError:
        print("matplotlib no está instalado: se omiten las figuras (pip install matplotlib).")
        return []

    os.makedirs(CARPETA_FIGURAS, exist_ok=True)
    guardadas = []

    def ruta(nombre):
        return os.path.join(CARPETA_FIGURAS, nombre)

    def fondo(ax, puntos):
        ax.scatter([p.x for p in puntos], [p.y for p in puntos], s=2, c="lightgray",
                   label=f"Todos los puntos ({len(puntos)})")
        ax.set_aspect("equal", adjustable="box")      # sin esto el círculo se vería como elipse
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")

    def dibujar_regiones(ax, nodo):
        if nodo.es_hoja():
            r = nodo.region
            ax.add_patch(Rectangle((r.origen.x, r.origen.y), r.ancho, r.alto,
                                   fill=False, ec="tab:purple", lw=0.6))
        else:
            for h in nodo.hijos:
                dibujar_regiones(ax, h)

    def figura_radio(puntos, arbol, centro, radio, nombre, titulo):
        encontrados = arbol.buscar_radio(centro, radio)
        esperados = radio_fuerza_bruta(puntos, centro, radio)
        coincide = claves(encontrados) == claves(esperados)
        assert coincide, f"{nombre}: el Quadtree no coincide con la fuerza bruta"

        fig, ax = plt.subplots(figsize=(7, 7))
        fondo(ax, puntos)
        ax.scatter([p.x for p in esperados], [p.y for p in esperados], s=70,
                   facecolors="none", edgecolors="tab:red", linewidths=1.2,
                   label=f"Fuerza bruta ({len(esperados)})")
        ax.scatter([p.x for p in encontrados], [p.y for p in encontrados], s=18,
                   c="tab:green", label=f"Quadtree ({len(encontrados)})")
        ax.scatter([centro.x], [centro.y], marker="*", s=220, c="gold",
                   edgecolors="black", zorder=5, label="Centro de búsqueda")
        ax.add_patch(Circle((centro.x, centro.y), radio, fill=False, ls="--", ec="tab:blue", lw=1.5))
        lim = max(radio * 3, 100)
        ax.set_xlim(centro.x - lim, centro.x + lim)
        ax.set_ylim(centro.y - lim, centro.y + lim)
        ax.set_title(f"{titulo}\nradio = {radio} m · {len(encontrados)} puntos · coincide con fuerza bruta")
        ax.legend(loc="upper right", fontsize=8)
        fig.savefig(ruta(nombre), dpi=130, bbox_inches="tight")
        plt.close(fig)
        guardadas.append(ruta(nombre))

    def figura_vecinos(puntos, arbol, consulta, k, nombre, titulo):
        resultado = arbol.buscar_mas_cercanos(consulta, k)
        esperado = vecinos_fuerza_bruta(puntos, consulta, k)
        assert distancias(consulta, resultado) == distancias(consulta, esperado), (
            f"{nombre}: las distancias del Quadtree no coinciden con la fuerza bruta"
        )
        dk = consulta.distancia_punto(resultado[-1])
        intrusos = sum(
            1 for p in puntos
            if consulta.distancia_punto(p) < dk and all(p is not r for r in resultado)
        )
        assert intrusos == 0, f"{nombre}: hay {intrusos} puntos más cerca que el k-ésimo vecino"

        fig, ax = plt.subplots(figsize=(7, 7))
        fondo(ax, puntos)
        for i, p in enumerate(resultado, start=1):
            ax.plot([consulta.x, p.x], [consulta.y, p.y], c="tab:green", lw=1, zorder=3)
            ax.annotate(str(i), (p.x, p.y), textcoords="offset points", xytext=(5, 5),
                        fontsize=9, color="darkgreen", zorder=6)
        ax.scatter([p.x for p in esperado], [p.y for p in esperado], s=90,
                   facecolors="none", edgecolors="tab:red", linewidths=1.2,
                   label="Fuerza bruta")
        ax.scatter([p.x for p in resultado], [p.y for p in resultado], s=28,
                   c="tab:green", zorder=4, label=f"Quadtree: {k} vecinos")
        ax.scatter([consulta.x], [consulta.y], marker="*", s=220, c="gold",
                   edgecolors="black", zorder=5, label="Consulta")
        radio_k = math.sqrt(dk)
        ax.add_patch(Circle((consulta.x, consulta.y), radio_k, fill=False, ls="--",
                            ec="tab:blue", lw=1.5, label="Distancia al k-ésimo vecino"))
        lim = max(radio_k * 2.5, 100)
        ax.set_xlim(consulta.x - lim, consulta.x + lim)
        ax.set_ylim(consulta.y - lim, consulta.y + lim)
        ax.set_title(f"{titulo}\nk = {k} · distancia al k-ésimo vecino = {radio_k:.1f} m · "
                     f"0 puntos más cercanos fuera del resultado")
        ax.legend(loc="upper right", fontsize=8)
        fig.savefig(ruta(nombre), dpi=130, bbox_inches="tight")
        plt.close(fig)
        guardadas.append(ruta(nombre))

    def figura_quadtree(nombre):
        puntos = generar_puntos_uniformes(200, semilla=99)
        arbol = construir_arbol(puntos, capacidad=4)
        fig, ax = plt.subplots(figsize=(7, 7))
        dibujar_regiones(ax, arbol.raiz)
        ax.scatter([p.x for p in puntos], [p.y for p in puntos], s=8, c="tab:green")
        ax.set_xlim(0, AREA)
        ax.set_ylim(0, AREA)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.set_title("Regiones del Quadtree (200 puntos, capacidad 4)")
        fig.savefig(ruta(nombre), dpi=130, bbox_inches="tight")
        plt.close(fig)
        guardadas.append(ruta(nombre))

    # Datos de las figuras
    rng = random.Random(7)
    uniformes = generar_puntos_uniformes(10000, semilla=42)
    arbol_u = construir_arbol(uniformes)
    clusters = generar_puntos_clusters(10000, semilla=42)
    arbol_c = construir_arbol(clusters)
    centro_ciudad = Punto(AREA / 2, AREA / 2)
    en_cluster = Punto(clusters[0].x + 5, clusters[0].y + 5)
    vacia = zona_mas_vacia(clusters, rng)

    # Radio
    figura_radio(uniformes, arbol_u, centro_ciudad, 500, "radio_tipico.png",
                 "Radio típico, datos uniformes")
    figura_radio(uniformes, arbol_u, centro_ciudad, 2500, "radio_grande.png",
                 "Radio grande, datos uniformes")
    figura_radio(uniformes, arbol_u, centro_ciudad, 30, "radio_pequeno.png",
                 "Radio muy pequeño, datos uniformes")
    figura_radio(uniformes, arbol_u, Punto(100, 100), 500, "radio_borde.png",
                 "Centro en la esquina del área (el círculo sale de los datos)")
    figura_radio(clusters, arbol_c, en_cluster, 500, "radio_cluster.png",
                 "Radio en una zona densa (datos agrupados)")

    # Vecinos más cercanos
    figura_vecinos(uniformes, arbol_u, centro_ciudad, 1, "vecinos_k1.png",
                   "Vecino más cercano, datos uniformes")
    figura_vecinos(uniformes, arbol_u, centro_ciudad, 10, "vecinos_k10.png",
                   "10 vecinos más cercanos, datos uniformes")
    figura_vecinos(clusters, arbol_c, en_cluster, 5, "vecinos_cluster_k5.png",
                   "5 vecinos más cercanos en una zona densa")
    figura_vecinos(clusters, arbol_c, vacia, 5, "vecinos_zona_vacia.png",
                   "5 vecinos más cercanos desde una zona sin puntos")

    # Estructura del árbol
    figura_quadtree("quadtree_regiones.png")
    return guardadas



def correr_pruebas():
    pruebas = [(n, f) for n, f in sorted(globals().items())
               if n.startswith("test_") and callable(f)]
    fallos = []
    for nombre, funcion in pruebas:
        try:
            funcion()
            print(f"  OK     {nombre}")
        except AssertionError as e:
            fallos.append(nombre)
            print(f"  FALLÓ  {nombre}\n         {e}")
        except Exception as e:
            fallos.append(nombre)
            print(f"  ERROR  {nombre}\n         {type(e).__name__}: {e}")
    print(f"\n{len(pruebas) - len(fallos)} de {len(pruebas)} pruebas pasaron.")
    print(f"Consultas comparadas contra fuerza bruta: "
          f"{RESUMEN['consultas_radio']} de radio y {RESUMEN['consultas_vecinos']} de vecinos.")
    return fallos


if __name__ == "__main__":
    print("Pruebas de corrección\n")
    fallos = correr_pruebas()
    if fallos:
        print("\nHay pruebas fallidas; no se generan figuras para no mostrar resultados incorrectos.")
        sys.exit(1)
    if "--sin-figuras" not in sys.argv:
        print("\nGenerando figuras en la carpeta 'figuras/'...")
        for archivo in generar_figuras():
            print(f"  guardada: {archivo}")