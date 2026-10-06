"""
Benchmark de escalabilidad: Lista nativa vs ABB vs Arbol B+
============================================================

COMO SE REALIZAN LAS PRUEBAS (resumen ordenado):
  1. Generacion: `generar_estudiantes(n, ordenado)` crea n dicts con id unico.
     - ordenado=False -> ids mezclados (shuffle), arboles balanceados en promedio.
     - ordenado=True  -> ids secuenciales, ABB se degenera a lista O(N).
  2. Construccion: `construir(est)` inserta el MISMO dataset en las 3 estructuras.
     - Lista nativa: solo guarda referencia (O(1)).
     - ABB: `insertar()` uno por uno (O(N log N) aleatorio, O(N^2) ordenado).
     - B+: `insertar(id, dato)` con splits (O(N log N) siempre).
  3. Medicion: `time.perf_counter()` alrededor de `fn()`, repetido REPETICIONES
     veces. Se reporta mediana, media, desviacion estandar (muestral, n-1),
     min y max. La mediana aisla ruido del SO/GC; la stdev mide dispersión.
  4. Experimentos (en este orden):
     a) busqueda_sin_build : estructuras ya construidas, solo N_BUSQUEDAS puntuales.
     b) busqueda_con_build : reconstruye la estructura DENTRO del timer + mismas
        búsquedas. Muestra costo total (insercion + busqueda).
     c) rango_F% : `buscar_rango(lo,hi)` con F en RANGO_FRACCIONES. Lista hace
        scan O(N), ABB inorden con poda, B+ baja a hoja de lo y recorre hojas.
     d) listar_ordenado : `listar()` completo ordenado por id. Lista hace
        `sorted O(N log N)`, ABB inorden O(N), B+ recorre hojas enlazadas O(N).
  5. Verificacion: por cada N se comprueba que los 3 listados/rangos devuelven
     los mismos ids y el tamaño esperado.

COMO EDITAR PARAMETROS:
  Edita SOLO el dict CONFIG de abajo. Todo (titulos, xticks, CSV, consola)
  se genera desde CONFIG, asi los labels de las graficas siempre coinciden
  con la prueba real. Para una corrida rapida de humo usa por ejemplo:
    CONFIG["MULTIPLOS"] = [1, 2]; CONFIG["REPETICIONES"] = 3
    CONFIG["N_BUSQUEDAS"] = 100; CONFIG["N_BASE"] = 200

NOTA DEMO LEGACY:
  `realizar_pruebas()` es solo demo vieja (N=10000 fijo). Su llamada esta
  comentada en __main__ y NO entra en CSV ni graficas.
"""

import csv
import random
import statistics
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Un solo limite de recursion (ABB degenerado con datos ordenados)
sys.setrecursionlimit(200000)

from ArboolABB import ArbolABB
from ArbolBplus import ArbolBPlus
from generar_estudiantes import generar_estudiantes


