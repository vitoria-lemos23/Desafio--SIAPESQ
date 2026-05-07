import os
import yaml
import xarray as xr
import rioxarray
from rasterio.enums import Resampling
import warnings

warnings.filterwarnings("ignore")

print("GPS Restaurado e Filtrado")

# Carregar config primeiro
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

RAW_DIR = 'data/raw'
OUT_DIR = 'outputs/rasters'
os.makedirs(OUT_DIR, exist_ok=True)

target_res = config['processing']['target_resolution']

# 1. Processar DEM (Altitude)
print("Processando Altitude")
dem = xr.open_dataset(os.path.join(RAW_DIR, 'dem_bruto.nc'))

# Procura a camada real de dados (ignora spatial_ref)
nome_dem = [v for v in dem.data_vars if v != 'spatial_ref'][0]
var_dem = dem[nome_dem]

# Renomeia eixos 
if 'longitude' in var_dem.coords:
    var_dem = var_dem.rename({'longitude': 'x', 'latitude': 'y'})
elif 'lon' in var_dem.coords:
    var_dem = var_dem.rename({'lon': 'x', 'lat': 'y'})

# Define sistema de coordenadas e dimensões espaciais
var_dem = var_dem.rio.set_spatial_dims(x_dim="x", y_dim="y").rio.write_crs("EPSG:4326")

# Reprojeta para a resolução alvo (mesmo CRS, mas reamostragem bilinear)
var_dem = var_dem.rio.reproject(
    var_dem.rio.crs,
    resolution=target_res,
    resampling=Resampling.bilinear
)

# Salva o raster de altitude (molde)
var_dem.rio.to_raster(os.path.join(OUT_DIR, 'altitude.tif'))
print("Altitude salva.")

# Carrega o molde para referência
molde = rioxarray.open_rasterio(os.path.join(OUT_DIR, 'altitude.tif')).squeeze()

# 2. Processar Clima (ERA5)
print("Processando Clima")
clima = xr.open_dataset(os.path.join(RAW_DIR, 'era5_2025_bruto.nc'), engine='netcdf4')

# Ajusta longitude para -180..180 
if clima.longitude.max() > 180:
    clima = clima.assign_coords(longitude=(((clima.longitude + 180) % 360) - 180))
    clima = clima.sortby('longitude')

clima = clima.rename({'longitude': 'x', 'latitude': 'y'})
clima = clima.rio.write_crs("EPSG:4326")

print("Calculando Temperatura Média")
temp_media = clima['t2m'].mean(dim='valid_time') - 273.15
temp_media = temp_media.rio.write_crs("EPSG:4326").rio.set_spatial_dims(x_dim="x", y_dim="y")
temp_alinhada = temp_media.rio.reproject_match(molde, resampling=Resampling.bilinear)
temp_alinhada.rio.to_raster(os.path.join(OUT_DIR, 't2m_media_abr_ago.tif'))

print("Calculando Precipitação Acumulada")
precip = clima['tp'].sum(dim='valid_time') * 1000  # converter m para mm
precip = precip.rio.write_crs("EPSG:4326").rio.set_spatial_dims(x_dim="x", y_dim="y")
precip.rio.reproject_match(molde, resampling=Resampling.bilinear).rio.to_raster(os.path.join(OUT_DIR, 'precipitacao_acumulada_abr_ago.tif'))

print("Calculando Indicadores de Geada e Calor")
# ATENÇÃO: Isso ainda é uma aproximação grosseira (baseado em média mensal)
# O ideal seria usar dados diários. Mas vamos manter como exemplo.
dias_geada = xr.where(temp_alinhada < 10, 5, 0).rio.write_crs("EPSG:4326")
dias_geada.rio.to_raster(os.path.join(OUT_DIR, 'dias_geada_abr_ago.tif'))

dias_calor = xr.where(temp_alinhada > 25, 10, 0).rio.write_crs("EPSG:4326")
dias_calor.rio.to_raster(os.path.join(OUT_DIR, 'dias_calor_abr_ago.tif'))

# Evapotranspiração 
nome_evap = 'e' if 'e' in clima.data_vars else ('evaporation' if 'evaporation' in clima.data_vars else None)

if nome_evap:
    print("Calculando Evapotranspiração")
    evap = clima[nome_evap].sum(dim='valid_time') * -1000  # converter e ajustar sinal
    evap = evap.rio.write_crs("EPSG:4326").rio.set_spatial_dims(x_dim="x", y_dim="y")
    evap.rio.reproject_match(molde, resampling=Resampling.bilinear).rio.to_raster(os.path.join(OUT_DIR, 'evapotranspiracao_abr_ago.tif'))
else:
    print(f" Evapotranspiração não encontrada! Variáveis disponíveis no arquivo: {list(clima.data_vars.keys())}")

# 3. Processar Uso do Solo
print("Processando Uso do Solo.")
uso = xr.open_dataset(os.path.join(RAW_DIR, 'uso_solo_bruto.nc'))

nome_uso = [v for v in uso.data_vars if v != 'spatial_ref'][0]
var_uso = uso[nome_uso]

if 'longitude' in var_uso.coords:
    var_uso = var_uso.rename({'longitude': 'x', 'latitude': 'y'})
elif 'lon' in var_uso.coords:
    var_uso = var_uso.rename({'lon': 'x', 'lat': 'y'})

var_uso = var_uso.rio.set_spatial_dims(x_dim="x", y_dim="y").rio.write_crs("EPSG:4326")
var_uso.rio.reproject_match(molde, resampling=Resampling.nearest).rio.to_raster(os.path.join(OUT_DIR, 'uso_solo.tif'))

print("Processamento concluída")