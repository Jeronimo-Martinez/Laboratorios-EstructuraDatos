"""Test de normalidad (Shapiro-Wilk) sobre las repeticiones del benchmark.

Lee las muestras crudas que `Experimentos.exportar()` escribe en
`Lab3/PruebaN/resultados_raw.csv` (una fila por repeticion) y aplica
`scipy.stats.shapiro` a cada grupo (experimento, orden, estructura, N).

Salida: `Lab3/PruebaN/normalidad.csv` con columnas
  experimento, orden, estructura, N, n_muestras, p_value, es_normal

Donde `es_normal` es "si" (p>=0.05), "no" (p<0.05, se rechaza normalidad)
o "no evaluable" (varianza cero o n<3: shapiro no aplicable).

El resultado se reporta tal cual salga: si la mayoria rechaza normalidad,
respalda usar la mediana en las graficas; si no, tambien se reporta.
No se ajusta el test para forzar un resultado.

Uso:
    python Lab3/test_normalidad.py            # rutas por defecto
    python Lab3/test_normalidad.py --raw RUTA --out RUTA
"""

import argparse
import csv
import os
import sys


def resolver_rutas():
    aqui = os.path.dirname(os.path.abspath(__file__))
    return (os.path.join(aqui, "PruebaN", "resultados_raw.csv"),
            os.path.join(aqui, "PruebaN", "normalidad.csv"))


def cargar_grupos(path_raw):
    grupos = {}
    with open(path_raw, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["experimento"], row["orden"], row["estructura"], row["N"])
            grupos.setdefault(key, []).append(float(row["tiempo_ms"]))
    return grupos


def main():
    raw_def, out_def = resolver_rutas()
    ap = argparse.ArgumentParser(description="Shapiro-Wilk por grupo sobre resultados_raw.csv")
    ap.add_argument("--raw", default=raw_def)
    ap.add_argument("--out", default=out_def)
    ap.add_argument("--alfa", type=float, default=0.05)
    args = ap.parse_args()

    try:
        from scipy.stats import shapiro
    except ImportError:
        print("ERROR: scipy no instalado. Instala con: pip install scipy", file=sys.stderr)
        sys.exit(2)

    grupos = cargar_grupos(args.raw)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    filas = []
    for key in sorted(grupos, key=lambda k: (k[0], k[1], k[2], int(k[3]))):
        muestra = grupos[key]
        n = len(muestra)
        if n < 3 or len(set(muestra)) < 2:
            filas.append((*key, n, "", "no evaluable"))
            continue
        try:
            _, p = shapiro(muestra)
            filas.append((*key, n, f"{p:.6g}", "si" if p >= args.alfa else "no"))
        except Exception as e:  # shapiro puede fallar con datos degenerados
            filas.append((*key, n, "", f"no evaluable ({e})"))

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["experimento", "orden", "estructura", "N",
                    "n_muestras", "p_value", "es_normal"])
        w.writerows(filas)

    total = len(filas)
    evaluables = [r for r in filas if r[6] in ("si", "no")]
    rechazan = [r for r in filas if r[6] == "no"]
    no_eval = total - len(evaluables)
    if evaluables:
        pct = 100.0 * len(rechazan) / len(evaluables)
        print(f"{len(rechazan)} de {len(evaluables)} combinaciones evaluables "
              f"({pct:.1f}%) rechazan normalidad a p<{args.alfa} "
              f"({no_eval} no evaluables de {total} totales).")
    else:
        print(f"Sin grupos evaluables ({total} grupos no evaluables).")
    print(f"Detalle en: {args.out}")


if __name__ == "__main__":
    main()
