import sys
import time
import random

# Aumentar límite de recursión debido al comportamiento degenerado del ABB con datos ordenados
sys.setrecursionlimit(200000)

from ArboolABB import ArbolABB
from ArbolBplus import ArbolBPlus
from generar_estudiantes import generar_estudiantes


def realizar_pruebas():
    # ---------------------------------------------------------
    # 1. GENERACIÓN DE DATOS
    # ---------------------------------------------------------
    print("Generando datos de estudiantes...")
    estudiantes_aleatorios = generar_estudiantes(1000000, ordenado=False)
    estudiantes_ordenados = generar_estudiantes(10000, ordenado=True)

    # Extraer 100 IDs aleatorios para realizar las búsquedas sobre los mismos objetivos
    todos_los_ids = [e["id"] for e in estudiantes_aleatorios]
    ids_busqueda = random.sample(todos_los_ids, 1000)

    # ---------------------------------------------------------
    # 2. ESCENARIO A: IDs EN ORDEN ALEATORIO
    # ---------------------------------------------------------
    print("\n" + "="*50)
    print("  ESCENARIO 1: IDs EN ORDEN ALEATORIO")
    print("="*50)

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
    print("\n" + "="*50)
    print("  ESCENARIO 2: IDs YA ORDENADOS")
    print("="*50)

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
    #t_inicio = time.perf_counter()
    #for target_id in ids_busqueda:
    #    _ = arbol_abb_ordenado.buscar(target_id)
    #tiempo_abb_ordenado = time.perf_counter() - t_inicio


    # Búsqueda en Árbol B+
    t_inicio = time.perf_counter()
    for target_id in ids_busqueda:
        _ = arbol_bplus_ordenado.buscar(target_id)
    tiempo_bplus_ordenado = time.perf_counter() - t_inicio

    print(f"Lista Nativa : {tiempo_lista_ordenado:.6f} segundos")
    #(f"Árbol ABB    : {tiempo_abb_ordenado:.6f} segundos  <-- (Degenerado a O(N))")
    print(f"Árbol B+     : {tiempo_bplus_ordenado:.6f} segundos  <-- (Mantiene O(log N))")


if __name__ == "__main__":
    realizar_pruebas()