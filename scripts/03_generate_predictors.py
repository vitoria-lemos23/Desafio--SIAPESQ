import os
import yaml
import pandas as pd
import numpy as np
import rasterio
from pystac_client import Client
import planetary_computer
import odc.stac
from rasterio.enums import Resampling
import warnings
import rioxarray

warnings.filterwarnings("ignore")

print("Geração de Preditores")

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

OUT_DIR = 'outputs/rasters'
arquivo_ocorrencias = 'data/raw/ocorrencias_canola_sdm_desafio.csv'

molde = rioxarray.open_rasterio(os.path.join(OUT_DIR, 'altitude.tif')).squeeze()


bounds = molde.rio.bounds()
bbox_cirurgica = [bounds[0], bounds[1], bounds[2], bounds[3]]
print(f"Buscando Sentinel-2 exatamente na área do Molde: {bbox_cirurgica}")

catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox_cirurgica,
    
    # Janela de 15 dias para fechar o mosaico sem explodir a RAM
    datetime="2025-08-01/2025-08-15",
    query={"eo:cloud_cover": {"lt": 40}}
)

melhores = list(search.item_collection())


print("Baixando Sentinel-2")
s2_data = odc.stac.load(
    melhores, 
    bands=["B04", "B08"], 
    bbox=bbox_cirurgica, 
    resolution=0.001, 
    crs="EPSG:4326", 
    patch_url=planetary_computer.sign,
    chunks={"x": 2048, "y": 2048, "time": 1} 
)

if "longitude" in s2_data.dims:
    s2_data = s2_data.rename({"longitude": "x", "latitude": "y"})

nir = s2_data["B08"].astype("float32")
red = s2_data["B04"].astype("float32")

print("Calculando NDVI Médio")
nir_med = nir.median(dim="time").compute()
red_med = red.median(dim="time").compute()

ndvi_m = (nir_med - red_med) / (nir_med + red_med + 0.0001)
ndvi_m = ndvi_m.rio.write_crs("EPSG:4326").rio.set_spatial_dims(x_dim="x", y_dim="y")
ndvi_m.rio.reproject_match(molde, resampling=Resampling.bilinear).rio.to_raster(os.path.join(OUT_DIR, 'ndvi_media_abr_ago.tif'))

print("Calculando NDVI Mínimo")
ndvi_stack = (nir - red) / (nir + red + 0.0001)
ndvi_min = ndvi_stack.min(dim="time").compute()
ndvi_min = ndvi_min.rio.write_crs("EPSG:4326").rio.set_spatial_dims(x_dim="x", y_dim="y")
ndvi_min.rio.reproject_match(molde, resampling=Resampling.bilinear).rio.to_raster(os.path.join(OUT_DIR, 'ndvi_min_abr_ago.tif'))

print("Cruzando os mapas gerados com os pontos do CSV")
df = pd.read_csv(arquivo_ocorrencias)
coords = [(lon, lat) for lon, lat in zip(df['decimalLongitude'], df['decimalLatitude'])]

mapas = {
    'altitude': 'altitude.tif', 't2m_media': 't2m_media_abr_ago.tif',
    'precip_acumulada': 'precipitacao_acumulada_abr_ago.tif',
    'dias_geada': 'dias_geada_abr_ago.tif', 'dias_calor': 'dias_calor_abr_ago.tif',
    'evapotranspiracao': 'evapotranspiracao_abr_ago.tif', 'uso_solo': 'uso_solo.tif',
    'ndvi_media': 'ndvi_media_abr_ago.tif', 'ndvi_min': 'ndvi_min_abr_ago.tif'
}

for col, arq in mapas.items():
    caminho = os.path.join(OUT_DIR, arq)
    if os.path.exists(caminho):
        with rasterio.open(caminho) as src:
            nodata = src.nodata
            valores = [val[0] for val in src.sample(coords)]
            if nodata is not None:
                valores = [np.nan if v == nodata else v for v in valores]
            df[col] = valores

df.to_csv('outputs/metadata.csv', index=False)
print("Tabela metadata.csv gerada com sucesso e sanitizada")