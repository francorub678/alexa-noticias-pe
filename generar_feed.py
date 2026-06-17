#!/usr/bin/env python3
"""
Genera el feed.json para tu Flash Briefing de Alexa: "Top de noticias Perú".

Flujo:
  1. Lee los RSS de medios peruanos definidos en FUENTES.
  2. Deduplica titulares parecidos y selecciona el TOP_N más recientes.
  3. (Opcional) Resume cada noticia con Claude para que suene natural leída en voz alta.
  4. Escribe docs/feed.json con el formato que exige Amazon Flash Briefing.

Uso:
  python generar_feed.py            # genera el feed
  python generar_feed.py --sin-ia   # sin resumir con IA (usa la bajada del RSS)

Requiere: pip install -r requirements.txt
Variable de entorno (si usas IA): ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser

# ---------------------------------------------------------------------------
# CONFIGURACIÓN — ajusta a tu gusto
# ---------------------------------------------------------------------------

# Fuentes RSS de medios peruanos. (orden = prioridad para desempates)
# ⚠️ VERIFICA estas URLs: los medios cambian sus RSS. Si una falla, el script
# la salta con un warning y sigue con las demás. Comenta/añade las que quieras.
FUENTES = [
    {"nombre": "Andina",       "url": "https://andina.pe/agencia/rss.aspx"},
    {"nombre": "RPP",          "url": "https://rpp.pe/feed"},
    {"nombre": "El Comercio",  "url": "https://elcomercio.pe/feed/"},
    {"nombre": "Gestión",      "url": "https://gestion.pe/arc/outboundfeeds/rss/?outputType=xml"},
    {"nombre": "Infobae Perú", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/peru/?outputType=xml"},
]

# Muchos medios bloquean el User-Agent por defecto de feedparser → usamos uno de navegador.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

TOP_N = 5  # cuántas noticias entran a tu boletín diario

# Modelo de Claude para resumir (Haiku 4.5: rápido y barato para titulares).
MODELO_IA = "claude-haiku-4-5-20251001"

SALIDA = Path(__file__).parent / "docs" / "feed.json"

# ---------------------------------------------------------------------------


def limpiar_html(texto: str) -> str:
    """Quita etiquetas HTML y espacios sobrantes de las bajadas del RSS."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def clave_dedup(titulo: str) -> str:
    """Clave normalizada para detectar titulares duplicados entre medios."""
    t = titulo.lower()
    t = re.sub(r"[^a-záéíóúñü0-9 ]", "", t)
    palabras = [p for p in t.split() if len(p) > 3]
    return " ".join(sorted(palabras[:6]))


def recolectar_noticias():
    """Lee todas las fuentes y devuelve una lista de noticias ordenadas por fecha."""
    noticias = []
    vistos = set()

    for fuente in FUENTES:
        try:
            d = feedparser.parse(fuente["url"], agent=USER_AGENT)
            if d.bozo and not d.entries:
                print(f"  ⚠️  {fuente['nombre']}: feed ilegible o vacío ({fuente['url']})",
                      file=sys.stderr)
                continue
            print(f"  ✓ {fuente['nombre']}: {len(d.entries)} entradas")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️  {fuente['nombre']}: error al leer ({e})", file=sys.stderr)
            continue

        for entry in d.entries:
            titulo = (entry.get("title") or "").strip()
            if not titulo:
                continue
            clave = clave_dedup(titulo)
            if clave in vistos:
                continue
            vistos.add(clave)

            # Fecha de publicación (para ordenar). Si no hay, va al final.
            fecha = None
            for campo in ("published_parsed", "updated_parsed"):
                if entry.get(campo):
                    fecha = datetime(*entry[campo][:6], tzinfo=timezone.utc)
                    break

            noticias.append({
                "fuente": fuente["nombre"],
                "titulo": titulo,
                "bajada": limpiar_html(entry.get("summary", "")),
                "url": entry.get("link", ""),
                "fecha": fecha,
            })

    # Más recientes primero; las sin fecha al final.
    noticias.sort(key=lambda n: n["fecha"] or datetime.min.replace(tzinfo=timezone.utc),
                  reverse=True)
    return noticias


def resumir_con_ia(noticias):
    """Reescribe cada noticia en 1 frase clara para escuchar. Modifica in-place."""
    try:
        from anthropic import Anthropic
    except ImportError:
        print("  ⚠️  paquete 'anthropic' no instalado; usando bajadas crudas.",
              file=sys.stderr)
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("  ⚠️  falta ANTHROPIC_API_KEY; usando bajadas crudas.", file=sys.stderr)
        return

    cliente = Anthropic()
    for n in noticias:
        contexto = f"Titular: {n['titulo']}\nBajada: {n['bajada'][:500]}"
        try:
            resp = cliente.messages.create(
                model=MODELO_IA,
                max_tokens=120,
                messages=[{
                    "role": "user",
                    "content": (
                        "Resume esta noticia peruana en UNA frase clara para escuchar en "
                        "voz alta por un parlante. Máximo 30 palabras, español neutro, sin "
                        "emojis, sin comillas, sin decir 'la noticia'. Solo la frase.\n\n"
                        + contexto
                    ),
                }],
            )
            n["resumen"] = resp.content[0].text.strip()
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️  IA falló para un titular ({e}); uso la bajada.", file=sys.stderr)
            n["resumen"] = n["bajada"] or n["titulo"]


def construir_feed(noticias):
    """Arma la lista de items en el formato Flash Briefing (text feed)."""
    ahora = datetime.now(timezone.utc)
    fecha_es = ahora.strftime("%d/%m")
    items = []

    for i, n in enumerate(noticias):
        texto = n.get("resumen") or n["bajada"] or n["titulo"]
        # Alexa lee items en orden de updateDate (más reciente primero):
        # le restamos segundos a cada item para forzar TU orden de prioridad.
        update = (ahora - timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%S.0Z")
        items.append({
            "uid": f"top-pe-{ahora.strftime('%Y%m%d')}-{i}",
            "updateDate": update,
            "titleText": f"Top Perú {fecha_es} · {n['fuente']}",
            "mainText": texto[:4400],
            "redirectionUrl": n["url"] or "https://www.andina.pe",
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-ia", action="store_true",
                        help="No resumir con Claude; usar la bajada del RSS.")
    args = parser.parse_args()

    print("📰 Recolectando noticias peruanas...")
    noticias = recolectar_noticias()
    if not noticias:
        print("❌ No se obtuvieron noticias de ninguna fuente. Revisa las URLs en FUENTES.",
              file=sys.stderr)
        sys.exit(1)

    noticias = noticias[:TOP_N]
    print(f"🏆 Top {len(noticias)} seleccionado.")

    if not args.sin_ia:
        print("🤖 Resumiendo con Claude...")
        resumir_con_ia(noticias)

    feed = construir_feed(noticias)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Feed escrito en {SALIDA} ({len(feed)} items).")
    print("\nVista previa de tu boletín:")
    for it in feed:
        print(f"  • {it['titleText']}: {it['mainText'][:90]}...")


if __name__ == "__main__":
    main()
