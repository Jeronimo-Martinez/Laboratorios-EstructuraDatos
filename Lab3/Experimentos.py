"""
COMO SE REALIZAN LAS PRUEBAS:
  1. Generacion: `generar_estudiantes(n, ordenado)` crea n dicts con id unico.
     - ordenado=False -> ids mezclados (shuffle), arboles balanceados en promedio.
     - ordenado=True  -> ids secuenciales, ABB se degenera a lista O(N).
  2. Construccion: `construir(est)` inserta el MISMO dataset en las 3 estructuras.
     - Lista nativa: solo guarda referencia (O(1)).
     - ABB: `insertar()` uno por uno (O(N log N) aleatorio, O(N^2) ordenado).
     - B+: `insertar(id, dato)` con splits (O(N log N) siempre).
  3. Medicion: `time.perf_counter()` alrededor de `fn()`, repetido REPETICIONES
     veces. Se reporta mediana, media, desviacion estandar (muestral, n-1),
     min, max y cuartiles p25/p75. La mediana aisla ruido del SO/GC; la stdev
     mide dispersión y el IQR (p25-p75) se usa en las barras de error porque
     las repeticiones no siempre son normales (ver test_normalidad.py).
     rango_*/listar miden BATCH_RANGO_LISTAR llamadas por repeticion y se
     normaliza por llamada: una sola llamada dura microsegundos (ruido de reloj).
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

CONFIG = {
    "N_BASE": 1000,
    "MULTIPLOS": list(range(5, 21)),  # [5..20] -> N = 5000, 6000, ..., 20000
    "N_BUSQUEDAS": 1000,            # # busquedas puntuales por medicion (se recorta a min(N_BUSQUEDAS, N))
    "REPETICIONES": 30,             # # repeticiones por punto
    "RANGO_FRACCIONES": [0.01, 0.05, 0.10, 0.25],  # pruebas de rango: 1%, 5%, 10%, 25% de N
    "T_BPLUS": 3,                    # grado minimo del B+
    "SEED": 42,                      # reproducibilidad
    "BATCH_RANGO_LISTAR": 20,  # 3 llamadas internas por repeticion en rango/listar(para disminuir el ruido)
    "M_VALORES": [10, 50, 100, 500, 1000, 5000],  # experimento variar-M (variar # de busquedas)
    "N_FIJO_M": 5000,  # N fijo para variar-M
}



# Busqueda por rango en la lista nativa
def rango_lista(lista, lo, hi):
    return [e for e in lista if lo <= e["id"] <= hi]

def construir(est):
    """Construye las 3 estructuras desde el mismo dataset `est`."""
    abb = ArbolABB()
    bp = ArbolBPlus(t=CONFIG["T_BPLUS"])
    for e in est:
        abb.insertar(e)
        bp.insertar(e["id"], e)
    return {"Lista nativa": est, "ABB": abb, "B+": bp}

def construir_uno(nombre, est):
    """Reconstruye UNA sola estructura (para prueba con construccion)."""
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

#buscar en lista nativa
def buscar(nombre, est, id_):
    if nombre == "Lista nativa":
        return next((e for e in est if e["id"] == id_), None)
    return est.buscar(id_)

#rango en lista nativa
def rango(nombre, est, lo, hi):
    if nombre == "Lista nativa":
        return rango_lista(est, lo, hi)
    return est.buscar_rango(lo, hi)

#listar en orden en lista nativa
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

#calcular rango ordenado esperado
def rango_lo_hi(sorted_ids, n, frac):
    size = max(1, int(n * frac))
    start = min(n // 4, n - size)
    lo = sorted_ids[start]
    hi = sorted_ids[start + size - 1]
    return lo, hi, size

#para el resumen .csv
def _resumen_con_cuartiles(ts):
    """Mediana/media/stdev/min/max + cuartiles p25/p75 (para barras IQR asimetricas)."""
    if len(ts) >= 4:
        qs = statistics.quantiles(ts, n=4)
        p25, p75 = qs[0], qs[2]
    else:
        p25, p75 = min(ts), max(ts)
    return {
        "median": statistics.median(ts),
        "mean": statistics.fmean(ts),
        "stdev": statistics.stdev(ts) if len(ts) > 1 else 0.0,
        "min": min(ts),
        "max": max(ts),
        "p25": p25,
        "p75": p75,
        "raw": ts,
    }


def medir(fn):
    """Mide REPETICIONES veces. Devuelve dict con mediana/media/stdev/min/max/p25/p75 (segundos).

    stdev es muestral (statistics.stdev, n-1): mide dispersion entre
    repeticiones del mismo N. Con REPETICIONES=1 devuelve stdev=0.0.
    La lista cruda queda en la clave "raw" (tiempos por repeticion, en segundos).
    p25/p75 son los cuartiles para graficar rango intercuartilico (asimétrico,
    """
    ts = []
    for _ in range(CONFIG["REPETICIONES"]):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return _resumen_con_cuartiles(ts)


def medir_batch(fn, batch):
    """Mide fn() ejecutada `batch` veces por repeticion; normaliza a tiempo
    POR LLAMADA dividiendo las 7 claves entre batch (unidades consistentes).

    Sirve para rango/listar donde una sola llamada dura microsegundos (ruido).
    """
    ts = []
    for _ in range(CONFIG["REPETICIONES"]):
        t0 = time.perf_counter()
        for _ in range(batch):
            fn()
        ts.append((time.perf_counter() - t0) / batch)
    return _resumen_con_cuartiles(ts)


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
            # Coherencia: si N < N_BUSQUEDAS se recorta
            k_busq = min(CONFIG["N_BUSQUEDAS"], n)
            ids_busqueda = random.sample(ids, k_busq)
            print(f"N={n:6d}  datos {orden:13s}  busquedas_efectivas={k_busq}", flush=True)

            # Rangos por fraccion, calculados desde datos reales
            rangos = {f: rango_lo_hi(sorted_ids, n, f) for f in fracs}

            for s in ESTRUCTURAS:
                e = estructuras[s]
                # busqueda SIN construccion
                res[("busqueda_sin_build", orden, s)].append(
                    medir(lambda s=s, e=e: [buscar(s, e, i) for i in ids_busqueda]))
                # busqueda CON construccion
                def _con(s=s):
                    est_nueva = construir_uno(s, est)
                    for i in ids_busqueda:
                        buscar(s, est_nueva, i)
                res[("busqueda_con_build", orden, s)].append(medir(_con))
                #rangos por fraccion sin construccion
                batch = CONFIG["BATCH_RANGO_LISTAR"]
                for f in fracs:
                    lo, hi, _ = rangos[f]
                    key = f"rango_{int(f * 100)}pct"
                    res[(key, orden, s)].append(
                        medir_batch(lambda s=s, e=e, lo=lo, hi=hi: rango(s, e, lo, hi), batch))
                #listado ordenado completo sin construccion
                res[("listar_ordenado", orden, s)].append(
                    medir_batch(lambda s=s, e=e: listar(s, e), batch))

            # verificar que las listas obtenidas sean la misma lista para las 3 estructuras.
            for f in fracs:
                lo, hi, esperado = rangos[f]
                r = [len(rango(s, estructuras[s], lo, hi)) for s in ESTRUCTURAS]
                assert len(set(r)) == 1 and r[0] == esperado, (f, r, esperado)
            l = [[x["id"] for x in listar(s, estructuras[s])] for s in ESTRUCTURAS]
            assert l[0] == l[1] == l[2] == sorted_ids
    return tamanos, res


def ejecutar_variando_M():
    # Experimento adicional: N fijo, varia M (# de busquedas), datos desordenados.
    n_fijo = CONFIG["N_FIJO_M"]
    Ms = [m for m in CONFIG["M_VALORES"] if m <= n_fijo]
    assert Ms, f"M_VALORES={CONFIG['M_VALORES']} todos > N_fijo={n_fijo}"
    random.seed(CONFIG["SEED"] + 1)  # stream distinto al del barrido en N
    est = generar_estudiantes(n_fijo, ordenado=False)
    estructuras = construir(est)
    ids = [e["id"] for e in est]
    resM = {s: [] for s in ESTRUCTURAS}
    for m in Ms:
        ids_m = random.sample(ids, m)
        print(f"N_fijo={n_fijo}  M={m}", flush=True)
        for s in ESTRUCTURAS:
            e = estructuras[s]
            resM[s].append(medir(lambda s=s, e=e: [buscar(s, e, i) for i in ids_m]))
    return n_fijo, Ms, resM


def titulo_exp(x):

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

# Graficacion

ESTILO = {"Lista nativa": ("o-", "tab:blue"), "ABB": ("s-", "tab:red"), "B+": ("^-", "tab:green")}


def _iqr_err(ds):
    """Barras asimetricas [low, high] en ms desde p25/p75 (recortadas para escala log).

    low/high se recortan para no cruzar el cero en escala logaritmica
    (una barra que llegara a 0 romperia el eje log).
    """
    meds = [d["median"] * 1000 for d in ds]
    low, high = [], []
    for d, m in zip(ds, meds):
        p25 = d.get("p25", d["median"]) * 1000
        p75 = d.get("p75", d["median"]) * 1000
        lo = max(0.0, m - p25)
        hi = max(0.0, p75 - m)
        if m > 0:
            lo = min(lo, m * 0.999)  # el extremo inferior queda > 0
        low.append(lo)
        high.append(hi)
    return meds, [low, high]


def _eje_y_log_uniforme(ax):
    """Escala log con ticks mayores SOLO en potencias exactas de 10.

    Con el localizador automatico, paneles de <1 decada mostraban ticks
    "comodos" (p.ej. 2e-1, 6e-2) a distancias visuales inconsistentes entre
    graficas. Fijando los mayores en 10^k, cada decada mide siempre lo mismo
    en todas las figuras. (Dentro de una decada, 2x..9x no son equidistantes
    por diseno del logaritmo: eso es correcto, no un bug.)
    """
    from matplotlib.ticker import LogFormatterMathtext, LogLocator
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10, numticks=12))
    ax.yaxis.set_minor_locator(
        LogLocator(base=10, subs=tuple(float(i) for i in range(2, 10)), numticks=24))
    ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10))


def _ylim_comun(res, x, ordenes, margen=1.15):
    """Rango Y comun (sobre p25..p75 de todas las curvas, en ms).

    Ambos paneles de una figura comparten ylim para que desordenados vs
    ordenados sean comparables a ojo. Siempre > 0 (apto para log).
    """
    lo, hi = float("inf"), 0.0
    for o in ordenes:
        for s in ESTRUCTURAS:
            for d in res[(x, o, s)]:
                p25 = d.get("p25", d["median"]) * 1000
                p75 = d.get("p75", d["median"]) * 1000
                if p25 > 0:
                    lo = min(lo, p25)
                if p75 > 0:
                    hi = max(hi, p75)
    if not hi > 0:
        return None
    if not lo > 0 or lo >= hi:
        lo = hi / 100.0
    return (lo / margen, hi * margen)


def graficar(tamanos, res):
    import math
    import os
    base = _base_dir()
    dir_prelim = os.path.join(base, "Resultados")
    os.makedirs(dir_prelim, exist_ok=True)
    xt = [f"{k}n" for k in CONFIG["MULTIPLOS"]]
    n_base = CONFIG["N_BASE"]
    exps = list(res.keys())
    # experimentos unicos en orden
    vistos = []
    for (x, _o, _s) in exps:
        if x not in vistos:
            vistos.append(x)

    for x in vistos:
        ylim = _ylim_comun(res, x, ORDENES)
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
        for ax, orden in zip(axes, ORDENES):
            for s in ESTRUCTURAS:
                m, c = ESTILO[s]
                meds, yerr = _iqr_err(res[(x, orden, s)])
                ax.errorbar(tamanos, meds, yerr=yerr, fmt=m, color=c,
                            label=s, lw=2, capsize=3, elinewidth=1)
            ax.set_title(f"Datos {orden}")
            ax.set_xlabel(f"Tamano N (n = {n_base})")
            ax.set_ylabel("Tiempo mediana, rango intercuartilico (ms)")
            ax.set_xticks(tamanos)
            ax.set_xticklabels(xt, rotation=45, ha="right")
            _eje_y_log_uniforme(ax)  # mismas decadas en toda figura
            if ylim is not None:
                ax.set_ylim(ylim)  # paneles izq/der comparables
            ax.grid(alpha=0.3, which="both")
            ax.legend()
        fig.suptitle(f"{titulo_exp(x)} — mediana de {CONFIG['REPETICIONES']} reps", fontsize=13)
        fig.tight_layout()
        fig.savefig(os.path.join(dir_prelim, f"grafica_{x}.png"), dpi=140)
        plt.close(fig)

    # Resumen 4x2 con los 4 paneles clave (evita figura gigante de 7 filas)
    claves_resumen = ["busqueda_sin_build", "busqueda_con_build",
                      "rango_10pct" if "rango_10pct" in vistos else vistos[2],
                      "listar_ordenado"]
    fig, axes = plt.subplots(4, 2, figsize=(13, 14))
    for r, x in enumerate(claves_resumen):
        ylim = _ylim_comun(res, x, ORDENES)
        for c, orden in enumerate(ORDENES):
            ax = axes[r][c]
            _dibujar_panel_resumen(ax, x, orden, tamanos, res, xt, escala="log")
            if ylim is not None:
                ax.set_ylim(ylim)  # fila comparte escala en ambos ordenes
    fig.tight_layout()
    fig.savefig(os.path.join(dir_prelim, "resumen_escalabilidad.png"), dpi=130)
    plt.close(fig)


def _dibujar_panel_resumen(ax, x, orden, tamanos, res, xt, escala="log"):
    """Curvas + referencias de un panel del resumen. La escala la pone el llamador."""
    import math
    for s in ESTRUCTURAS:
        m, col = ESTILO[s]
        meds, yerr = _iqr_err(res[(x, orden, s)])
        ax.errorbar(tamanos, meds, yerr=yerr, fmt=m, color=col,
                    label=s, lw=2, capsize=2, elinewidth=1)
    if x == "busqueda_sin_build":
        # Referencias teoricas normalizadas al 1er punto de Lista nativa
        meds_lista = [d["median"] * 1000 for d in res[(x, orden, "Lista nativa")]]
        n0, y0 = tamanos[0], meds_lista[0]
        if y0 > 0 and n0 > 1:
            ax.plot(tamanos, [y0 * (n / n0) for n in tamanos],
                    "k--", alpha=0.35, label="O(N) referencia")
            ax.plot(tamanos, [y0 * (math.log(n) / math.log(n0)) for n in tamanos],
                    "k:", alpha=0.35, label="O(log N) referencia")
    ax.set_title(f"{titulo_exp(x)} - {orden}", fontsize=10)
    ax.set_xticks(tamanos)
    ax.set_xticklabels(xt, rotation=45, ha="right")
    ax.set_ylabel("ms (mediana+IQR)")
    if escala == "log":
        _eje_y_log_uniforme(ax)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)


def graficar_resumen_lineal(tamanos, res):
    """Resumen 4x2 gemelo en ESCALA LINEAL (sin ylim compartido).

    Complementa al resumen logaritmico: muestra las pendientes reales, pero
    cada panel autoescala (en lineal, compartir ylim aplastaria los paneles
    pequenos contra el ABB-ordenado de busqueda_con_build).
    """
    import os
    base = _base_dir()
    dir_prelim = os.path.join(base, "Resultados")
    os.makedirs(dir_prelim, exist_ok=True)
    xt = [f"{k}n" for k in CONFIG["MULTIPLOS"]]
    vistos = []
    for (x, _o, _s) in res:
        if x not in vistos:
            vistos.append(x)
    claves = ["busqueda_sin_build", "busqueda_con_build",
              "rango_10pct" if "rango_10pct" in vistos else vistos[2],
              "listar_ordenado"]
    fig, axes = plt.subplots(4, 2, figsize=(13, 14))
    for r, x in enumerate(claves):
        for c, orden in enumerate(ORDENES):
            _dibujar_panel_resumen(axes[r][c], x, orden, tamanos, res, xt, escala="lineal")
    fig.suptitle(f"Resumen lineal — mediana de {CONFIG['REPETICIONES']} reps", fontsize=13)
    fig.tight_layout()
    out = os.path.join(dir_prelim, "resumen_escalabilidad_lineal.png")
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Resumen lineal en: {out}")


def graficar_variando_M(n_fijo, Ms, resM):
    """Tiempo vs M con N fijo (datos desordenados, busqueda_sin_build). Eje X log."""
    import os
    base = _base_dir()
    dir_prelim = os.path.join(base, "Resultados")
    os.makedirs(dir_prelim, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for s in ESTRUCTURAS:
        m, c = ESTILO[s]
        meds, yerr = _iqr_err(resM[s])
        ax.errorbar(Ms, meds, yerr=yerr, fmt=m, color=c,
                    label=s, lw=2, capsize=3, elinewidth=1)
    ax.set_title(f"Busqueda sin construccion variando M (N fijo = {n_fijo}, desordenados)")
    ax.set_xlabel("M = numero de busquedas")
    ax.set_ylabel("Tiempo mediana, rango intercuartilico (ms)")
    ax.set_xscale("log")
    _eje_y_log_uniforme(ax)  # mismas decadas que el resto de figuras
    ax.set_xticks(Ms)
    ax.set_xticklabels([str(m) for m in Ms])
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    out = os.path.join(dir_prelim, "grafica_variando_M.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Grafica variando-M en: {out}")
    for s in ESTRUCTURAS:
        meds = [f"{d['median'] * 1000:.3f}" for d in resM[s]]
        print(f"  {s:13s} M={Ms} -> ms=[{', '.join(meds)}]")


def _base_dir():
    import os
    cwd = os.getcwd()
    if os.path.basename(cwd) == "Lab3" and os.path.isfile(os.path.join(cwd, "Experimentos.py")):
        return cwd
    candidato = os.path.join(cwd, "Lab3")
    if os.path.isdir(candidato):
        return candidato
    return os.path.dirname(os.path.abspath(__file__))


def exportar(tamanos, res):
    import os
    base = _base_dir()
    dir_prelim = os.path.join(base, "Resultados")
    dir_prueban = os.path.join(base, "PruebaN")
    os.makedirs(dir_prelim, exist_ok=True)
    os.makedirs(dir_prueban, exist_ok=True)
    with open(os.path.join(dir_prelim, "resultados.csv"), "w", newline="") as f:
        w = csv.writer(f)
        k0, k1 = CONFIG["MULTIPLOS"][0], CONFIG["MULTIPLOS"][-1]
        w.writerow(["experimento", "titulo", "orden", "estructura"]
                   + [f"N={n}_median_ms" for n in tamanos]
                   + [f"N={n}_stdev_ms" for n in tamanos]
                   + [f"factor_{k1}n/{k0}n_medianas"])
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
    with open(os.path.join(dir_prelim, "resultados_detalle.csv"), "w", newline="") as f:
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
    # muestras crudas por repeticion (para test de normalidad, Tarea 2).
    # NOTA de unidades: busqueda_* = ms por repeticion (repes con N_BUSQUEDAS
    # busquedas dentro); rango_*/listar = ms POR LLAMADA (total del batch / BATCH).
    with open(os.path.join(dir_prueban, "resultados_raw.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["experimento", "orden", "estructura", "N", "repeticion", "tiempo_ms"])
        for x in sorted({k[0] for k in res}):
            for o in ORDENES:
                for s in ESTRUCTURAS:
                    for n, d in zip(tamanos, res[(x, o, s)]):
                        for j, t in enumerate(d.get("raw", [])):
                            w.writerow([x, o, s, n, j, f"{t * 1000:.6f}"])
    print(f"CSV en: {dir_prelim} (resultados, detalle) y {dir_prueban} (raw)")


def imprimir_resumen(tamanos, res):
    k0, k1 = CONFIG["MULTIPLOS"][0], CONFIG["MULTIPLOS"][-1]
    print(f"\nFactor de crecimiento t({k1}n)/t({k0}n) sobre medianas + stdev en {k1}n:")
    for x in sorted({k[0] for k in res}):
        for o in ORDENES:
            for s in ESTRUCTURAS:
                ts = res[(x, o, s)]
                factor = ts[-1]["median"] / ts[0]["median"] if ts[0]["median"] > 0 else float("inf")
                print(f"  {x:22s} {o:13s} {s:13s} x{factor:7.1f}  "
                      f"(mediana{k1}n={ts[-1]['median'] * 1000:.2f}ms stdev={ts[-1]['stdev'] * 1000:.2f}ms)")


if __name__ == "__main__":
    print(f"CONFIG: {CONFIG}")
    tamanos, res = ejecutar()
    exportar(tamanos, res)
    graficar(tamanos, res)
    graficar_resumen_lineal(tamanos, res)
    n_fijo, Ms, resM = ejecutar_variando_M()
    graficar_variando_M(n_fijo, Ms, resM)
    imprimir_resumen(tamanos, res)
