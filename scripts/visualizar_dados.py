"""Baixa os arquivos oficiais e gera um relatório exploratório local."""

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "occupancy": "https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip",
    "ccpp": "https://archive.ics.uci.edu/static/public/294/combined+cycle+power+plant.zip",
}


def baixar():
    manifest = {}
    for name, url in SOURCES.items():
        folder = ROOT / "data/01_raw" / name
        folder.mkdir(parents=True, exist_ok=True)
        archive = folder / ("occupancy_detection.zip" if name == "occupancy" else "combined_cycle_power_plant.zip")
        if not archive.exists():
            print(f"Baixando {name}: {url}", flush=True)
            temporary = archive.with_suffix(".zip.part")
            try:
                with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
                    shutil.copyfileobj(response, output)
                if not zipfile.is_zipfile(temporary):
                    raise ValueError(f"O download de {name} não é um ZIP válido")
                temporary.replace(archive)
            finally:
                temporary.unlink(missing_ok=True)
        # Extrai somente os arquivos usados, mantendo o ZIP original.
        expected = {"datatraining.txt", "datatest.txt", "datatest2.txt"} if name == "occupancy" else {"Folds5x2_pp.xlsx", "Readme.txt"}
        found = set()
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                basename = Path(member.filename).name
                if basename in expected:
                    with zf.open(member) as source, (folder / basename).open("wb") as output:
                        shutil.copyfileobj(source, output)
                    found.add(basename)
        if not expected.issubset(found):
            raise ValueError(f"Arquivos ausentes em {name}: {expected - found}")
        manifest[name] = {
            "url": url,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "verificado_em_utc": datetime.now(timezone.utc).isoformat(),
        }
    (ROOT / "data/01_raw/fontes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def carregar():
    import pandas as pd

    occupancy = {}
    for filename in ("datatraining.txt", "datatest.txt", "datatest2.txt"):
        df = pd.read_csv(ROOT / "data/01_raw/occupancy" / filename, index_col=0, parse_dates=["date"])
        df.index.name = "registro_original"
        occupancy[filename] = df
    # As demais abas repetem as observações em outras ordens.
    try:
        ccpp = pd.read_excel(ROOT / "data/01_raw/ccpp/Folds5x2_pp.xlsx", sheet_name=0, engine="openpyxl")
    except ImportError:
        prepared = ROOT / "data/02_intermediate/ccpp.csv"
        if not prepared.exists():
            raise
        ccpp = pd.read_csv(prepared)
    return occupancy, ccpp


def gerar_relatorio():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    occupancy, ccpp = carregar()
    reports = ROOT / "reports"
    figures = reports / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    intermediate = ROOT / "data/02_intermediate"
    intermediate.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})
    parts = ["<h1>Desafio final IAM — primeira leitura dos dados</h1>",
             "<p>Inspeção descritiva inicial. Nenhum modelo foi treinado. Os arquivos originais foram preservados.</p>",
             "<p>Occupancy: gráficos somente do treino original. CCPP: primeira aba, sem concatenar os cinco embaralhamentos. "
             "A divisão de treino/teste do CCPP ainda será feita; esta visão global não deve orientar seleção de modelos ou atributos.</p>"]
    parts.append("<h2>Arquivos de ocupação</h2>")
    for filename, frame in occupancy.items():
        parts.append(f"<p>{filename}: {len(frame):,} registros; {frame['date'].min()} a {frame['date'].max()}.</p>")
        frame.to_csv(intermediate / filename.replace(".txt", ".csv"), index=True)
    ccpp.to_csv(intermediate / "ccpp.csv", index=False)

    for name, df, target in [("occupancy", occupancy["datatraining.txt"], "Occupancy"), ("ccpp", ccpp, "PE")]:
        numeric = df.select_dtypes(include="number")
        parts.extend([f"<h2>{name.upper()}</h2>",
                      f"<p>{len(df):,} linhas; {len(df.columns)} colunas; "
                      f"{int(df.isna().sum().sum())} valores ausentes; {int(df.duplicated().sum())} linhas duplicadas completas.</p>",
                      "<h3>Primeiras 15 linhas</h3>", df.head(15).to_html(),
                      "<h3>Tipos e ausências</h3>", df.dtypes.astype(str).to_frame("tipo").join(df.isna().sum().rename("ausentes")).to_html(),
                      "<h3>Estatísticas</h3>", numeric.describe().round(4).to_html()])
        numeric.hist(bins=35, figsize=(12, 8), color="#247b91", edgecolor="white")
        plt.suptitle(f"{name.upper()} — distribuições (unidades originais)")
        plt.tight_layout()
        plt.savefig(figures / f"{name}_distribuicoes.png")
        plt.close("all")
        corr = numeric.corr()
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(corr)), corr.columns)
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", color="white" if abs(corr.iloc[i, j]) > .65 else "black")
        fig.colorbar(im, ax=ax, label="Correlação de Pearson")
        ax.set_title(f"{name.upper()} — correlação não implica causalidade")
        fig.tight_layout()
        fig.savefig(figures / f"{name}_correlacoes.png")
        plt.close(fig)
        for suffix in ("distribuicoes", "correlacoes"):
            parts.append(f'<img src="figures/{name}_{suffix}.png" alt="{name}: {suffix}">')

    train = occupancy["datatraining.txt"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    counts = train.Occupancy.value_counts().reindex([0, 1], fill_value=0)
    axes[0].bar(["Vazia (0)", "Ocupada (1)"], counts, color=["#247b91", "#d67a31"])
    axes[0].set_ylabel("Número de registros")
    for label, color in [(0, "#247b91"), (1, "#d67a31")]:
        subset = train[train.Occupancy == label]
        axes[1].scatter(subset.Light, subset.CO2, s=7, alpha=.25, label=str(label), color=color)
    axes[1].set(xlabel="Iluminação (lux)", ylabel="CO₂ (ppm)")
    axes[1].legend(title="Ocupação")
    fig.tight_layout()
    fig.savefig(figures / "occupancy_relacoes.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.scatter(ccpp.AT, ccpp.PE, s=5, alpha=.2, color="#247b91")
    ax.set(xlabel="Temperatura ambiente (°C)", ylabel="Potência elétrica líquida (MW)", title="CCPP — temperatura e potência")
    fig.tight_layout()
    fig.savefig(figures / "ccpp_relacoes.png")
    plt.close(fig)
    parts.extend(['<h2>Relações físicas e alvo</h2><img src="figures/occupancy_relacoes.png" alt="Ocupação, luz e CO2">',
                  '<p>Luz e CO₂ podem estar associados à presença, mas iluminação artificial e ventilação também afetam os sensores. '
                  'Amostras próximas no tempo exigem cuidado na futura validação.</p>',
                  '<img src="figures/ccpp_relacoes.png" alt="Temperatura versus potência">',
                  '<p>Uma associação negativa entre temperatura e potência é compatível com o efeito da densidade do ar na turbina a gás; '
                  'a correlação isolada não demonstra causalidade.</p>'])
    css = "body{max-width:1200px;margin:40px auto;padding:0 24px;font:16px system-ui;color:#203040}table{border-collapse:collapse;font-size:13px;display:block;overflow:auto}td,th{padding:7px;border:1px solid #ddd}img{max-width:100%;height:auto}h2{margin-top:40px}"
    html = '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Dados — desafio final IAM</title><style>' + css + '</style><body>' + "\n".join(parts) + '</body></html>'
    output = reports / "primeira_visualizacao.html"
    output.write_text(html, encoding="utf-8")
    print(f"Relatório gerado: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--somente-download", action="store_true")
    parser.add_argument("--sem-download", action="store_true", help="Usa os arquivos já extraídos em data/01_raw")
    args = parser.parse_args()
    if not args.sem_download:
        baixar()
    if not args.somente_download:
        gerar_relatorio()


if __name__ == "__main__":
    main()
