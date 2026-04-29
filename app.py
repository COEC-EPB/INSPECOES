from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import unicodedata

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API online 🚀"


# 🔹 LIMPAR TEXTO
def limpar_texto(texto):
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto


# 🔹 NORMALIZAR COLUNAS
def normalizar_colunas(df):
    df.columns = [limpar_texto(c) for c in df.columns]
    return df


# 🔹 LER EXCEL INTELIGENTE (NUNCA QUEBRA)
def ler_excel_corrigido(file):
    try:
        df_raw = pd.read_excel(file, header=None)

        palavras_chave = ["MATRIC", "FUNC", "NOME", "MES"]

        header_row = None

        for i, row in df_raw.iterrows():
            valores = row.astype(str).apply(limpar_texto)
            texto = " ".join(valores)

            if any(p in texto for p in palavras_chave):
                header_row = i
                break

        if header_row is None:
            print("⚠️ Header não encontrado, usando linha 0")
            header_row = 0

        df = pd.read_excel(file, header=header_row)
        df = normalizar_colunas(df)

        return df

    except Exception as e:
        raise Exception(f"Erro ao ler Excel: {str(e)}")


# 🔹 ENCONTRAR COLUNA
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

        # 🔹 CONCATENAR MESES (PROTEGIDO)
        lista_df = []

        for f in arquivos:
            try:
                df = ler_excel_corrigido(f)
                lista_df.append(df)
            except Exception as e:
                return jsonify({
                    "erro": f"Erro no arquivo {f.filename}: {str(e)}"
                }), 400

        df_meses = pd.concat(lista_df, ignore_index=True)

        # 🔹 IPEO (PROTEGIDO)
        try:
            df_ipeo = ler_excel_corrigido(ipeo_file)
        except Exception as e:
            return jsonify({
                "erro": f"Erro no arquivo IPEO: {str(e)}"
            }), 400

        print("COLUNAS MESES:", df_meses.columns.tolist())
        print("COLUNAS IPEO:", df_ipeo.columns.tolist())

        # 🔹 MAPEAR COLUNAS CHAVE
        mapa_meses = {
            "MATRICULA": encontrar_coluna(df_meses, "MATRICULA"),
            "MES": encontrar_coluna(df_meses, "MES"),
        }

        mapa_ipeo = {
            "MATRICULA": encontrar_coluna(df_ipeo, "MATRICULA"),
            "MES": encontrar_coluna(df_ipeo, "MES"),
        }

        if not mapa_meses["MATRICULA"] or not mapa_meses["MES"]:
            return jsonify({"erro": "Colunas MATRICULA/MES não encontradas nos meses"}), 400

        if not mapa_ipeo["MATRICULA"] or not mapa_ipeo["MES"]:
            return jsonify({"erro": "Colunas MATRICULA/MES não encontradas no IPEO"}), 400

        # 🔹 PADRONIZAR NOMES
        df_meses = df_meses.rename(columns={
            mapa_meses["MATRICULA"]: "MATRICULA",
            mapa_meses["MES"]: "MES"
        })

        df_ipeo = df_ipeo.rename(columns={
            mapa_ipeo["MATRICULA"]: "MATRICULA",
            mapa_ipeo["MES"]: "MES"
        })

        # 🔹 MERGE
        df = df_meses.merge(df_ipeo, on=["MATRICULA", "MES"], how="inner")

        print("COLUNAS APÓS MERGE:", df.columns.tolist())

        # 🔹 FUNÇÃO AUXILIAR
        def get(nome):
            return encontrar_coluna(df, nome)

        # 🔹 MAPEAR COLUNAS FINAIS
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

        if len(colunas_existentes) == 0:
            return jsonify({"erro": "Nenhuma coluna válida encontrada após o merge"}), 400

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
