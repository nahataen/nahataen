#!/usr/bin/env python3
"""Particulas de commits - animacion SVG 100% propia para el perfil.

Lee el calendario real de contribuciones del usuario con la API de GitHub
y genera un SVG animado (SMIL, sin JavaScript): particulas que nacen en
los dias con mas actividad y flotan hacia arriba desvaneciendose.

Uso en local (prueba con datos falsos, sin token):
    MOCK=1 python generador/genera_invasor.py

Uso en Actions (datos reales):
    GITHUB_TOKEN=... GITHUB_USER=nahataen python generador/genera_invasor.py

Genera: dist/particulas.svg (claro) y dist/particulas-dark.svg (oscuro).
"""

import json
import os
import random
import urllib.request

USER = os.environ.get("GITHUB_USER", "nahataen")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MOCK = os.environ.get("MOCK", "")

CELL, GAP = 11, 4
STEP = CELL + GAP
TOP_H, LABEL_H, FOOT_H, PAD = 30, 16, 30, 12

MESES = ["", "ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

PALETAS = {
    "claro": {"fondo": "#FFFFFF", "vacio": "#EAEEF2",
              "celdas": ["#9EC1DB", "#39C5CF", "#2F81F7", "#0969DA"],
              "tinta": "#24292F", "tenue": "#57606A",
              "particula": "#2F81F7", "particula2": "#39C5CF",
              "estrella": "#D0D7DE"},
    "oscuro": {"fondo": "#0D1117", "vacio": "#161B22",
               "celdas": ["#1B3A5C", "#2F81F7", "#39C5CF", "#7DF9FF"],
               "tinta": "#E6EDF3", "tenue": "#7D8590",
               "particula": "#39C5CF", "particula2": "#2F81F7",
               "estrella": "#30363D"},
}


def datos_reales():
    """Baja las contribuciones publicas del ultimo anio via GraphQL."""
    consulta = {
        "query": ("query($login:String!){user(login:$login){"
                  "contributionsCollection{"
                  "contributionCalendar{totalContributions "
                  "weeks{contributionDays{"
                  "contributionCount date}}}}}}"),
        "variables": {"login": USER},
    }
    peticion = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(consulta).encode(),
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json",
                 "User-Agent": "particulas-de-commits"},
    )
    respuesta = json.load(urllib.request.urlopen(peticion, timeout=30))
    if "errors" in respuesta:
        raise RuntimeError("GitHub API: %s" % respuesta["errors"])
    calendario = (respuesta["data"]["user"]
                  ["contributionsCollection"]["contributionCalendar"])
    semanas = [[d["contributionCount"] for d in s["contributionDays"]]
               for s in calendario["weeks"]]
    fechas = [[d["date"] for d in s["contributionDays"]]
              for s in calendario["weeks"]]
    return semanas, fechas, calendario["totalContributions"]


def datos_falsos():
    """Datos deterministas solo para probar el dibujo en local."""
    azar = random.Random(42)
    semanas = [[max(0, int(azar.gauss(4, 5))) for _ in range(7)]
               for _ in range(53)]
    fechas = [["2025-01-01"] * 7 for _ in range(53)]
    return semanas, fechas, 1337


def nivel(cuenta, tope):
    if cuenta <= 0 or tope <= 0:
        return -1
    if cuenta >= tope * 0.75:
        return 3
    if cuenta >= tope * 0.50:
        return 2
    if cuenta >= tope * 0.25:
        return 1
    return 0


def fmt(numero):
    texto = "%.4f" % numero
    return texto.rstrip("0").rstrip(".") or "0"


