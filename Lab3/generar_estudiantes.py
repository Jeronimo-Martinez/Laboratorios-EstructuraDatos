import random

# Nombres y apellidos para generar combinaciones aleatorias
NOMBRES = ["Ana", "Carlos", "María", "Juan", "Sofía", "Luis", "Elena", "Pedro", "Lucía", "Diego",
           "Valentina", "Mateo", "Camila", "Javier", "Isabella", "Gabriel", "Valeria", "Fernando"]
APELLIDOS = ["García", "Rodríguez", "López", "González", "Pérez", "Sánchez", "Martínez", "Romero"]


def generar_estudiantes(cantidad=10000, ordenado=False):
    """
    Genera una lista de estudiantes con estructura diccionarios.
    :param cantidad: Número total de estudiantes a generar (por defecto 10000).
    :param ordenado: True para IDs secuenciales, False para IDs en orden aleatorio.
    """
    # Genera IDs únicos entre 1000 y 1000 + cantidad
    ids = list(range(1001, 1001 + cantidad))

    if not ordenado:
        random.shuffle(ids)  # Mezcla los IDs aleatoriamente

    estudiantes = []
    for i in range(cantidad):
        nombre_completo = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
        edad = random.randint(18, 28)
        promedio = round(random.uniform(5.0, 10.0), 1)

        estudiantes.append({
            "id": ids[i],
            "nombre": nombre_completo,
            "edad": edad,
            "promedio": promedio
        })

    return estudiantes


