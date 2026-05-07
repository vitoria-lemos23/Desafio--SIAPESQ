import os
import glob
import rasterio
import pandas as pd
import numpy as np
import warnings
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

print(" Validação de Qualidade e Alinhamento Espacial")

RASTER_DIR = 'outputs/rasters'
MAPS_DIR = 'outputs/maps'
METADATA_CSV = 'outputs/metadata.csv'

os.makedirs(MAPS_DIR, exist_ok=True)

tifs = glob.glob(os.path.join(RASTER_DIR, '*.tif'))

if not tifs:
    print("Nenhum arquivo .tif encontrado na pasta de outputs!")
    exit()

# ------------------------------------------------------------
# 1. TESTE DE ALINHAMENTO E CRS
# ------------------------------------------------------------
print("\nTestando Alinhamento Espacial e Sistema de Coordenadas...")

gabarito_path = os.path.join(RASTER_DIR, 'altitude.tif')
with rasterio.open(gabarito_path) as src:
    ref_shape = src.shape
    ref_crs = src.crs
    ref_bounds = src.bounds

erros = 0
for tif in tifs:
    nome = os.path.basename(tif)
    with rasterio.open(tif) as src:
        shape_ok = src.shape == ref_shape
        crs_ok = src.crs == ref_crs
        bounds_ok = src.bounds == ref_bounds
        
        status_shape = "OK" if shape_ok else "NO"
        status_crs = "OK" if crs_ok else "NO"
        status_bounds = "OK" if bounds_ok else "NO"
        
        print(f"[{status_crs} CRS] [{status_shape} Shape] [{status_bounds} Bounds] {nome} | Shape: {src.shape}")
        
        if not (shape_ok and crs_ok and bounds_ok):
            erros += 1

if erros == 0:
    print("SUCESSO: Todos os rasters estão perfeitamente alinhados!")
else:
    print(f"ATENÇÃO: Encontrados {erros} erros de alinhamento.")

# ------------------------------------------------------------
# 2. GERAÇÃO DE MAPAS DE VALIDAÇÃO (CORRIGIDA)
# ------------------------------------------------------------
print("\nGerando mapas de validação visual para o Relatório...")

for tif in tifs:
    nome_var = os.path.basename(tif).replace('.tif', '')
    print(f"   Processando {nome_var}...")
    
    with rasterio.open(tif) as src:
        data = src.read(1).astype(np.float32)
        nodata = src.nodata
        if nodata is not None:
            data = np.where(data == nodata, np.nan, data)
        
        # Estatísticas básicas
        valid_mask = ~np.isnan(data)
        if not np.any(valid_mask):
            print(f"Raster sem dados válidos (todos NaN). Pulando.")
            continue
        
        min_val = np.nanmin(data)
        max_val = np.nanmax(data)
        print(f"      Valores: min={min_val:.2f}, max={max_val:.2f}")
        
        # Escolha do colormap
        if 't2m' in nome_var or 'calor' in nome_var:
            cmap = 'RdYlBu_r'
        elif 'ndvi' in nome_var:
            cmap = 'YlGn'
        elif 'precipitacao' in nome_var:
            cmap = 'Blues'
        elif 'uso_solo' in nome_var:
            cmap = 'tab20'
        else:
            cmap = 'viridis'
        
        fig, ax = plt.subplots(figsize=(15, 12))
        im = ax.imshow(data, extent=[src.bounds.left, src.bounds.right,
                                     src.bounds.bottom, src.bounds.top],
                       cmap=cmap, interpolation='nearest')
        
        if 'uso_solo' not in nome_var:
            cbar = plt.colorbar(im, ax=ax, label='Valor')
            cbar.ax.tick_params(labelsize=8)
        
        ax.set_title(f"Validação Visual: {nome_var}", fontsize=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        
        # Salva com alta resolução
        caminho_mapa = os.path.join(MAPS_DIR, f"{nome_var}_validacao.png")
        plt.savefig(caminho_mapa, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"      Mapa salvo: {caminho_mapa}")

print(f"Mapas gerados em: {MAPS_DIR}")

# ------------------------------------------------------------
# 3. AUDITORIA DE METADATA
# ------------------------------------------------------------
print("\nAuditando o arquivo metadata.csv...")
if not os.path.exists(METADATA_CSV):
    print(f"Arquivo {METADATA_CSV} não encontrado. Execute o módulo 03 primeiro.")
else:
    df = pd.read_csv(METADATA_CSV)
    total_pontos = len(df)
    # Conta pontos com pelo menos um valor não NaN entre as variáveis ambientais
    vars_ambientais = ['altitude', 't2m_media', 'precip_acumulada', 'dias_geada', 
                       'dias_calor', 'ndvi_media', 'ndvi_min']
    df_valid = df[vars_ambientais].dropna(how='all')
    pontos_validos = len(df_valid)
    pontos_nodata = total_pontos - pontos_validos
    print(f"Total de ocorrências no CSV: {total_pontos}")
    print(f"Pontos Válidos (dentro da região): {pontos_validos}")
    print(f"Pontos Ignorados (fora da área): {pontos_nodata}")

print("\nMÓDULO 04 FINALIZADO! PROJETO PRONTO PARA ENTREGA!")