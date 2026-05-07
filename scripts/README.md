# 🛰️ Desafio SIAPESQ - Pipeline de Variáveis Ambientais para SDM

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Rasterio](https://img.shields.io/badge/Rasterio-Geospatial-green)
![Xarray](https://img.shields.io/badge/Xarray-Data_Arrays-orange)
![Status](https://img.shields.io/badge/Status-Concluído-brightgreen)

## 📌 Visão Geral
Este repositório contém a solução técnica para o Desafio de Engenharia de Dados Espaciais da **SIAPESQ**. O objetivo do projeto é construir um pipeline automatizado de extração, processamento e padronização de variáveis ambientais (Topografia, Clima, Uso do Solo e Índices Ópticos) para alimentar modelos de Machine Learning focados na Modelagem de Distribuição de Espécies (SDM) da cultura da Canola (*Brassica napus*).

O pipeline foi projetado com foco em **escalabilidade**, **prevenção de estouro de memória (Out-Of-Memory)** e **reprodutibilidade**, garantindo a integridade matemática da pilha de rasters (*Raster Stack*).

---

## ⚙️ Decisões de Arquitetura e Engenharia
Para atender aos rigorosos requisitos matemáticos e geográficos do desafio, as seguintes estratégias foram implementadas:

1. **Cloud Downscaling (Otimização de Rede):** Em vez de realizar o download de matrizes pesadas (ex: DEM de 30m) para processamento local, a resolução alvo (`0.001 graus` / ~100m) foi forçada via API STAC. Isso transferiu o custo computacional para os servidores em nuvem, reduzindo o tráfego e o uso de memória local em mais de 90%.
2. **Raster Gabarito e Alinhamento Cirúrgico:** A Altitude (DEM) foi eleita como "Raster Molde". Todos os outros preditores foram forçados a herdar seu *Shape*, *Bounding Box* e *CRS* (EPSG:4326) através de reprojeções matriciais.
3. **Resampling Orientado à Natureza do Dado:** Atendendo aos requisitos de SDM, aplicou-se interpolação **Bilinear** para variáveis contínuas (Clima, Altitude) e **Nearest Neighbor (Vizinho Mais Próximo)** para a variável categórica (Uso do Solo), impedindo a geração de classes sintéticas corrompidas.
4. **Correção de Longitude Global (ERA5):** Implementação de transformação matricial (`((longitude + 180) % 360) - 180`) para converter o padrão europeu de 0 a 360 graus para o sistema cartesiano centrado no Meridiano de Greenwich (-180 a 180), garantindo o encaixe perfeito sobre a América do Sul.
5. **Estratégia de Mosaico Blindada (Sentinel-2):** Para compor o índice NDVI de uma extensa área continental sem estourar a memória RAM, a busca foi ancorada em uma janela temporal de 15 dias de agosto com processamento em lotes (`chunks`), blindada com constante matemática (`+ 0.0001`) contra anomalias de reflectância nula.
6. **Sanitização de NoData:** Conversão programática de anomalias espaciais (ex: `-32768`) para nulos padrão da linguagem (`NaN`) durante a amostragem (*Point Sampling*), entregando um CSV cirurgicamente limpo para a Inteligência Artificial.

---

## 🗂️ Estrutura do Pipeline

O pipeline é modularizado em 4 scripts principais e 1 orquestrador:

* `01_download_data.py`: Requisição de dados brutos (Copernicus DEM, ESA WorldCover, ERA5-Land).
* `02_process_data.py`: Correção de CRS, reamostragem, e criação do *Raster Stack* alinhado.
* `03_generate_predictors.py`: Extração do Sentinel-2 (NDVI), *Point Sampling* cruzado com o CSV de ocorrências e tratamento de *NoData*.
* `04_validate_outputs.py`: Testes unitários espaciais e renderização de mapas de calor para auditoria visual.
* `run_pipeline.py`: CLI (Interface de Linha de Comando) orquestradora *End-to-End*.

---

## 🚀 Como Executar

### 1. Pré-requisitos e Instalação
Recomenda-se o uso do Anaconda/Miniconda para gerenciar as dependências espaciais pesadas (GDAL, PROJ).

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/Desafio_SIAPESQ.git
cd Desafio_SIAPESQ

# Instale as dependências
pip install -r requirements.txt

```

# 🔑 Autenticação do Copernicus (CDS API)
Para o download automático dos dados climáticos, é necessário possuir uma credencial válida.

Crie uma conta no [Copernicus Climate Data Store.](https://cds.climate.copernicus.eu/)
Obtenha sua API Key no seu perfil de usuário.
Abra o arquivo config.yaml na raiz do projeto e insira a sua chave:
``` api:
  cds_url: "https://cds.climate.copernicus.eu/api"
  cds_key: "COLOQUE_SUA_CHAVE_AQUI"
```

## Executando o Orquestrador
Com as dependências instaladas e a chave configurada, execute o pipeline com um único comando na raiz do projeto:
``` bash
python run_pipeline.py \
  --occurrences data/raw/ocorrencias_canola_sdm_desafio.csv \
  --start-date 2025-04-01 \
  --end-date 2025-09-30 \
  --area="-20,-58,-35,-43" \
  --output outputs/rasters
```

## 📊 Resultados e Validação

<img src="C:\Users\vitor\my projects\Desafio_SIAPESQ\project\outputs\maps\evapotranspiracao_abr_ago_validacao.png" width="50%" alt="Texto Alternativo">

<img src="C:\Users\vitor\my projects\Desafio_SIAPESQ\project\outputs\maps\uso_solo_validacao.png" width="50%" alt="Texto Alternativo">





