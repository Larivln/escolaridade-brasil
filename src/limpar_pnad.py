"""
Limpeza dos microdados da PNAD Contínua trimestral (IBGE) para o Power BI.

Lê os arquivos PNADC_*.zip (direto do zip, sem precisar extrair), fica só com
as colunas que interessam, traduz os códigos para texto e grava uma tabela
resumida em dados/escolaridade_powerbi.csv.

Uso:
    python src/limpar_pnad.py                 (procura os zips em dados/ e em Downloads)
    python src/limpar_pnad.py caminho1.zip caminho2.zip
"""
import csv
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "escolaridade_powerbi.csv"

# Posições das colunas no arquivo de largura fixa (início, fim) contando do zero.
COL = {
    "ano": (0, 4), "trimestre": (4, 5), "uf": (5, 7),
    "upa": (11, 20), "v1008": (27, 29), "v1014": (29, 31),   # identificam o domicílio
    "peso": (49, 64),          # V1028 - peso da pessoa (com calibração)
    "cond_dom": (92, 94),      # V2005 - condição no domicílio
    "sexo": (94, 95),          # V2007
    "idade": (103, 106),       # V2009
    "cor": (106, 107),         # V2010
    "frequenta": (108, 109),   # V3002 - frequenta escola (1 sim, 2 não)
    "curso_ant": (124, 126),   # V3009A - curso mais elevado que frequentou antes
    "concluiu": (134, 135),    # V3014 - concluiu esse curso (1 sim, 2 não)
    "instrucao": (404, 405),   # VD3004 - nível de instrução
    "anos_estudo": (405, 407), # VD3005
    "renda": (443, 451),       # VD4019 - rendimento habitual de todos os trabalhos
}

SALARIO_MINIMO = {2019: 998, 2020: 1045, 2021: 1100, 2022: 1212, 2023: 1320, 2024: 1412, 2025: 1518}

SEXO = {"1": "Masculino", "2": "Feminino"}
COR = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indígena", "9": "Ignorado"}
INSTRUCAO = {
    "1": "Sem instrução",
    "2": "Fundamental incompleto",
    "3": "Fundamental completo",
    "4": "Médio incompleto",
    "5": "Médio completo",
    "6": "Superior incompleto",
    "7": "Superior completo",
    " ": "Não se aplica (menor de 5 anos)",
}
# Escolaridade detalhada: ordem -> nome (abre o superior completo em graduação e pós)
ESCOLARIDADE = {
    0: "Não se aplica (menor de 5 anos)",
    1: "Sem instrução",
    2: "Fundamental incompleto",
    3: "Fundamental completo",
    4: "Médio incompleto",
    5: "Médio completo",
    6: "Superior incompleto",
    7: "Superior completo (graduação)",
    8: "Especialização",
    9: "Mestrado",
    10: "Doutorado",
}
ETAPA = {0: "Não se aplica", 1: "Sem instrução", 2: "Educação básica", 3: "Educação básica",
         4: "Educação básica", 5: "Educação básica", 6: "Ensino superior", 7: "Ensino superior",
         8: "Pós-graduação", 9: "Pós-graduação", 10: "Pós-graduação"}
POS = {"13": 8, "14": 9, "15": 10}


def escolaridade_ordem(instrucao, frequenta, curso_ant, concluiu):
    """Nível mais alto CONCLUÍDO. Pós só conta se a pessoa não estuda mais e concluiu o curso."""
    if instrucao == " ":
        return 0
    if instrucao == "7" and frequenta == "2" and concluiu == "1" and curso_ant in POS:
        return POS[curso_ant]
    return int(instrucao)
UF = {
    "11": ("Rondônia", "Norte"), "12": ("Acre", "Norte"), "13": ("Amazonas", "Norte"),
    "14": ("Roraima", "Norte"), "15": ("Pará", "Norte"), "16": ("Amapá", "Norte"),
    "17": ("Tocantins", "Norte"),
    "21": ("Maranhão", "Nordeste"), "22": ("Piauí", "Nordeste"), "23": ("Ceará", "Nordeste"),
    "24": ("Rio Grande do Norte", "Nordeste"), "25": ("Paraíba", "Nordeste"),
    "26": ("Pernambuco", "Nordeste"), "27": ("Alagoas", "Nordeste"), "28": ("Sergipe", "Nordeste"),
    "29": ("Bahia", "Nordeste"),
    "31": ("Minas Gerais", "Sudeste"), "32": ("Espírito Santo", "Sudeste"),
    "33": ("Rio de Janeiro", "Sudeste"), "35": ("São Paulo", "Sudeste"),
    "41": ("Paraná", "Sul"), "42": ("Santa Catarina", "Sul"), "43": ("Rio Grande do Sul", "Sul"),
    "50": ("Mato Grosso do Sul", "Centro-Oeste"), "51": ("Mato Grosso", "Centro-Oeste"),
    "52": ("Goiás", "Centro-Oeste"), "53": ("Distrito Federal", "Centro-Oeste"),
}
# Classe pela renda domiciliar do trabalho, em salários mínimos (SM) do ano.
CLASSES = [
    (1, "Sem renda do trabalho"),
    (2, "E (até 2 SM)"),
    (3, "D (2 a 4 SM)"),
    (4, "C (4 a 10 SM)"),
    (5, "B (10 a 20 SM)"),
    (6, "A (mais de 20 SM)"),
]
FAIXAS = [(0, 13, "0 a 13 anos"), (14, 17, "14 a 17 anos"), (18, 24, "18 a 24 anos"),
          (25, 39, "25 a 39 anos"), (40, 59, "40 a 59 anos"), (60, 999, "60 anos ou mais")]


