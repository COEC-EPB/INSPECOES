from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import unicodedata

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API online 🚀"


# 🔹 NORMALIZAR COLUNAS
def normalizar_colunas(df):
    def limpar(col):
        col = str(col).strip().upper()
        col = unicodedata.normalize('NFKD', col).encode('ASCII', 'ignore').decode('ASCII')
        return col
    df.columns = [limpar(c) for c in df.columns]
    return df


# 🔹 DETECTAR HEADER AUTOMATICAMENTE
def ler_excel_corrigido(file):

    df_raw = pd.read_excel(file, header=None)

    header_row = None

    for i, row in df_raw.iterrows():
        valores = row.astype(str).str.upper()

        if valores.str.contains("MATRICULA").any():
            header_row = i
            break

    if header_row is None:
        raise ValueError("❌ Não encontrou linha de cabeçalho com 'MATRICULA'")

    df = pd.read_excel(file, header=header_row)
    df = normalizar_colunas(df)

    return df


@app.route('/processar', methods=['POST'])
def processar():
    try:
        arquivos = request.files.getlist("meses")
        ipeo_file = request.files.get("ipeo")

        if not arquivos or not ipeo_file:
            return jsonify({"erro": "Envie arquivos de meses e IPEO"}), 400

        # 🔹 CONCATENAR MESES
        lista_df = []
        for f in arquivos:
            df = ler_excel_corrigido(f)
            lista_df.append(df)

        df_meses = pd.concat(lista_df, ignore_index=True)

        # 🔹 IPEO
        df_ipeo = ler_excel_corrigido(ipeo_file)

        # 🔍 DEBUG
        print("COLUNAS MESES:", df_meses.columns.tolist())
        print("COLUNAS IPEO:", df_ipeo.columns.tolist())

        # 🔹 VALIDAÇÃO
        obrigatorias = ["MATRICULA", "MES"]

        for col in obrigatorias:
            if col not in df_meses.columns:
                return jsonify({"erro": f"Coluna '{col}' não encontrada nos arquivos de meses"}), 400
            if col not in df_ipeo.columns:
                return jsonify({"erro": f"Coluna '{col}' não encontrada no IPEO"}), 400

        # 🔹 MERGE
        df = df_meses.merge(
            df_ipeo,
            on=["MATRICULA", "MES"],
            how="inner"
        )

        # 🔹 COLUNAS DESEJADAS
        colunas_desejadas = [
            "DI", "ROE", "RNT", "IOC", "ISF", "ROV",
            "EMPRESA", "MES", "REGIONAL", "POLO PRESTADOR",
            "MATRICULA", "NOME FUNCIONARIO", "IPEO",
            "PRODUTIVIDADE", "EFICIENCIA", "UTILIZACAO", "TMS"
        ]

        colunas_existentes = [c for c in colunas_desejadas if c in df.columns]

        if not colunas_existentes:
            return jsonify({"erro": "Nenhuma coluna esperada foi encontrada após o merge"}), 400

        df = df[colunas_existentes]

        # 🔹 AGRUPAMENTO
        colunas_grupo = [
            "EMPRESA", "MES", "REGIONAL", "POLO PRESTADOR",
            "MATRICULA", "NOME FUNCIONARIO"
        ]

        colunas_grupo = [c for c in colunas_grupo if c in df.columns]

        df_final = df.groupby(colunas_grupo, as_index=False).mean(numeric_only=True)

        # 🔹 EXPORTAR
        output = "resultado.xlsx"
        df_final.to_excel(output, index=False)

        return send_file(output, as_attachment=True)

    except Exception as e:
        print("ERRO:", str(e))
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