# =====================================================================
# DEMO LEGACY (conservada tal cual, NO se usa en el benchmark)
# =====================================================================
def realizar_pruebas():
    """DEMO legacy: N=10000 fijo, sin repeticiones ni graficas. Solo demo."""
    # ---------------------------------------------------------
    # 1. GENERACIÓN DE DATOS
    # ---------------------------------------------------------
    print("Generando datos de estudiantes...")
    estudiantes_aleatorios = generar_estudiantes(10000, ordenado=False)
    estudiantes_ordenados = generar_estudiantes(10000, ordenado=True)

    # Extraer 100 IDs aleatorios para realizar las búsquedas sobre los mismos objetivos
    todos_los_ids = [e["id"] for e in estudiantes_aleatorios]
    ids_busqueda = random.sample(todos_los_ids, 1000)

    # ---------------------------------------------------------
    # 2. ESCENARIO A: IDs EN ORDEN ALEATORIO
    # ---------------------------------------------------------
    print("\n" + "=" * 50)
    print("  ESCENARIO 1: IDs EN ORDEN ALEATORIO")
    print("=" * 50)

    # A) Lista Nativa
    lista_aleatoria = estudiantes_aleatorios

    # B) Árbol ABB
    arbol_abb_aleatorio = ArbolABB()
    for e in estudiantes_aleatorios:
        arbol_abb_aleatorio.insertar(e)

    # C) Árbol B+
    arbol_bplus_aleatorio = ArbolBPlus(t=3)
    for e in estudiantes_aleatorios:
        arbol_bplus_aleatorio.insertar(e["id"], e)

    # --- Mediciones para IDs Aleatorios ---
    # Búsqueda en Lista
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = next((e for e in lista_aleatoria if e["id"] == target_id), None)
    tiempo_lista_aleatorio = time.perf_counter() - t_inicio

    # Búsqueda en ABB
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = arbol_abb_aleatorio.buscar(target_id)
    tiempo_abb_aleatorio = time.perf_counter() - t_inicio

    # Búsqueda en Árbol B+
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = arbol_bplus_aleatorio.buscar(target_id)
    tiempo_bplus_aleatorio = time.perf_counter() - t_inicio

    print(f"Lista Nativa : {tiempo_lista_aleatorio:.6f} segundos")
    print(f"Árbol ABB    : {tiempo_abb_aleatorio:.6f} segundos")
    print(f"Árbol B+     : {tiempo_bplus_aleatorio:.6f} segundos")

    # ---------------------------------------------------------
    # 3. ESCENARIO B: IDs YA ORDENADOS
    # ---------------------------------------------------------
    print("\n" + "=" * 50)
    print("  ESCENARIO 2: IDs YA ORDENADOS")
    print("=" * 50)

    # A) Lista Nativa
    lista_ordenada = estudiantes_ordenados

    # B) Árbol ABB
    arbol_abb_ordenado = ArbolABB()
    for e in estudiantes_ordenados:
        arbol_abb_ordenado.insertar(e)

    # C) Árbol B+
    arbol_bplus_ordenado = ArbolBPlus(t=3)
    for e in estudiantes_ordenados:
        arbol_bplus_ordenado.insertar(e["id"], e)

    # --- Mediciones para IDs Ordenados ---
    # Búsqueda en Lista
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = next((e for e in lista_ordenada if e["id"] == target_id), None)
    tiempo_lista_ordenado = time.perf_counter() - t_inicio

    # Búsqueda en ABB (Degenerado)
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = arbol_abb_ordenado.buscar(target_id)
    tiempo_abb_ordenado = time.perf_counter() - t_inicio

    # Búsqueda en Árbol B+
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = arbol_bplus_ordenado.buscar(target_id)
    tiempo_bplus_ordenado = time.perf_counter() - t_inicio

    print(f"Lista Nativa : {tiempo_lista_ordenado:.6f} segundos")
    print(f"Árbol ABB    : {tiempo_abb_ordenado:.6f} segundos  <-- (Degenerado a O(N))")
    print(f"Árbol B+     : {tiempo_bplus_ordenado:.6f} segundos  <-- (Mantiene O(log N))")


# =====================================================================
# CONFIG UNICO EDITABLE — edita solo aqui
# =====================================================================
CONFIG = {
    "N_BASE": 1000,                  # n: tamanos N = n, 2n, ..., 10n
    "MULTIPLOS": list(range(1, 11)),  # [1..10]
    "N_BUSQUEDAS": 1000,            # nº busquedas puntuales por medicion (se recorta a min(N_BUSQUEDAS, N))
    "REPETICIONES": 30,             # nº repeticiones por punto (para mediana +- stdev). NO cambiar por ahora.
    "RANGO_FRACCIONES": [0.01, 0.05, 0.10, 0.25],  # pruebas "pro rango": 1%, 5%, 10%, 25% de N
    "T_BPLUS": 3,                    # grado minimo del B+
    "SEED": 42,                      # reproducibilidad
}


