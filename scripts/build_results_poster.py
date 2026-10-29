"""Build a 24 x 36 inch print poster from repository visuals (no external assets).

Requires reportlab, pypdf and Pillow. The optional --hero image should be a
higher-resolution render of fire 387635 from scripts/generate_hero_vase.py.
Scientific panels use the current v2 figure and PCA scores as vector artwork.
The PCA helper uses the repository .venv (matplotlib, pandas and pyarrow).
"""
from pathlib import Path
import argparse
import subprocess
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from PIL import Image
from pypdf import PdfReader, PdfWriter, Transformation

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hero', type=Path, default=ROOT/'docs/assets/hero-vase-vpd.png')
    args = parser.parse_args()
    out = ROOT/'output/pdf/fire_vase_results_poster.pdf'
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = ROOT/'tmp/pdfs'; temp.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(ROOT/'.venv/bin/python'), str(ROOT/'scripts/render_poster_pca.py')], check=True)
    for name, file in [('Body','Arial.ttf'),('Bold','Arial Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(name, '/System/Library/Fonts/Supplemental/'+file))
    W,H=1728,2592
    c=canvas.Canvas(str(temp/'poster-base.pdf'),pagesize=(W,H))
    c.setTitle('Fire VASE | The shape of a fire'); c.setAuthor('Fire VASE research repository')
    def text(x,y,s,size=24,font='Body',color='#142934'):
        c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,y,s)
    c.setFillColor(HexColor('#ffffff'));c.rect(0,0,W,H,fill=1,stroke=0)
    text(85,2480,'F I R E   V A S E',29,'Bold','#a45419')
    text(80,2348,'The shape of a fire',112,'Bold')
    text(86,2285,'Wildfire histories, made visible.',39)
    c.setStrokeColor(HexColor('#d7dfe2')); c.line(85,2235,1643,2235)
    # A transparent, data-derived surface, with its source aspect ratio intact.
    im=Image.open(args.hero); box=im.getbbox(); im=im.crop(box)
    im.save(temp/'hero-cropped.png')
    iw,ih=im.size; height=1100; width=height*iw/ih
    # Layered transparent ellipses form a soft cast shadow and a contact shadow.
    # These are vector layout elements; the source scientific render is unchanged.
    def shadow(cx, cy, rx, ry, opacity):
        c.saveState()
        c.setFillColor(HexColor('#263440'))
        for step in range(50, 0, -1):
            scale=step/50
            c.setFillAlpha(opacity/22)
            c.ellipse(cx-rx*scale,cy-ry*scale,cx+rx*scale,cy+ry*scale,fill=1,stroke=0)
        c.restoreState()
    shadow(75+width/2+105,1085,340,42,.22)
    shadow(75+width/2,1095,95,15,.42)
    c.drawImage(str(temp/'hero-cropped.png'),75,1100,width=width,height=height,mask='auto')
    x=1200
    text(x,2130,'ONE FIRE',22,'Bold','#a45419')
    text(x,2050,'925',79,'Bold');text(x,2010,'square kilometres',25)
    text(x,1905,'33',79,'Bold');text(x,1865,'days of development',25)
    text(x,1760,'31',79,'Bold');text(x,1720,'dated observations',25)
    text(x,1605,'READ THE VASE',21,'Bold','#a45419')
    for j,line in enumerate(['Upward: development time','Width: cumulative growth','Colour: atmospheric dryness']):text(x,1550-j*39,line,22)
    # Inferno colour key matches the existing hero renderer.
    from reportlab.lib.colors import Color
    stops=[(0.0,(0,0,4)),(.25,(87,16,110)),(.5,(188,55,84)),(.75,(249,142,9)),(1,(252,255,164))]
    for i in range(240):
        t=i/239
        k=min(int(t*4),3); a,ca=stops[k]; b,cb=stops[k+1]
        rgb=[(ca[j]+(cb[j]-ca[j])*(t-a)/(b-a))/255 for j in range(3)]
        c.setFillColor(Color(*rgb));c.rect(x+i*1.65,1360,1.8,18,fill=1,stroke=0)
    text(x,1320,'2.02',20);text(x+290,1320,'4.15 kPa',20)
    text(x,1278,'Daily vapour pressure deficit',20)
    text(85,1035,'Fire 387635  /  western region  /  2018',21,'Body','#526771')
    text(85,989,'Illustrative 3D rendering: cumulative normalized width, coloured by centroid gridMET VPD.',19,'Body','#526771')
    c.setFillColor(HexColor('#ffffff'));c.rect(0,0,W,930,fill=1,stroke=0)
    text(85,856,'Different histories. Shared coordinates.',49,'Bold','#142934')
    text(85,808,'Current v2 results reveal continuous gradients in how fires allocate growth through time.',25,'Body','#38515a')
    text(85,735,'01  FROM OBSERVATIONS TO FORM',22,'Bold','#267e7a')
    text(902,735,'02  A CONTINUUM OF DEVELOPMENT',22,'Bold','#267e7a')
    # White panels reserve clean backgrounds for the original vector figures.
    for panel_x in (70,884):
        c.saveState()
        c.setFillColor(HexColor('#263440'))
        for offset in range(16,0,-1):
            c.setFillAlpha(.006)
            c.roundRect(panel_x-offset/2,210-offset,774+offset,495+offset/2,5,fill=1,stroke=0)
        c.restoreState()
    c.setFillColor(HexColor('#ffffff'))
    c.rect(70,210,774,495,fill=1,stroke=0);c.rect(884,210,774,495,fill=1,stroke=0)
    text(85,164,'Growth observations become comparable VASE profiles.',21,'Body','#38515a')
    text(902,164,'Two main gradients explain 62.4% of variation.',21,'Body','#38515a')
    text(85,105,'Broad gradients are supported; these are not established natural fire classes.',21,'Bold','#142934')
    text(85,63,'Sources: figures/v2/Figures 1-2; docs/assets/hero-vase-vpd.json.  |  CU-ESIIL/fire_vase',17,'Body','#38515a')
    c.save()
    page=PdfReader(temp/'poster-base.pdf').pages[0]
    for name,x in [('Figure_1',70),('Figure_2',884)]:
        source_path = temp/'poster-pca.pdf' if name == 'Figure_2' else ROOT/f'figures/v2/{name}.pdf'
        source=PdfReader(source_path).pages[0]
        sw,sh=float(source.mediabox.width),float(source.mediabox.height)
        scale=min(754/sw,475/sh)
        page.merge_transformed_page(source,Transformation().scale(scale).translate(x+10+(754-sw*scale)/2,220+(475-sh*scale)/2))
    writer=PdfWriter();writer.add_page(page)
    writer.add_metadata({'/Title':'Fire VASE | The shape of a fire','/Author':'Fire VASE research repository'})
    with out.open('wb') as f:writer.write(f)
    print(out)
    print(f'Hero effective resolution: {ih/(1100/72):.0f} dpi; vector text and scientific panels.')

if __name__=='__main__':main()
