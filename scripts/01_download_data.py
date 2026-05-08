import os
import yaml
import cdsapi
from pystac_client import Client
import planetary_computer
import odc.stac
import zipfile
import shutil
import cdsapi




# Carregando Configurações
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# A chave e a URL que colocou no config.yaml será inputada aqui
c = cdsapi.Client(
    url=config['api']['url'],
    key=config['api']['key']
)
bbox = config['area']['bbox_stac']
periodo = f"{config['period']['start']}/{config['period']['end']}"
target_res = config['processing']['target_resolution'] # 🛡️ FIX: Puxando 0.01 do config!

OUT_DIR = 'data/raw'
os.makedirs(OUT_DIR, exist_ok=True)

catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace
)

# ------------------------------------------------------------
# EXTRAÇÃO 1: Altitude (Copernicus DEM)
# ------------------------------------------------------------
print("\nBuscando Altitude (Copernicus DEM)...")
search_dem = catalog.search(collections=["cop-dem-glo-30"], bbox=bbox)
items_dem = search_dem.item_collection()

if items_dem:
    print(f"   -> Servidor da Microsoft fazendo o downscaling para {target_res}...")
    dem = odc.stac.load(
        items_dem,
        bbox=bbox,
        resolution=target_res, # O Segredo para não gerar 11GB!
        crs="EPSG:4326",
        chunks={"x": 2048, "y": 2048} 
    )
    dem = dem.compute()
    dem.to_netcdf(os.path.join(OUT_DIR, 'dem_bruto.nc'))
    print("Altitude super leve salva em data/raw/dem_bruto.nc")

# ------------------------------------------------------------
# EXTRAÇÃO 2: Uso do Solo (ESA WorldCover)
# ------------------------------------------------------------
print("\nBuscando Uso do Solo (ESA WorldCover)...")
search_wc = catalog.search(collections=["esa-worldcover"], bbox=bbox)
items_wc = search_wc.item_collection()

if items_wc:
    print(f"-> Servidor da Microsoft fazendo o downscaling para {target_res}...")
    wc = odc.stac.load(
        items_wc,
        bbox=bbox,
        resolution=target_res, 
        crs="EPSG:4326",
        chunks={"x": 2048, "y": 2048}
    )
    wc = wc.compute()
    wc.to_netcdf(os.path.join(OUT_DIR, 'uso_solo_bruto.nc'))
    print("Uso do Solo salvo em data/raw/uso_solo_bruto.nc")

# ------------------------------------------------------------
# EXTRAÇÃO 3: Clima (ERA5-Land via Copernicus Europeu)
# ------------------------------------------------------------
print("\nSolicitando Clima (ERA5-Land 2025) da Europa...")
area_cds = [
    config['area']['north'], config['area']['west'],
    config['area']['south'], config['area']['east']
]

URL_CDS = "https://cds.climate.copernicus.eu/api"
CHAVE_CDS = "ca528f95-9841-45e2-9747-bb087f721c5f" 

c = cdsapi.Client(url=URL_CDS, key=CHAVE_CDS)
arquivo_era5 = os.path.join(OUT_DIR, 'era5_2025_bruto.nc')

c.retrieve(
    'reanalysis-era5-land-monthly-means',
    {
        'product_type': 'monthly_averaged_reanalysis',
        'variable': [
            '2m_temperature', 
            'total_precipitation',
            'total_evaporation'  
        ],
        'year': '2025',
        'month': ['04', '05', '06', '07', '08', '09'],
        'time': '00:00',
        'area': area_cds,
        'format': 'netcdf',
    },
    arquivo_era5
)
print("Clima salvo em data/raw/era5_2025_bruto.nc")

# Limpeza do ZIP
if zipfile.is_zipfile(arquivo_era5):
    temp_dir = os.path.join(OUT_DIR, 'temp_era5_extract')
    with zipfile.ZipFile(arquivo_era5, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    for file in os.listdir(temp_dir):
        if file.endswith('.nc'):
            shutil.move(os.path.join(temp_dir, file), arquivo_era5)
            break
    shutil.rmtree(temp_dir)

print("\nDownload dos dados concluídos")