def faixa_etaria(idade):
    for ordem, (ini, fim, nome) in enumerate(FAIXAS, start=1):
        if ini <= idade <= fim:
            return ordem, nome
    raise ValueError(idade)


def classe_social(renda_domicilio, sm):
    if renda_domicilio <= 0:
        return CLASSES[0]
    x = renda_domicilio / sm
    if x <= 2:
        return CLASSES[1]
    if x <= 4:
        return CLASSES[2]
    if x <= 10:
        return CLASSES[3]
    if x <= 20:
        return CLASSES[4]
    return CLASSES[5]


def ler_zip(caminho):
    """Devolve (pessoas, renda_por_domicilio) de um zip da PNADC."""
    pessoas = []
    renda_dom = defaultdict(float)
    descartadas = 0
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".txt"))
        with z.open(nome) as f:
            for bruto in f:
                linha = bruto[:460].decode("latin1")
                c = {k: linha[a:b] for k, (a, b) in COL.items()}
                try:
                    peso = float(c["peso"])
                    idade = int(c["idade"])
                except ValueError:
                    descartadas += 1
                    continue
                if c["sexo"] not in SEXO or c["uf"] not in UF or c["instrucao"] not in INSTRUCAO:
                    descartadas += 1
                    continue
                renda = float(c["renda"]) if c["renda"].strip() else None
                anos = int(c["anos_estudo"]) if c["anos_estudo"].strip() else None
                dom = (c["upa"], c["v1008"], c["v1014"])
                # Pensionista, empregado doméstico e parente do empregado não entram na renda do domicílio
                if renda and c["cond_dom"] not in ("17", "18", "19"):
                    renda_dom[dom] += renda
                pessoas.append((int(c["ano"]), int(c["trimestre"]), c["uf"], c["sexo"], c["cor"],
                                idade,
                                escolaridade_ordem(c["instrucao"], c["frequenta"], c["curso_ant"], c["concluiu"]),
                                anos, renda, peso, dom))
    return pessoas, renda_dom, descartadas


def br(x, casas=2):
    """Número no formato brasileiro (vírgula decimal) para o Power BI em pt-BR."""
    return f"{x:.{casas}f}".replace(".", ",")


def main():
    zips = [Path(a) for a in sys.argv[1:]]
    if not zips:
        zips = sorted((RAIZ / "dados").glob("PNADC_*.zip")) + sorted((Path.home() / "Downloads").glob("PNADC_*.zip"))
    if not zips:
        sys.exit("Nenhum arquivo PNADC_*.zip encontrado em dados/ nem em Downloads.")

    # chave -> [população, amostra, soma(anos*peso), peso c/ anos, soma(renda*peso), peso c/ renda]
    tabela = defaultdict(lambda: [0.0, 0, 0.0, 0.0, 0.0, 0.0])

    for caminho in zips:
        print(f"Lendo {caminho.name} ...")
        pessoas, renda_dom, descartadas = ler_zip(caminho)
        pop = pop25 = sup25 = pos25 = soma_renda = peso_renda = 0.0
        for ano, tri, uf, sexo, cor, idade, instr, anos, renda, peso, dom in pessoas:
            sm = SALARIO_MINIMO[ano]
            chave = (ano, tri, uf, sexo, cor, faixa_etaria(idade), instr, classe_social(renda_dom.get(dom, 0.0), sm))
            t = tabela[chave]
            t[0] += peso
            t[1] += 1
            if anos is not None:
                t[2] += anos * peso
                t[3] += peso
            if renda:
                t[4] += renda * peso
                t[5] += peso
                soma_renda += renda * peso
                peso_renda += peso
            pop += peso
            if idade >= 25:
                pop25 += peso
                sup25 += peso if instr >= 7 else 0
                pos25 += peso if instr >= 8 else 0
        print(f"  linhas lidas: {len(pessoas):,} | descartadas (inválidas): {descartadas}")
        print(f"  população estimada: {pop/1e6:.1f} milhões")
        print(f"  renda média habitual do trabalho: R$ {soma_renda/peso_renda:,.0f}")
        print(f"  25 anos ou mais com superior completo: {100*sup25/pop25:.1f}%")
        print(f"  25 anos ou mais com pós-graduação concluída: {100*pos25/pop25:.1f}%")

    SAIDA.parent.mkdir(exist_ok=True)
    with open(SAIDA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "trimestre", "periodo", "uf", "regiao", "genero", "cor_raca",
                    "faixa_etaria_ordem", "faixa_etaria", "escolaridade_ordem", "escolaridade", "etapa_ensino",
                    "classe_ordem", "classe_social", "populacao", "amostra",
                    "soma_anos_estudo", "populacao_anos_estudo", "soma_renda", "populacao_com_renda"])
        for (ano, tri, uf, sexo, cor, (fo, fn), instr, (co, cn)), t in sorted(tabela.items()):
            w.writerow([ano, tri, f"{ano} T{tri}", UF[uf][0], UF[uf][1], SEXO[sexo], COR.get(cor, "Ignorado"),
                        fo, fn, instr, ESCOLARIDADE[instr], ETAPA[instr], co, cn,
                        br(t[0]), t[1], br(t[2]), br(t[3]), br(t[4]), br(t[5])])
    print(f"\nGravado: {SAIDA}  ({len(tabela):,} linhas)")


if __name__ == "__main__":
    main()
