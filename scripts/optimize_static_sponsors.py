#!/usr/bin/env python3
"""Losslessly preserve aspect ratio and re-encode only the approved demo sponsor.
Runs at publication time, never per visitor. The original remains in git history.
"""
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/"public"/"sponsors"/"arimar-pollo-asado.webp"

def optimize(path=ASSET):
    path=Path(path)
    if not path.is_file():
        return False
    current=path.read_bytes()
    with Image.open(BytesIO(current)) as source:
        if source.format!="WEBP" or source.width*source.height>12_000_000:
            raise ValueError("Sponsor media must be bounded WebP")
        if source.width<=260 and source.height<=400:
            return False
        image=ImageOps.exif_transpose(source)
        image.thumbnail((260,400),Image.Resampling.LANCZOS)
        if image.mode not in ("RGB","RGBA"):
            image=image.convert("RGB")
        out=BytesIO()
        image.save(out,format="WEBP",quality=72,method=5)
        transformed=out.getvalue()
    if len(transformed)>=len(current):
        return False
    tmp=path.with_suffix(".tmp")
    tmp.write_bytes(transformed)
    tmp.replace(path)
    print(f"Sponsor image: {len(current)} -> {len(transformed)} bytes")
    return True

if __name__=="__main__":
    optimize()
