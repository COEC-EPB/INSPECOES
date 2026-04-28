from flask import Flask, request, send_file
from flask_cors import CORS
import pandas as pd
import unicodedata

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API online 🚀"



def normalizar_colunas(df):
    def limpar(col):
        col = col.strip().upper()
        col = unicodedata.normalize('NFKD', col).encode('ASCII', 'ignore').decode('ASCII')
        return col
    df.columns = [limpar(c) for c in df.columns]
    return df


@app.route('/processar', methods=['POST'])
def processar():

    arquivos = request.files.getlist("meses")
    ipeo_file = request.files.get("ipeo")

    if not arquivos or not ipeo_file:
        return {"erro": "Envie arquivos de meses e IPEO"}, 400

    # 🔹 CONCATENAR MESES
    lista_df = []
    for f in arquivos:
        df = pd.read_excel(f)
        df = normalizar_colunas(df)
        lista_df.append(df)

    df_meses = pd.concat(lista_df, ignore_index=True)

    # 🔹 IPEO
    df_ipeo = pd.read_excel(ipeo_file)
    df_ipeo = normalizar_colunas(df_ipeo)

    # 🔍 DEBUG (opcional)
    print("COLUNAS MESES:", df_meses.columns)
    print("COLUNAS IPEO:", df_ipeo.columns)

    # 🔹 VALIDAÇÃO
    obrigatorias = ["MATRICULA", "MES"]

    for col in obrigatorias:
        if col not in df_meses.columns:
            return {"erro": f"Coluna {col} não encontrada nos arquivos de meses"}, 400
        if col not in df_ipeo.columns:
            return {"erro": f"Coluna {col} não encontrada no IPEO"}, 400

    # 🔹 JOIN
    df = df_meses.merge(
        df_ipeo,
        on=["MATRICULA", "MES"],
        how="inner"
    )

    # 🔹 COLUNAS (já normalizadas!)
    colunas = [
        "DI", "ROE", "RNT", "IOC", "ISF", "ROV",
        "EMPRESA", "MES", "REGIONAL", "POLO PRESTADOR",
        "MATRICULA", "NOME FUNCIONARIO", "IPEO",
        "PRODUTIVIDADE", "EFICIENCIA", "UTILIZACAO", "TMS"
    ]

    # Ajuste automático: pega só as que existem
    colunas_existentes = [c for c in colunas if c in df.columns]
    df = df[colunas_existentes]

    # 🔹 AGRUPAMENTO
    df_final = df.groupby([
        "EMPRESA", "MES", "REGIONAL", "POLO PRESTADOR",
        "MATRICULA", "NOME FUNCIONARIO"
    ], as_index=False).mean()

    # 🔹 EXPORTAR
    output = "resultado.xlsx"
    df_final.to_excel(output, index=False)

    return send_file(output, as_attachment=True)
