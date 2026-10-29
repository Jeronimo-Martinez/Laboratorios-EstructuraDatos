class Punto:
    __slots__ = ['x', 'y']  # Cambia la estructura interna de la clase de un dict a un array para optimizar memoria
    def __init__(self,x,y):
        self.x = x
        self.y = y

    def distancia_punto(self, punto):
        return (self.x - punto.x)**2 + (self.y - punto.y)**2

class Region:
    def __init__(self, origen, alto, ancho):
        self.origen = origen # Esquina inferior izq de la region
        self.alto = alto
        self.ancho = ancho

    def centro(self):
        return Punto(self.origen.x + self.ancho/2 , self.origen.y + self.alto/2)

    def contiene_punto(self, punto: Punto):
        max_x = self.origen.x + self.ancho
        max_y = self.origen.y + self.alto

        return self.origen.x <= punto.x <= max_x and self.origen.y <= punto.y <= max_y

    def distancia_min(self, punto: Punto):
        min_x = self.origen.x
        max_x = self.origen.x + self.ancho
        min_y = self.origen.y
        max_y = self.origen.y + self.alto

        dx = max(min_x - punto.x, 0, punto.x - max_x)
        dy = max(min_y - punto.y, 0, punto.y - max_y)

        return dx ** 2 + dy ** 2

    def cuadrante(self, punto: Punto):
        """Devuelve 0..3: bit 0 = x (1 si x >= centro_x), bit 1 = y (1 si y >= centro_y)."""
        c = self.centro()
        indice = 0
        if punto.x >= c.x:
            indice |= 1
        if punto.y >= c.y:
            indice |= 2
        return indice

    def intersecta_circulo(self, centro: Punto, radio_cuadrado):
        return self.distancia_min(centro) <= radio_cuadrado

class Nodo:
    __slots__  = ['region','puntos','hijos']
    def __init__(self,region):
        self.region = region
        self.puntos = []
        self.hijos = None # lista con los hijos ordenados segun la representacion por bits
                          # 00 down_izq, 01 down_der, 10 up_izq, 11 up_der.  Para 2D
    def es_hoja(self):
        return self.hijos is None

    def subdividir(self):
        r = self.region
        mitad_ancho = r.ancho / 2
        mitad_alto = r.alto / 2
        ox, oy = r.origen.x, r.origen.y
        self.hijos = [
            Nodo(Region(Punto(ox, oy), mitad_alto, mitad_ancho)),  # 0: abajo-izq
            Nodo(Region(Punto(ox + mitad_ancho, oy), mitad_alto, mitad_ancho)),  # 1: abajo-der
            Nodo(Region(Punto(ox, oy + mitad_alto), mitad_alto, mitad_ancho)),  # 2: arriba-izq
            Nodo(Region(Punto(ox + mitad_ancho, oy + mitad_alto), mitad_alto, mitad_ancho)),  # 3: arriba-der
        ]
        for p in self.puntos:
            self.hijos[r.cuadrante(p)].puntos.append(p)
        self.puntos = []

class QuadTree:
    def __init__(self,region : Region, capacidad = 4 ,profundidad_max=20):
        self.raiz = Nodo(region)
        self.capacidad = capacidad
        self.profundidad_max = profundidad_max
        # self.k = k

    def insertar(self, punto: Punto):
        if not self.raiz.region.contiene_punto(punto):
            return False
        self._insertar(self.raiz, punto,0)
        return True

    def _insertar(self,nodo,punto:Punto , profundidad):
        if not nodo.es_hoja():
            hijo  =  nodo.hijos[nodo.region.cuadrante(punto)]
            self._insertar(hijo,punto,profundidad +1)
        elif len(self.raiz.puntos) < self.capacidad or profundidad > self.profundidad_max:
            nodo.puntos.append(punto)
        else:
            nodo.subdividir()
            self._insertar(nodo,punto,profundidad)

    def buscar_radio(self,centro,radio):
        r = radio**2
        resultados = []
        self._buscar_radio(self.raiz, centro, r, resultados)
        return resultados

    def _buscar_radio(self,nodo,centro, radio_cuadrado, resultados):
        if nodo.region.distancia_min(centro) > radio_cuadrado:
            return
        if nodo.es_hoja():
            for p in nodo.puntos:
                if centro.distancia_punto(p) <= radio_cuadrado:
                    resultados.append(p)
        else:
            for hijo in nodo.hijos:
                self._buscar_radio(hijo, centro, radio_cuadrado, resultados)

    def buscar_mas_cercanos(self,punto: Punto, k=1): #k: cantidad de vecinos más cercanos
        if k <= 0:
            return []
        candidatos = []  # lista de (distancia_cuadrada, punto), ordenada de menor a mayor
        self._buscar_mas_cercanos(self.raiz, punto, k, candidatos)
        return [p for d, p in candidatos]


    def _buscar_mas_cercanos(self,nodo,punto, k , candidatos):
        limite = candidatos[-1][0] if len(candidatos) == k else float('inf')
        if nodo.region.distancia_min(punto) > limite:
            return

        if nodo.es_hoja:
            for p in nodo.puntos:
                d = punto.distancia_punto(p)
                if len(candidatos) < k or d < candidatos[-1][0]:
                    candidatos.append((d, p))
                    candidatos.sort(key=lambda c: c[0]) #ordenar candidatos por c:distancia
                    if len(candidatos) > k:
                        candidatos.pop()  # descartar el peor
        else:
            hijos = sorted(nodo.hijos, key=lambda h: h.region.distancia_min(punto)) #lista con los hijos ordenados por distancia
            for hijo in hijos:
                self._buscar_mas_cercanos(hijo, punto, k, candidatos)

def radio_fuerza_bruta(puntos, punto: Punto, radio):
    radio_cuadrado = radio ** 2
    return [p for p in puntos if punto.distancia_punto(p) <= radio_cuadrado]


def vecinos_fuerza_bruta(puntos, punto: Punto, k=1):
    if k <= 0:
        return []
    candidatos = []   # lista de (distancia_cuadrada, punto), ordenada de menor a mayor
    for p in puntos:
        d = punto.distancia_punto(p)
        if len(candidatos) < k or d < candidatos[-1][0]:
            candidatos.append((d, p))
            candidatos.sort(key=lambda c: c[0])
            if len(candidatos) > k:
                candidatos.pop()
    return [p for d, p in candidatos]