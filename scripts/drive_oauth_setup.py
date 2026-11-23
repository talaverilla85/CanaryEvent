#!/usr/bin/env python3
"""Genera localmente el secreto OAuth de Drive para el propietario del archivo.

Nunca compartir el JSON ni subirlo al repositorio. Usar con la cuenta
la cuenta propietaria del Drive y guardarlo en GitHub Actions Secrets.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--client', required=True, help='JSON OAuth tipo aplicación de escritorio')
    p.add_argument('--output', default=str(Path.home() / '.dparranda-drive-oauth.json'))
    args = p.parse_args()
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(args.client, SCOPES)
    credentials = flow.run_local_server(port=0, access_type='offline', prompt='consent')
    if not credentials.refresh_token:
        raise RuntimeError('Sin refresh_token. Repetir consentimiento con prompt=consent.')
    target = Path(args.output).expanduser()
    if target.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise RuntimeError('Por seguridad guarda el token fuera del repositorio')
    target.write_text(credentials.to_json(), encoding='utf-8')
    os.chmod(target, 0o600)
    print('Token guardado SOLO en tu equipo:', target)
    print('Añade su contenido al secreto GitHub DPARRANDA_GOOGLE_DRIVE_OAUTH_JSON.')
    print('No lo subas a Drive, GitHub ni lo pegues en una conversación.')

if __name__ == '__main__':
    main()