# ---------------------------------------------------------------
# Busqueda por rango en la lista nativa (los arboles usan su propio buscar_rango)
# ---------------------------------------------------------------
def rango_lista(lista, lo, hi):
    return [e for e in lista if lo <= e["id"] <= hi]


# ---------------------------------------------------------------
# Adaptadores homogeneos
# ---------------------------------------------------------------
def construir(est):
    """Construye las 3 estructuras desde el mismo dataset `est`."""
    abb = ArbolABB()
    bp = ArbolBPlus(t=CONFIG["T_BPLUS"])
    for e in est:
        abb.insertar(e)
        bp.insertar(e["id"], e)
    return {"Lista nativa": est, "ABB": abb, "B+": bp}


def construir_uno(nombre, est):
    """Reconstruye UNA sola estructura (para prueba con-construccion)."""
    if nombre == "Lista nativa":
        return est  # construir lista = guardar referencia, O(1)
    if nombre == "ABB":
        abb = ArbolABB()
        for e in est:
            abb.insertar(e)
        return abb
    bp = ArbolBPlus(t=CONFIG["T_BPLUS"])
    for e in est:
        bp.insertar(e["id"], e)
    return bp


def buscar(nombre, est, id_):
    if nombre == "Lista nativa":
        return next((e for e in est if e["id"] == id_), None)
    return est.buscar(id_)


def rango(nombre, est, lo, hi):
    if nombre == "Lista nativa":
        return rango_lista(est, lo, hi)
    return est.buscar_rango(lo, hi)


def listar(nombre, est):
    if nombre == "Lista nativa":
        return sorted(est, key=lambda e: e["id"])
    return est.listar_en_orden()


ESTRUCTURAS = ["Lista nativa", "ABB", "B+"]
ORDENES = ["desordenados", "ordenados"]

# Orden fijo de experimentos para listar de manera ordenada en consola/CSV/graficas
EXPERIMENTOS = (
    ["busqueda_sin_build", "busqueda_con_build"]
    + [f"rango_{int(f * 100)}pct" for f in CONFIG["RANGO_FRACCIONES"]]
    + ["listar_ordenado"]
)