def construir_svg(semanas, fechas, total, paleta):
    ncols = len(semanas)
    ancho_rejilla = ncols * STEP - GAP
    alto_rejilla = 7 * STEP - GAP
    ancho = PAD * 2 + ancho_rejilla
    rejilla_y = PAD + TOP_H + LABEL_H
    alto = rejilla_y + alto_rejilla + FOOT_H + PAD

    tope = max((c for s in semanas for c in s), default=0)
    partes = []
    push = partes.append
    push('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="monospace">' % (ancho, alto, ancho, alto))
    push('<rect width="100%%" height="100%%" fill="%s" rx="10"/>' % paleta["fondo"])

    # Estrellas de fondo con parpadeo.
    azar = random.Random(7)
    for i in range(45):
        x = round(azar.uniform(PAD, ancho - PAD), 1)
        y = round(azar.uniform(8, rejilla_y + alto_rejilla), 1)
        r = round(azar.uniform(0.8, 1.6), 1)
        dur = round(azar.uniform(1.6, 3.6), 1)
        push('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="0.5">'
             '<animate attributeName="opacity" values="0.15;0.8;0.15" '
             'dur="%ss" begin="%ss" repeatCount="indefinite"/></circle>'
             % (x, y, r, paleta["estrella"], dur, fmt((i % 7) * 0.3)))

    # Etiquetas de mes.
    mes_previo = 0
    for col, dias in enumerate(fechas):
        try:
            mes = int(dias[0][5:7])
        except (IndexError, ValueError):
            continue
        if mes != mes_previo:
            mes_previo = mes
            push('<text x="%d" y="%d" font-size="9" fill="%s">%s</text>'
                 % (PAD + col * STEP, PAD + TOP_H + 12,
                    paleta["tenue"], MESES[mes]))

    # Celdas de contribuciones.
    celdas = []
    for col, dias in enumerate(semanas):
        for fila in range(7):
            cuenta = dias[fila] if fila < len(dias) else 0
            niv = nivel(cuenta, tope)
            color = paleta["vacio"] if niv < 0 else paleta["celdas"][niv]
            x = PAD + col * STEP
            y = rejilla_y + fila * STEP
            celdas.append((col, fila, cuenta, x, y))
            push('<rect x="%d" y="%d" width="%d" height="%d" rx="2.5" fill="%s"/>'
                 % (x, y, CELL, CELL, color))

    # Dias con mas actividad: pulso suave.
    candidatas = sorted([c for c in celdas if c[2] > 0],
                        key=lambda c: -c[2])
    if not candidatas:
        candidatas = [celdas[i * len(celdas) // 12] for i in range(12)]
    destacadas, usadas = [], []
    for cand in candidatas:
        if all(abs(cand[0] - u) >= 3 for u in usadas):
            destacadas.append(cand)
            usadas.append(cand[0])
        if len(destacadas) == 12:
            break
    while len(destacadas) < 12:
        destacadas.append(celdas[len(destacadas) * len(celdas) // 12])
    for i, (_, _, _, x, y) in enumerate(destacadas):
        push('<rect x="%d" y="%d" width="%d" height="%d" rx="2.5" '
             'fill="none" stroke="%s" stroke-width="1.5" opacity="0">'
             '<animate attributeName="opacity" values="0;0.9;0" '
             'keyTimes="0;0.5;1" dur="%ss" begin="%ss" '
             'repeatCount="indefinite"/></rect>'
             % (x - 2, y - 2, CELL + 4, CELL + 4, paleta["particula"],
                fmt(2.4 + (i % 4) * 0.5), fmt(i * 0.35)))

    # Particulas: nacen en dias activos y flotan hacia arriba.
    fuentes = [c for c in celdas if c[2] > 0] or celdas
    azar = random.Random(11)
    for i in range(26):
        col, _, _, x, y = azar.choice(fuentes)
        x0 = x + CELL / 2
        y0 = y + CELL / 2
        subida = round(azar.uniform(40, 110), 1)
        deriva = round(azar.uniform(-24, 24), 1)
        dur = round(azar.uniform(3.0, 6.0), 1)
        r = round(azar.uniform(1.5, 3.0), 1)
        color = paleta["particula"] if i % 2 == 0 else paleta["particula2"]
        push('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="0">'
             '<animate attributeName="cy" values="%s;%s" '
             'dur="%ss" begin="%ss" repeatCount="indefinite"/>'
             '<animate attributeName="cx" values="%s;%s" '
             'dur="%ss" begin="%ss" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values="0;0.95;0" '
             'keyTimes="0;0.25;1" dur="%ss" begin="%ss" '
             'repeatCount="indefinite"/></circle>'
             % (fmt(x0), fmt(y0), r, color,
                fmt(y0), fmt(y0 - subida), dur, fmt(i * 0.35),
                fmt(x0), fmt(x0 + deriva), dur, fmt(i * 0.35),
                dur, fmt(i * 0.35)))

    # Pie con el total real.
    pie_y = rejilla_y + alto_rejilla + 22
    push('<text x="%d" y="%d" font-size="13" font-weight="bold" fill="%s">'
         'CONTRIBUCIONES: %d</text>' % (PAD, pie_y, paleta["tinta"], total))
    push("</svg>")
    return "\n".join(partes)


def main():
    if MOCK or not TOKEN:
        semanas, fechas, total = datos_falsos()
        print("modo prueba con datos falsos")
    else:
        semanas, fechas, total = datos_reales()
        print("datos reales de %s: %d contribuciones" % (USER, total))
    os.makedirs("dist", exist_ok=True)
    for nombre, tema in (("particulas.svg", "claro"),
                         ("particulas-dark.svg", "oscuro")):
        svg = construir_svg(semanas, fechas, total, PALETAS[tema])
        with open(os.path.join("dist", nombre), "w", encoding="utf-8") as archivo:
            archivo.write(svg)
        print("generado dist/%s (%d bytes)" % (nombre, len(svg.encode("utf-8"))))


if __name__ == "__main__":
    main()
