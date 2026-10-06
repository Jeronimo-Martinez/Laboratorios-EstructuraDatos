class NodoABB:
    def __init__(self, estudiante):
        self.estudiante = estudiante  # Diccionario con los datos
        self.id = estudiante["id"]  # Clave para comparar
        self.izquierdo = None
        self.derecho = None


class ArbolABB:
    def __init__(self):
        self.raiz = None

    def insertar(self, estudiante):
        nuevo_nodo = NodoABB(estudiante)
        if self.raiz is None:
            self.raiz = nuevo_nodo
        else:
            self._insertar_recursivo(self.raiz, nuevo_nodo) #baja el arbol recursivamente hasta encontrar una posición valida

    def _insertar_recursivo(self, actual, nuevo_nodo):
        if nuevo_nodo.id < actual.id:
            if actual.izquierdo is None:
                actual.izquierdo = nuevo_nodo
            else:
                self._insertar_recursivo(actual.izquierdo, nuevo_nodo)
        elif nuevo_nodo.id > actual.id:
            if actual.derecho is None:
                actual.derecho = nuevo_nodo
            else:
                self._insertar_recursivo(actual.derecho, nuevo_nodo)

    def buscar(self, id_estudiante):
        return self._buscar_recursivo(self.raiz, id_estudiante)

    def _buscar_recursivo(self, actual, id_estudiante):
        if actual is None or actual.id == id_estudiante:
            return actual.estudiante if actual else None

        if id_estudiante < actual.id:
            return self._buscar_recursivo(actual.izquierdo, id_estudiante)
        else:
            return self._buscar_recursivo(actual.derecho, id_estudiante)

    def listar_en_orden(self):
        # Retorna todos los estudiantes ordenados por ID (Recorrido Inorden) der -> raiz -> izq
        estudiantes_ordenados = []
        self._inorden_recursivo(self.raiz, estudiantes_ordenados)
        return estudiantes_ordenados

    def _inorden_recursivo(self, actual, resultado):
        if actual is not None:
            self._inorden_recursivo(actual.izquierdo, resultado)
            resultado.append(actual.estudiante)
            self._inorden_recursivo(actual.derecho, resultado)

    def buscar_rango(self, id_min, id_max):
        # Retorna los estudiantes con id_min <= id <= id_max, ordenados por ID.

        resultado = []
        self._rango_recursivo(self.raiz, id_min, id_max, resultado)
        return resultado

    def _rango_recursivo(self, actual, id_min, id_max, resultado):
        if actual is None:
            return
        if id_min < actual.id:
            self._rango_recursivo(actual.izquierdo, id_min, id_max, resultado)
        if id_min <= actual.id <= id_max:
            resultado.append(actual.estudiante)
        if actual.id < id_max:
            self._rango_recursivo(actual.derecho, id_min, id_max, resultado)