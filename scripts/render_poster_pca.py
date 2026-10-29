"""Render the simplified poster map from the unchanged, current v2 PCA scores."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/fire_vase_matplotlib')
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

root=Path(__file__).resolve().parents[1]
d=pd.read_parquet(root/'analysis/v2/event_analysis.parquet')
p=d[d.primary_eligible]
assert len(p)==10246
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':16,'axes.labelcolor':'#142934','text.color':'#142934','axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(11,6.8))
fig.subplots_adjust(left=.16,right=.84,bottom=.23,top=.84)
h=ax.hexbin(p.shape_PC1,p.shape_PC2,gridsize=40,mincnt=1,bins='log',cmap='Blues',rasterized=True)
ax.set_title('A map of 10,246 fire growth histories',fontsize=21,pad=20,loc='left')
ax.set_xlabel('Earlier growth  <---->  Later growth\nPC1: 34.1% of variation',fontsize=16,labelpad=12)
ax.set_ylabel('Endpoint-weighted  <---->  Middle-concentrated\nPC2: 28.2% of variation',fontsize=15,labelpad=12)
ax.tick_params(labelsize=12)
bar=fig.colorbar(h,ax=ax,fraction=.045,pad=.04)
bar.set_label('Fires per hexagon',fontsize=14);bar.ax.tick_params(labelsize=12)
fig.text(.16,.035,'Nearby positions indicate similar growth timing. Darker bins contain more fires.',fontsize=13)
out=root/'tmp/pdfs/poster-pca.pdf';out.parent.mkdir(parents=True,exist_ok=True)
fig.savefig(out,dpi=450);plt.close(fig)
print(out)