def rango_lo_hi(sorted_ids, n, frac):
    """Calcula (lo, hi, esperado) desde los ids reales, robusto al generador."""
    size = max(1, int(n * frac))
    start = min(n // 4, n - size)
    lo = sorted_ids[start]
    hi = sorted_ids[start + size - 1]
    return lo, hi, size


def medir(fn):
    """Mide REPETICIONES veces. Devuelve dict con mediana/media/stdev/min/max (segundos).

    stdev es muestral (statistics.stdev, n-1): mide dispersion entre
    repeticiones del mismo N. Con REPETICIONES=1 devuelve stdev=0.0.
    """
    ts = []
    for _ in range(CONFIG["REPETICIONES"]):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return {
        "median": statistics.median(ts),
        "mean": statistics.fmean(ts),
        "stdev": statistics.stdev(ts) if len(ts) > 1 else 0.0,
        "min": min(ts),
        "max": max(ts),
    }


def ejecutar():
    random.seed(CONFIG["SEED"])
    n_base = CONFIG["N_BASE"]
    tamanos = [n_base * k for k in CONFIG["MULTIPLOS"]]
    fracs = list(CONFIG["RANGO_FRACCIONES"])
    exps = (
        ["busqueda_sin_build", "busqueda_con_build"]
        + [f"rango_{int(f * 100)}pct" for f in fracs]
        + ["listar_ordenado"]
    )
    res = {(x, o, s): [] for x in exps for o in ORDENES for s in ESTRUCTURAS}

    for n in tamanos:
        for orden in ORDENES:
            est = generar_estudiantes(n, ordenado=(orden == "ordenados"))
            estructuras = construir(est)
            ids = [e["id"] for e in est]
            sorted_ids = sorted(ids)
            # Coherencia: si N < N_BUSQUEDAS se recorta (antes crasheaba con sample)
            k_busq = min(CONFIG["N_BUSQUEDAS"], n)
            ids_busqueda = random.sample(ids, k_busq)
            print(f"N={n:6d}  datos {orden:13s}  busquedas_efectivas={k_busq}", flush=True)

            # Rangos por fraccion, calculados desde datos reales
            rangos = {f: rango_lo_hi(sorted_ids, n, f) for f in fracs}

            for s in ESTRUCTURAS:
                e = estructuras[s]
                # a) busqueda SIN construccion (estructuras ya construidas)
                res[("busqueda_sin_build", orden, s)].append(
                    medir(lambda s=s, e=e: [buscar(s, e, i) for i in ids_busqueda]))
                # b) busqueda CON construccion (reconstruye dentro del timer)
                def _con(s=s):
                    est_nueva = construir_uno(s, est)
                    for i in ids_busqueda:
                        buscar(s, est_nueva, i)
                res[("busqueda_con_build", orden, s)].append(medir(_con))
                # c) rangos por fraccion (sin construccion)
                for f in fracs:
                    lo, hi, _ = rangos[f]
                    key = f"rango_{int(f * 100)}pct"
                    res[(key, orden, s)].append(medir(lambda s=s, e=e, lo=lo, hi=hi: rango(s, e, lo, hi)))
                # d) listado ordenado completo (sin construccion)
                res[("listar_ordenado", orden, s)].append(medir(lambda s=s, e=e: listar(s, e)))

            # verificacion de correccion (mismo resultado en las 3 estructuras)
            for f in fracs:
                lo, hi, esperado = rangos[f]
                r = [len(rango(s, estructuras[s], lo, hi)) for s in ESTRUCTURAS]
                assert len(set(r)) == 1 and r[0] == esperado, (f, r, esperado)
            l = [[x["id"] for x in listar(s, estructuras[s])] for s in ESTRUCTURAS]
            assert l[0] == l[1] == l[2] == sorted_ids
    return tamanos, res


def titulo_exp(x):
    """Titulo coherente con CONFIG (nunca hardcodear el nº de busquedas)."""
    nb = CONFIG["N_BUSQUEDAS"]
    if x == "busqueda_sin_build":
        return f"{nb} busquedas aleatorias por id (sin construccion)"
    if x == "busqueda_con_build":
        return f"{nb} busquedas aleatorias por id (incluyendo construccion)"
    if x.startswith("rango_"):
        pct = x.replace("rango_", "").replace("pct", "")
        return f"Busqueda por rango ({pct}% de los ids)"
    if x == "listar_ordenado":
        return "Listado completo ordenado por id"
    return x


ESTILO = {"Lista nativa": ("o-", "tab:blue"), "ABB": ("s-", "tab:red"), "B+": ("^-", "tab:green")}


def graficar(tamanos, res):
    xt = [f"{k}n" for k in CONFIG["MULTIPLOS"]]
    n_base = CONFIG["N_BASE"]
    exps = list(res.keys())
    # experimentos unicos en orden
    vistos = []
    for (x, _o, _s) in exps:
        if x not in vistos:
            vistos.append(x)

    for x in vistos:
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
        for ax, orden in zip(axes, ORDENES):
            for s in ESTRUCTURAS:
                m, c = ESTILO[s]
                meds = [d["median"] * 1000 for d in res[(x, orden, s)]]
                stds = [d["stdev"] * 1000 for d in res[(x, orden, s)]]
                ax.errorbar(tamanos, meds, yerr=stds, fmt=m, color=c,
                            label=s, lw=2, capsize=3, elinewidth=1)
            ax.set_title(f"Datos {orden}")
            ax.set_xlabel(f"Tamano N (n = {n_base})")
            ax.set_ylabel("Tiempo mediana +- stdev (ms)")
            ax.set_xticks(tamanos)
            ax.set_xticklabels(xt)
            ax.grid(alpha=0.3)
            ax.legend()
        fig.suptitle(f"{titulo_exp(x)} — mediana de {CONFIG['REPETICIONES']} reps", fontsize=13)
        fig.tight_layout()
        fig.savefig(f"grafica_{x}.png", dpi=140)
        plt.close(fig)

    # Resumen 4x2 con los 4 paneles clave (evita figura gigante de 7 filas)
    claves_resumen = ["busqueda_sin_build", "busqueda_con_build",
                      "rango_10pct" if "rango_10pct" in vistos else vistos[2],
                      "listar_ordenado"]
    fig, axes = plt.subplots(4, 2, figsize=(13, 14))
    for r, x in enumerate(claves_resumen):
        for c, orden in enumerate(ORDENES):
            ax = axes[r][c]
            for s in ESTRUCTURAS:
                m, col = ESTILO[s]
                meds = [d["median"] * 1000 for d in res[(x, orden, s)]]
                stds = [d["stdev"] * 1000 for d in res[(x, orden, s)]]
                ax.errorbar(tamanos, meds, yerr=stds, fmt=m, color=col,
                            label=s, lw=2, capsize=2, elinewidth=1)
            ax.set_title(f"{titulo_exp(x)} - {orden}", fontsize=10)
            ax.set_xticks(tamanos)
            ax.set_xticklabels(xt)
            ax.set_ylabel("ms (mediana+-stdev)")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("resumen_escalabilidad.png", dpi=130)
    plt.close(fig)


def exportar(tamanos, res):
    with open("preliminar1/resultados.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["experimento", "titulo", "orden", "estructura"]
                   + [f"N={n}_median_ms" for n in tamanos]
                   + [f"N={n}_stdev_ms" for n in tamanos]
                   + ["factor_10n/n_medianas"])
        # listado ordenado: experimento, orden, estructura
        for x in sorted({k[0] for k in res}):
            for o in ORDENES:
                for s in ESTRUCTURAS:
                    ts = res[(x, o, s)]
                    meds = [f"{d['median'] * 1000:.4f}" for d in ts]
                    stds = [f"{d['stdev'] * 1000:.4f}" for d in ts]
                    factor = f"{ts[-1]['median'] / ts[0]['median']:.2f}" if ts[0]["median"] > 0 else "inf"
                    w.writerow([x, titulo_exp(x), o, s] + meds + stds + [factor])
    # detalle completo (media/min/max) para analisis fino
    with open("preliminar1/resultados_detalle.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["experimento", "orden", "estructura", "N",
                    "median_ms", "mean_ms", "stdev_ms", "min_ms", "max_ms"])
        for x in sorted({k[0] for k in res}):
            for o in ORDENES:
                for s in ESTRUCTURAS:
                    for n, d in zip(tamanos, res[(x, o, s)]):
                        w.writerow([x, o, s, n,
                                    f"{d['median'] * 1000:.4f}", f"{d['mean'] * 1000:.4f}",
                                    f"{d['stdev'] * 1000:.4f}", f"{d['min'] * 1000:.4f}",
                                    f"{d['max'] * 1000:.4f}"])


def imprimir_resumen(tamanos, res):
    print("\nFactor de crecimiento t(10n)/t(n) sobre medianas + stdev en 10n:")
    for x in sorted({k[0] for k in res}):
        for o in ORDENES:
            for s in ESTRUCTURAS:
                ts = res[(x, o, s)]
                factor = ts[-1]["median"] / ts[0]["median"] if ts[0]["median"] > 0 else float("inf")
                print(f"  {x:22s} {o:13s} {s:13s} x{factor:7.1f}  "
                      f"(mediana10n={ts[-1]['median'] * 1000:.2f}ms stdev={ts[-1]['stdev'] * 1000:.2f}ms)")


if __name__ == "__main__":
    # realizar_pruebas()  # DEMO legacy: descomentar solo para verla, no entra en CSV/graficas
    print(f"CONFIG: {CONFIG}")
    tamanos, res = ejecutar()
    exportar(tamanos, res)
    graficar(tamanos, res)
    imprimir_resumen(tamanos, res)

        ## añadir pruebas de busqueda con construccion y sin construccion
        #medir dispersion, varianza para determinar numero minimo de epeticiones si converge