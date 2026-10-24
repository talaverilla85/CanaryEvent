from pathlib import Path
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]/'public'/'icons'
root.mkdir(parents=True, exist_ok=True)
for size in (192,512):
    im=Image.new('RGB',(size,size),(20,44,42))
    d=ImageDraw.Draw(im)
    b=int(size*.14); m=size//2; w=int(size*.055)
    d.ellipse((b,b,size-b,size-b),outline=(198,241,184),width=w)
    for (x1,y1,x2,y2) in [(m,m-size*.21,m,m+size*.21),(m-size*.21,m,m+size*.21,m),(m-size*.15,m-size*.15,m+size*.15,m+size*.15),(m-size*.15,m+size*.15,m+size*.15,m-size*.15)]:
        d.line((x1,y1,x2,y2),fill=(198,241,184),width=w)
    im.save(root/f'icon-{size}.png')
print('OK')
