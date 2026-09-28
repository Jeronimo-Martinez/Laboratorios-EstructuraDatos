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
            self._insertar_recursivo(self.raiz, nuevo_nodo)

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
        """Busca un estudiante por su ID en O(log N) promedio"""
        return self._buscar_recursivo(self.raiz, id_estudiante)

    def _buscar_recursivo(self, actual, id_estudiante):
        if actual is None or actual.id == id_estudiante:
            return actual.estudiante if actual else None

        if id_estudiante < actual.id:
            return self._buscar_recursivo(actual.izquierdo, id_estudiante)
        else:
            return self._buscar_recursivo(actual.derecho, id_estudiante)

    def listar_en_orden(self):
        """Retorna todos los estudiantes ordenados por ID (Recorrido Inorden)"""
        estudiantes_ordenados = []
        self._inorden_recursivo(self.raiz, estudiantes_ordenados)
        return estudiantes_ordenados

    def _inorden_recursivo(self, actual, resultado):
        if actual is not None:
            self._inorden_recursivo(actual.izquierdo, resultado)
            resultado.append(actual.estudiante)
            self._inorden_recursivo(actual.derecho, resultado)

