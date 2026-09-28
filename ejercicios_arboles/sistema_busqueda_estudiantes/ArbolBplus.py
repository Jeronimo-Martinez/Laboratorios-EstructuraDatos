import bisect
class NodoBPlus:
    def __init__(self, es_hoja=False):
        self.es_hoja = es_hoja
        self.claves = []  # Lista de IDs (solo llaves para navegación)
        self.punteros = []  # Nodos hijos (si es interno) OR Punteros a Datos (si es hoja)
        self.siguiente = None  # Puntero al siguiente nodo hoja enlazado


class ArbolBPlus:
    def __init__(self, t=3):
        self.raiz = NodoBPlus(es_hoja=True)
        self.t = t  # Grado mínimo

    def buscar(self, id_estudiante):
        """Devuelve el PUNTERO al registro del estudiante, no el nodo."""
        actual = self.raiz

        # 1. Navegar por los nodos internos usando bisect_right en C
        while not actual.es_hoja:
            i = bisect.bisect_right(actual.claves, id_estudiante)
            actual = actual.punteros[i]

        # 2. En la hoja, ubicar la clave en O(log K) con bisect_left
        i = bisect.bisect_left(actual.claves, id_estudiante)
        if i < len(actual.claves) and actual.claves[i] == id_estudiante:
            return actual.punteros[i]  # Devuelve la referencia al dato externo

        return None

    def insertar(self, id_estudiante, puntero_dato):
        """
        :param id_estudiante: La clave de búsqueda (int)
        :param puntero_dato: Referencia en memoria/puntero al registro del estudiante
        """
        raiz = self.raiz
        if len(raiz.claves) == (2 * self.t - 1):
            nueva_raiz = NodoBPlus(es_hoja=False)
            nueva_raiz.punteros.append(self.raiz)
            self._dividir_hijo(nueva_raiz, 0)
            self.raiz = nueva_raiz

        self._insertar_no_lleno(self.raiz, id_estudiante, puntero_dato)

    def _dividir_hijo(self, padre, i):
        t = self.t
        hijo = padre.punteros[i]
        nuevo_nodo = NodoBPlus(es_hoja=hijo.es_hoja)
        mid = t - 1

        if hijo.es_hoja:
            # En hojas: divide claves y sus correspondientes PUNTEROS a datos
            nuevo_nodo.claves = hijo.claves[mid:]
            nuevo_nodo.punteros = hijo.punteros[mid:]
            hijo.claves = hijo.claves[:mid]
            hijo.punteros = hijo.punteros[:mid]

            # Enlace de lista secuencial entre hojas
            nuevo_nodo.siguiente = hijo.siguiente
            hijo.siguiente = nuevo_nodo

            padre.claves.insert(i, nuevo_nodo.claves[0])
            padre.punteros.insert(i + 1, nuevo_nodo)
        else:
            # En nodos internos: divide claves y PUNTEROS a otros nodos hijos
            clave_promovida = hijo.claves[mid]
            nuevo_nodo.claves = hijo.claves[mid + 1:]
            nuevo_nodo.punteros = hijo.punteros[mid + 1:]
            hijo.claves = hijo.claves[:mid]
            hijo.punteros = hijo.punteros[:mid + 1]

            padre.claves.insert(i, clave_promovida)
            padre.punteros.insert(i + 1, nuevo_nodo)

    def _insertar_no_lleno(self, nodo, id_estudiante, puntero_dato):
        if nodo.es_hoja:
            # bisect_left determina el índice de inserción ordenada directamente
            i = bisect.bisect_left(nodo.claves, id_estudiante)
            nodo.claves.insert(i, id_estudiante)
            nodo.punteros.insert(i, puntero_dato)  # Inserta únicamente el puntero al registro
        else:
            # bisect_right determina instantáneamente el nodo hijo descendiente
            i = bisect.bisect_right(nodo.claves, id_estudiante)

            if len(nodo.punteros[i].claves) == (2 * self.t - 1):
                self._dividir_hijo(nodo, i)
                if id_estudiante > nodo.claves[i]:
                    i += 1
            self._insertar_no_lleno(nodo.punteros[i], id_estudiante, puntero_dato)

    def listar_en_orden(self):
        """Retorna una lista con todos los PUNTEROS ordenados por ID."""
        actual = self.raiz
        while not actual.es_hoja:
            actual = actual.punteros[0]

        punteros_datos = []
        while actual:
            punteros_datos.extend(actual.punteros)
            actual = actual.siguiente
        return punteros_datos