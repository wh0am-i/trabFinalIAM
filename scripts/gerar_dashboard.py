"""Gera um dashboard HTML independente, com dados reais embutidos."""

import json
from pathlib import Path

import pandas as pd

from visualizar_dados import ROOT, carregar

DESCRIPTIONS = {
    "date": "Data e hora da medição (fuso não informado)",
    "Temperature": "Temperatura ambiente (°C)",
    "Humidity": "Umidade relativa (%)",
    "Light": "Iluminação (lux)",
    "CO2": "Concentração de CO₂ (ppm)",
    "HumidityRatio": "Razão de umidade (kg de vapor / kg de ar seco)",
    "Occupancy": "Alvo: 0 = vazia; 1 = ocupada",
    "AT": "Temperatura ambiente de sucção (°C)",
    "V": "Vácuo de exaustão (cm Hg)",
    "AP": "Pressão atmosférica (mbar)",
    "RH": "Umidade relativa (%)",
    "PE": "Alvo: potência elétrica líquida (MW)",
}


def main():
    occupancy, ccpp = carregar()
    datasets = []
    for filename, df in [*occupancy.items(), ("ccpp", ccpp)]:
        is_occupancy = filename != "ccpp"
        key = filename.replace(".txt", "")
        numeric = df.select_dtypes(include="number")
        limits = []
        for col in df.columns:
            minimum, maximum = df[col].min(), df[col].max()
            limits.append([col, str(minimum) if col == "date" else float(minimum),
                           str(maximum) if col == "date" else float(maximum), int(df[col].isna().sum())])
        spread = numeric.agg(["mean", "std", "var", "min", "max"]).T
        spread.columns = ["Média", "Desvio padrão (amostral)", "Variância (amostral)", "Mínimo", "Máximo"]
        spread["Amplitude (máx − mín)"] = numeric.max() - numeric.min()
        info = [[col, str(df[col].dtype), int(df[col].count()), int(df[col].isna().sum()), DESCRIPTIONS.get(col, "")] for col in df.columns]
        table = df.copy()
        if is_occupancy:
            table["date"] = table.date.dt.strftime("%Y-%m-%d %H:%M:%S")
            table = table.reset_index()
        else:
            table.insert(0, "linha", range(len(table)))
        period = f"Período: {df.date.min()} até {df.date.max()}." if is_occupancy else "Datas individuais não fornecidas; não interpretar a ordem das linhas como ordem temporal."
        description = ("Sensores de sala · " + ("Treino original, usado como visão inicial." if filename == "datatraining.txt" else "Teste original, exibido separadamente para consulta; reservar para a avaliação futura.")) if is_occupancy else "Usina de ciclo combinado · 9.568 medições · Somente Sheet1, sem concatenar abas repetidas."
        datasets.append({
            "key": key,
            "label": ("Occupancy · " + filename) if is_occupancy else "CCPP · usina · Sheet1",
            "context": description,
            "columns": table.columns.tolist(),
            "rows": json.loads(table.to_json(orient="values", double_precision=15)),
            "numeric": numeric.columns.tolist(),
            "info": info,
            "describe": numeric.describe().to_html(float_format=lambda value: f"{value:,.6g}"),
            "limits": limits,
            "spread": spread.to_html(float_format=lambda value: f"{value:.6g}"),
            "covariance": numeric.cov().to_html(float_format=lambda value: f"{value:.6g}"),
            "correlation": numeric.corr().to_html(float_format=lambda value: f"{value:.4f}"),
            "missing": int(df.isna().sum().sum()),
            "duplicates": int(df.duplicated().sum()),
            "period": period,
        })
        print(f"{filename}: {df.shape}, ausentes={df.isna().sum().sum()}, duplicatas={df.duplicated().sum()}")
    template = Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
    payload = json.dumps(datasets, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    output = ROOT / "reports/dashboard.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__DATA__", payload), encoding="utf-8")
    print(f"Dashboard: {output}")


if __name__ == "__main__":
    main()
