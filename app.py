from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import unicodedata

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API online 🚀"


# 🔹 NORMALIZAR TEXTO
def limpar_texto(texto):
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto


# 🔹 NORMALIZAR COLUNAS
def normalizar_colunas(df):
    df.columns = [limpar_texto(c) for c in df.columns]
    return df


# 🔹 DETECTAR HEADER AUTOMATICAMENTE
def ler_excel_corrigido(file):
    df_raw = pd.read_excel(file, header=None)

    header_row = None

    for i, row in df_raw.iterrows():
        valores = row.astype(str).apply(limpar_texto)

        if valores.str.contains("MATRICULA").any():
            header_row = i
            break

    if header_row is None:
        raise Exception("Não encontrou cabeçalho com MATRICULA")

    df = pd.read_excel(file, header=header_row)
    df = normalizar_colunas(df)

    return df


# 🔹 ENCONTRAR COLUNA POR APROXIMAÇÃO
def encontrar_coluna(df, nome):
    nome = limpar_texto(nome).replace(" ", "")

    for col in df.columns:
        c = limpar_texto(col).replace(" ", "")
        if nome in c:
            return col

    return None


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

        print("COLUNAS MESES:", df_meses.columns.tolist())
        print("COLUNAS IPEO:", df_ipeo.columns.tolist())

        # 🔹 MAPEAR COLUNAS IMPORTANTES
        mapa = {
            "MATRICULA": encontrar_coluna(df_meses, "MATRICULA"),
            "MES": encontrar_coluna(df_meses, "MES"),
        }

        mapa_ipeo = {
            "MATRICULA": encontrar_coluna(df_ipeo, "MATRICULA"),
            "MES": encontrar_coluna(df_ipeo, "MES"),
        }

        if not mapa["MATRICULA"] or not mapa["MES"]:
            return jsonify({"erro": "Colunas MATRICULA/MES não encontradas nos meses"}), 400

        if not mapa_ipeo["MATRICULA"] or not mapa_ipeo["MES"]:
            return jsonify({"erro": "Colunas MATRICULA/MES não encontradas no IPEO"}), 400

        # 🔹 RENOMEAR PARA PADRÃO
        df_meses = df_meses.rename(columns={
            mapa["MATRICULA"]: "MATRICULA",
            mapa["MES"]: "MES"
        })

        df_ipeo = df_ipeo.rename(columns={
            mapa_ipeo["MATRICULA"]: "MATRICULA",
            mapa_ipeo["MES"]: "MES"
        })

        # 🔹 MERGE
        df = df_meses.merge(df_ipeo, on=["MATRICULA", "MES"], how="inner")

        print("COLUNAS APÓS MERGE:", df.columns.tolist())

        # 🔹 MAPEAR TODAS AS COLUNAS NECESSÁRIAS
        def get(nome):
            return encontrar_coluna(df, nome)

        colunas_map = {
            "EMPRESA": get("EMPRESA"),
            "MES": "MES",
            "REGIONAL": get("REGIONAL"),
            "POLO": get("POLO"),
            "MATRICULA": "MATRICULA",
            "NOME": get("NOME"),
            "IPEO": get("IPEO"),
            "DI": get("DI"),
            "ROE": get("ROE"),
            "RNT": get("RNT"),
            "IOC": get("IOC"),
            "ISF": get("ISF"),
            "ROV": get("ROV"),
            "PROD": get("PROD"),
            "EFIC": get("EFIC"),
            "UTIL": get("UTIL"),
            "TMS": get("TMS"),
        }

        print("MAPEAMENTO FINAL:", colunas_map)

        # 🔹 FILTRAR COLUNAS EXISTENTES
        colunas_existentes = [c for c in colunas_map.values() if c is not None]
        df = df[colunas_existentes]

        # 🔹 GROUP BY
        colunas_grupo = [
            colunas_map["EMPRESA"],
            colunas_map["MES"],
            colunas_map["REGIONAL"],
            colunas_map["POLO"],
            colunas_map["MATRICULA"],
            colunas_map["NOME"],
        ]

        colunas_grupo = [c for c in colunas_grupo if c is not None]

        df_final = df.groupby(colunas_grupo, as_index=False).mean(numeric_only=True)

        # 🔹 EXPORTAR
        output = "resultado.xlsx"
        df_final.to_excel(output, index=False)

        return send_file(output, as_attachment=True)

    except Exception as e:
        print("ERRO REAL:", str(e))
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
