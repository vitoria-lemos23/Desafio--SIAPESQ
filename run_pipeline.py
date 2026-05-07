import argparse
import subprocess
import yaml
import os

print("==================================================")
print("PIPELINE DE VARIÁVEIS AMBIENTAIS SDM")
print("==================================================\n")

def atualizar_configuracoes(args):
    """Lê os argumentos do terminal e atualiza o config.yaml dinamicamente"""
    
   
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Converte a string para números
    n, w, s, e = map(float, args.area.split(','))

    # Atualiza o dicionário com os dados do terminal
    config['area']['north'] = n
    config['area']['west'] = w
    config['area']['south'] = s
    config['area']['east'] = e
    # A BBOX do STAC exige a ordem: [min_lon, min_lat, max_lon, max_lat] -> [W, S, E, N]
    config['area']['bbox_stac'] = [w, s, e, n] 

    config['period']['start'] = args.start_date
    config['period']['end'] = args.end_date

    # Garante que a pasta de saída existe
    os.makedirs(args.output, exist_ok=True)

    # 4. Salva as mudanças de volta no arquivo config.yaml
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
        
    print(f"Configurações atualizadas para o período: {args.start_date} a {args.end_date}")
    print(f"BBOX definida para: {config['area']['bbox_stac']}\n")


def rodar_scripts():
    scripts = [
        "scripts/01_download_data.py",
        "scripts/02_process_data.py",
        "scripts/03_generate_predictors.py",
        "scripts/04_validate_outputs.py"
    ]

    for script in scripts:
        print(f"▶️ Iniciando: {script} ...")

        # subprocess manda o terminal rodar o comando automaticamente
        resultado = subprocess.run(["python", script])
        
        if resultado.returncode != 0:
            print(f"\nERRO FATAL: O pipeline quebrou durante a execução de {script}.")
            exit(1)
        print("-" * 50)


if __name__ == "__main__":

    # leitor de comandos do terminal
    parser = argparse.ArgumentParser(description="Pipeline Automatizado para SDM - Canola")
    
    parser.add_argument("--occurrences", required=True, help="Caminho para o CSV de ocorrências")
    parser.add_argument("--start-date", required=True, help="Data de início (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="Data de fim (YYYY-MM-DD)")
    parser.add_argument("--area", required=True, help="BBOX no formato Norte,Oeste,Sul,Leste")
    parser.add_argument("--output", required=True, help="Pasta de saída para os rasters")

    args = parser.parse_args()

    # Executa as funções
    atualizar_configuracoes(args)
    rodar_scripts()
    
    print("Todos os arquivos estão na pasta outputs.")