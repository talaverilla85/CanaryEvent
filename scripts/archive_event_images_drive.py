#!/usr/bin/env python3
"""Archiva en Drive imágenes expresamente autorizadas desde el catálogo D'Parranda.

No modifica el catálogo público ni concede derechos de reutilización en redes.
La columna L del inventario (Autorizado) es una condición obligatoria.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
import unicodedata
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "public" / "events.json"
SPREADSHEET_ID = "1g9Ac8VKxz1j8RULFW9VFjNwHkLqHxDV0dOca_0Q_E4g"
SHEET_NAME = "Imágenes verificadas"
ORIGINALS_ROOT_ID = "1FozTNO-dCQbV7VlAWRScrYqefS_7dB2R"
SCOPES = ["https://www.googleapis.com/auth/drive",
          "https://www.googleapis.com/auth/spreadsheets"]
UA = "DParranda-ImageArchive/1.0 (+https://dparranda.es)"
MAX_BYTES = 15 * 1024 * 1024
CATEGORIES = {
    "musica": "Conciertos y espectáculos",
    "teatro": "Conciertos y espectáculos",
    "cine": "Conciertos y espectáculos",
    "familia": "Familia e infantil",
    "infantil": "Familia e infantil",
    "deporte": "Deporte y naturaleza",
    "naturaleza": "Deporte y naturaleza",
    "mercadillos": "Mercadillos y ferias",
    "mercadillo": "Mercadillos y ferias",
    "feria": "Mercadillos y ferias",
    "cultura": "Fiestas populares y cultura",
    "fiestas": "Fiestas populares y cultura",
}
CHRISTMAS_RE = re.compile(
    r"\b(navidad|navideñ\w*|pap[aá]\s*noel|reyes\s*magos|"
    r"encendido\s*(de\s*)?(las\s*)?luces|bel[eé]n)\b", re.I
)
MIMES = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
    "GIF": ("image/gif", ".gif"),
    "AVIF": ("image/avif", ".avif"),
}


def slug(value: str, limit: int = 75) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", ascii_text).strip("-")[:limit] or "evento"


def authorized(value: str) -> bool:
    return str(value).strip().casefold() == "autorizado"


def discover(catalog: dict, today: date | None = None) -> dict[str, dict]:
    """Agrupa por URL sin perder las relaciones entre eventos y un cartel común."""
    today = today or date.today()
    images = {}
    for e in catalog.get("events", []):
        url = str(e.get("image_url") or "").strip()
        if not url or e.get("image_status") != "official_remote":
            continue
        until = str(e.get("end") or e.get("start") or "")[:10]
        try:
            if until and date.fromisoformat(until) < today:
                continue
        except ValueError:
            continue
        entry = images.setdefault(url, {
            "url": url, "id": str(e.get("id", "")),
            "title": str(e.get("title") or "Evento"),
            "municipality": str(e.get("municipality") or "Sin municipio"),
            "start": str(e.get("start") or "")[:10],
            "category": str(e.get("category") or "otros").lower(),
            "source_url": str(e.get("source_url") or ""),
            "source_name": str(e.get("source_name") or ""),
            "image_origin": str(e.get("image_origin") or ""),
            "event_ids": set(),
        })
        entry["event_ids"].add(str(e.get("id", "")))
    return images


def valid_https(url: str) -> str:
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Solo se permiten imágenes HTTPS públicas")
    if len(url) > 1600 or p.port not in (None, 443):
        raise ValueError("URL fuera de límites")
    host = p.hostname.lower().strip(".")
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Dominio no público")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("No se permiten direcciones IP directas")
    return host


def public_dns(host: str) -> None:
    """Impide que una URL del inventario resuelva a una red interna."""
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError("El origen no resuelve exclusivamente a IP públicas")


def robots_allowed(url: str, host: str) -> bool:
    robots = requests.get(
        "https://" + host + "/robots.txt",
        headers={"User-Agent": UA}, timeout=(5, 12), allow_redirects=False
    )
    if robots.status_code in (401, 403):
        return False
    if robots.status_code == 404:
        return True
    if robots.status_code != 200:
        raise ValueError("No se pudo verificar robots.txt: " + str(robots.status_code))
    parser = RobotFileParser()
    parser.parse(robots.text.splitlines())
    return parser.can_fetch(UA, url)


def download_image(url: str) -> tuple[bytes, str, str]:
    host = valid_https(url)
    public_dns(host)
    if not robots_allowed(url, host):
        raise ValueError("El origen no permite la descarga en robots.txt")
    result = requests.get(
        url, headers={"User-Agent": UA, "Accept": "image/*"},
        timeout=(8, 25), stream=True, allow_redirects=False
    )
    try:
        if result.status_code != 200:
            raise ValueError("HTTP " + str(result.status_code) + " (no se siguen redirecciones)")
        if not result.headers.get("Content-Type", "").lower().startswith("image/"):
            raise ValueError("La respuesta no es una imagen")
        chunks, total = [], 0
        for chunk in result.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("La imagen supera 15 MB")
            chunks.append(chunk)
        raw = b"".join(chunks)
    finally:
        result.close()
    try:
        with Image.open(BytesIO(raw)) as pic:
            fmt = pic.format
            pic.verify()
    except (UnidentifiedImageError, OSError, ValueError) as ex:
        raise ValueError("Formato o imagen no válido") from ex
    if fmt not in MIMES:
        raise ValueError("Formato no admitido: " + str(fmt))
    return raw, *MIMES[fmt]


def services():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    secret = os.environ.get("DPARRANDA_GOOGLE_DRIVE_OAUTH_JSON", "").strip()
    if not secret:
        raise RuntimeError("Falta el secreto DPARRANDA_GOOGLE_DRIVE_OAUTH_JSON")
    info = json.loads(secret)
    creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return (
        build("drive", "v3", credentials=creds, cache_discovery=False),
        build("sheets", "v4", credentials=creds, cache_discovery=False),
    )


def find_or_create_folder(drive, parent: str, name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace("'", "\\'")
    result = drive.files().list(
        q=f"trashed = false and mimeType = 'application/vnd.google-apps.folder' and "
          f"name = '{escaped}' and '{parent}' in parents",
        fields="nextPageToken,files(id,name)", pageSize=100
    ).execute(num_retries=3)
    found = result.get("files", [])
    if found:
        return found[0]["id"]
    created = drive.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder",
              "parents": [parent]}, fields="id"
    ).execute(num_retries=3)
    return created["id"]


def destination(drive, e: dict, cache: dict[tuple[str, str], str]) -> str:
    def folder(parent, name):
        key = (parent, name)
        if key not in cache:
            cache[key] = find_or_create_folder(drive, parent, name)
        return cache[key]

    year = e["start"][:4] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["start"]) else str(date.today().year)
    base = folder(ORIGINALS_ROOT_ID, year)
    base = folder(base, "Gran Canaria")
    title = e["title"]
    category = ("Navidad " + year if CHRISTMAS_RE.search(title)
                else CATEGORIES.get(e["category"], "Otros eventos"))
    base = folder(base, category)
    return folder(base, e["municipality"][:100])


def existing_hash(drive, digest: str) -> str | None:
    found = drive.files().list(
        q=("trashed = false and appProperties has { "
           "key = 'dparranda_sha256' and value = '" + digest + "' }"),
        fields="nextPageToken,files(id,name)", pageSize=1
    ).execute(num_retries=3).get("files", [])
    return found[0]["id"] if found else None


def upload(drive, e: dict, raw: bytes, mime: str, ext: str, digest: str, folder: str) -> str:
    from googleapiclient.http import MediaIoBaseUpload
    name = f"{e['start']}_{slug(e['title'])}_{digest[:12]}{ext}"
    media = MediaIoBaseUpload(BytesIO(raw), mimetype=mime, resumable=False)
    f = drive.files().create(
        body={
            "name": name,
            "parents": [folder],
            "description": f"Evento D'Parranda: {e['id']}\nOrigen: {e['source_url']}\nImagen: {e['url']}\n"
                           "Archivo autorizado por registro de permisos. No implica permiso para redes.",
            "appProperties": {"dparranda_sha256": digest,
                              "dparranda_url_sha256": hashlib.sha256(e["url"].encode()).hexdigest()},
        },
        media_body=media, fields="id"
    ).execute(num_retries=3)
    return f["id"]


def sheet_values(sheets) -> list[list[str]]:
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'!A1:P5000"
    ).execute(num_retries=3)
    return result.get("values", [])


def append_new(sheets, images, existing: dict) -> int:
    new_rows = []
    for url, e in images.items():
        if url in existing:
            continue
        new_rows.append([
            e["id"], e["title"], e["municipality"], e["start"], len(e["event_ids"]),
            url, e["source_url"], e["source_name"], e["image_origin"],
            "Pendiente de verificar", "No — pendiente de copia",
            "Pendiente", "", "", "", ""
        ])
    if new_rows:
        sheets.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'!A:P",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": new_rows}
        ).execute(num_retries=3)
    return len(new_rows)


def record_updates(sheets, updates) -> None:
    if not updates:
        return
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"valueInputOption": "RAW", "data": updates}
    ).execute(num_retries=3)


def run(drive, sheets, images: dict, max_files: int) -> dict:
    rows = sheet_values(sheets)
    existing = {r[5]: i for i, r in enumerate(rows, start=1) if len(r) > 5 and r[5]}
    added = append_new(sheets, images, existing)
    if added:
        rows = sheet_values(sheets)
    counters = {"detectadas": len(images), "nuevas_en_inventario": added,
                "archivadas": 0, "duplicadas": 0, "pendientes": 0,
                "denegadas": 0, "errores": 0}
    cache = {}
    touched = 0
    for row_number, r in enumerate(rows, start=1):
        if row_number == 1 or len(r) < 6 or r[5] not in images:
            continue
        e = images[r[5]]
        permission = r[11] if len(r) > 11 else ""
        if str(permission).strip().casefold() == "denegado":
            counters["denegadas"] += 1
            continue
        if not authorized(permission):
            counters["pendientes"] += 1
            continue
        if len(r) > 12 and r[12].strip():
            continue
        if touched >= max_files:
            break
        touched += 1
        try:
            content, mime, extension = download_image(e["url"])
            digest = hashlib.sha256(content).hexdigest()
            file_id = existing_hash(drive, digest)
            if file_id:
                counters["duplicadas"] += 1
                status = "Sí — archivo reutilizado"
            else:
                folder = destination(drive, e, cache)
                file_id = upload(drive, e, content, mime, extension, digest, folder)
                counters["archivadas"] += 1
                status = "Sí — archivado"
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            fields = [status, permission, file_id, digest, now, ""]
            time.sleep(1)
        except Exception as ex:
            counters["errores"] += 1
            fields = [(r[10] if len(r) > 10 else "No — pendiente de copia"),
                      permission, "", "", "", str(ex)[:180]]
        record_updates(sheets, [{
            "range": f"'{SHEET_NAME}'!K{row_number}:P{row_number}",
            "values": [fields]
        }])
    return counters


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-files", type=int, default=80)
    args = parser.parse_args()
    images = discover(json.loads(CATALOG.read_text(encoding="utf-8")))
    if args.dry_run:
        print(json.dumps({"imagenes_activas_distintas": len(images),
                          "subida": "desactivada por dry-run"}, ensure_ascii=False))
        return 0
    if args.max_files < 1 or args.max_files > 250:
        parser.error("--max-files debe estar entre 1 y 250")
    drive, sheets = services()
    summary = run(drive, sheets, images, args.max_files)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not summary["errores"] else 1


if __name__ == "__main__":
    sys.exit(main())
