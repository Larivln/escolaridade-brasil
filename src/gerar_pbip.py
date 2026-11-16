"""Gera o projeto Power BI (.pbip) do dashboard de escolaridade."""
import json, uuid, pathlib, sys

# --publico: grava um caminho genérico no parâmetro PastaDados (para subir no GitHub
# sem expor o seu usuário do Windows). Sem ele, grava a pasta real deste computador.
PUBLICO = "--publico" in sys.argv
ARGS = [a for a in sys.argv[1:] if a != "--publico"]
RAIZ = pathlib.Path(ARGS[0]) if ARGS else pathlib.Path(__file__).resolve().parent.parent
PASTA = "C:\\caminho\\para\\escolaridade-brasil\\dados\\" if PUBLICO else str((RAIZ / "dados").resolve()) + "\\"
OUT = RAIZ / "powerbi"
NOME = "Escolaridade"
T = "PNAD"


def w(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2)
    path.write_text(txt, encoding="utf-8")


# ---------------------------------------------------------------- modelo
# (nome no CSV, nome no modelo, tipo M, tipo modelo, oculta, sortBy, formato)
COLS = [
    ("ano", "Ano", "Int64.Type", "int64", False, None, "0"),
    ("trimestre", "Trimestre", "Int64.Type", "int64", True, None, "0"),
    ("periodo", "Período", "type text", "string", False, None, None),
    ("uf", "UF", "type text", "string", False, None, None),
    ("regiao", "Região", "type text", "string", False, None, None),
    ("genero", "Gênero", "type text", "string", False, None, None),
    ("cor_raca", "Cor/raça", "type text", "string", False, None, None),
    ("faixa_etaria_ordem", "faixa_etaria_ordem", "Int64.Type", "int64", True, None, "0"),
    ("faixa_etaria", "Faixa etária", "type text", "string", False, "faixa_etaria_ordem", None),
    ("escolaridade_ordem", "escolaridade_ordem", "Int64.Type", "int64", True, None, "0"),
    ("escolaridade", "Escolaridade", "type text", "string", False, "escolaridade_ordem", None),
    ("etapa_ensino", "Etapa de ensino", "type text", "string", False, "etapa_ensino_ordem", None),
    ("classe_ordem", "classe_ordem", "Int64.Type", "int64", True, None, "0"),
    ("classe_social", "Classe social", "type text", "string", False, "classe_ordem", None),
    ("populacao", "populacao", "type number", "double", True, None, "#,0"),
    ("amostra", "amostra", "Int64.Type", "int64", True, None, "#,0"),
    ("soma_anos_estudo", "soma_anos_estudo", "type number", "double", True, None, "#,0"),
    ("populacao_anos_estudo", "populacao_anos_estudo", "type number", "double", True, None, "#,0"),
    ("soma_renda", "soma_renda", "type number", "double", True, None, "#,0"),
    ("populacao_com_renda", "populacao_com_renda", "type number", "double", True, None, "#,0"),
]
pasta_m = PASTA.replace('"', '""')
tipos = ", ".join(f'{{"{c}", {mt}}}' for c, _, mt, *_ in COLS)
renomes = ", ".join(f'{{"{c}", "{n}"}}' for c, n, *_ in COLS if c != n)
M = [
    "let",
    f'    Fonte = Csv.Document(File.Contents(PastaDados & "escolaridade_powerbi.csv"), [Delimiter=";", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
    "    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),",
    f'    Tipos = Table.TransformColumnTypes(Cabecalhos, {{{tipos}}}, "pt-BR"),',
    '    EtapaOrdem = Table.AddColumn(Tipos, "etapa_ensino_ordem", each',
    '        if [etapa_ensino] = "Sem instrução" then 1',
    '        else if [etapa_ensino] = "Educação básica" then 2',
    '        else if [etapa_ensino] = "Ensino superior" then 3',
    '        else if [etapa_ensino] = "Pós-graduação" then 4',
    '        else 5, Int64.Type),',
    f"    Renomeado = Table.RenameColumns(EtapaOrdem, {{{renomes}}})",
    "in",
    "    Renomeado",
]

columns = []
for c, n, _, dt, hidden, sort, fmt in COLS:
    col = {"name": n, "dataType": dt, "sourceColumn": n,
           "summarizeBy": "none" if dt == "string" or hidden or c in ("ano", "trimestre") else "sum"}
    if hidden:
        col["isHidden"] = True
    if sort:
        col["sortByColumn"] = sort
    if fmt:
        col["formatString"] = fmt
    if c == "uf":
        col["dataCategory"] = "StateOrProvince"
    columns.append(col)
columns.append({"name": "etapa_ensino_ordem", "dataType": "int64", "sourceColumn": "etapa_ensino_ordem",
                "isHidden": True, "summarizeBy": "none", "formatString": "0"})

MEDIDAS = [
    ("População", f"SUM({T}[populacao])", "#,0"),
    ("% da População",
     f"DIVIDE([População], CALCULATE([População], ALL({T}[Escolaridade], {T}[escolaridade_ordem], "
     f"{T}[Etapa de ensino], {T}[etapa_ensino_ordem])))", "0.0%"),
    ("% Superior Completo",
     f"DIVIDE(\n    CALCULATE([População], {T}[escolaridade_ordem] >= 7),\n"
     f"    CALCULATE([População], {T}[escolaridade_ordem] >= 1)\n)", "0.0%"),
    ("% Pós-graduação",
     f"DIVIDE(\n    CALCULATE([População], {T}[escolaridade_ordem] >= 8),\n"
     f"    CALCULATE([População], {T}[escolaridade_ordem] >= 1)\n)", "0.0%"),
    ("Média Anos de Estudo",
     f"DIVIDE(SUM({T}[soma_anos_estudo]), SUM({T}[populacao_anos_estudo]))", "0.0"),
    ("Renda Média do Trabalho",
     f"DIVIDE(SUM({T}[soma_renda]), SUM({T}[populacao_com_renda]))", '"R$ "#,0.00'),
]
DESCR = {
    "% Superior Completo": "Pessoas com graduação completa ou mais (especialização, mestrado, doutorado), "
                           "entre quem tem nível de instrução informado.",
    "% Pós-graduação": "Pessoas com especialização, mestrado ou doutorado.",
}
measures = []
for n, expr, fmt in MEDIDAS:
    m = {"name": n, "expression": expr, "formatString": fmt}
    if n in DESCR:
        m["description"] = DESCR[n]
    measures.append(m)

model = {
    "compatibilityLevel": 1567,
    "model": {
        "culture": "pt-BR",
        "sourceQueryCulture": "pt-BR",
        "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
        "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "expressions": [{
            "name": "PastaDados",
            "kind": "m",
            "description": "Pasta onde está o escolaridade_powerbi.csv (termina com \\). Troque em Página Inicial > Transformar dados > Editar parâmetros.",
            "expression": f'"{pasta_m}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        }],
        "tables": [{
            "name": T,
            "columns": columns,
            "measures": measures,
            "partitions": [{"name": T, "mode": "import", "source": {"type": "m", "expression": M}}],
        }],
        "annotations": [
            {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            {"name": "PBI_QueryOrder", "value": json.dumps(["PastaDados", T])},
        ],
    },
}
SM = OUT / f"{NOME}.SemanticModel"
w(SM / "model.bim", model)
w(SM / "definition.pbism", {"version": "1.0", "settings": {}})


def platform(tipo):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": tipo, "displayName": NOME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, NOME + tipo))},
    }


w(SM / ".platform", platform("SemanticModel"))

# ---------------------------------------------------------------- relatório
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def ref(kind, prop):
    return {kind: {"Expression": {"SourceRef": {"Source": "e"}}, "Property": prop}}


def C(p):
    return ("Column", p)


def Me(p):
    return ("Measure", p)


def filtro_in(prop, valores):
    return {
        "Version": 2,
        "From": [{"Name": "e", "Entity": T, "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [ref("Column", prop)],
            "Values": [[{"Literal": {"Value": f"'{v}'"}}] for v in valores],
        }}}],
    }


_n = [0]


def visual(vtype, x, y, wd, h, proj=None, titulo=None, objects=None, order=None, vc=None):
    _n[0] += 1
    name = f"v{_n[0]:02d}{uuid.uuid5(uuid.NAMESPACE_URL, str(_n[0])).hex[:14]}"
    sv = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if proj:
        selects, projections, seen = [], {}, set()
        for role, items in proj.items():
            projections[role] = []
            for kind, prop in items:
                qn = f"{T}.{prop}"
                projections[role].append({"queryRef": qn, **({"active": True} if role == "Category" else {})})
                if qn not in seen:
                    seen.add(qn)
                    selects.append({**ref(kind, prop), "Name": qn, "NativeReferenceName": prop})
        q = {"Version": 2, "From": [{"Name": "e", "Entity": T, "Type": 0}], "Select": selects}
        if order:
            kind, prop, desc = order
            q["OrderBy"] = [{"Direction": 2 if desc else 1, "Expression": ref(kind, prop)}]
        sv["projections"] = projections
        sv["prototypeQuery"] = q
    if objects:
        sv["objects"] = objects
    vco = dict(vc or {})
    if titulo:
        vco["title"] = [{"properties": {"show": lit("true"), "text": lit(f"'{titulo}'")}}]
    if vco:
        sv["vcObjects"] = vco
    cfg = {"name": name, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": _n[0] * 100, "width": wd, "height": h}}],
           "singleVisual": sv}
    return {"x": x, "y": y, "z": _n[0] * 100, "width": wd, "height": h,
            "config": json.dumps(cfg, ensure_ascii=False), "filters": "[]"}


def texto(x, y, wd, h, s, size="20pt", bold=True, cor=None):
    style = {"fontSize": size}
    if bold:
        style["fontWeight"] = "bold"
    if cor:
        style["color"] = cor
    return visual("textbox", x, y, wd, h, objects={"general": [{"properties": {
        "paragraphs": [{"textRuns": [{"value": s, "textStyle": style}]}]}}]})


ADULTOS = ["25 a 39 anos", "40 a 59 anos", "60 anos ou mais"]


def slicer(x, y, wd, prop, selecao=None, unico=False):
    obj = {"data": [{"properties": {"mode": lit("'Dropdown'")}}]}
    if unico:
        obj["selection"] = [{"properties": {"singleSelect": lit("true")}}]
    if selecao:
        obj["general"] = [{"properties": {"filter": {"filter": filtro_in(prop, selecao)}}}]
    return visual("slicer", x, y, wd, 64, {"Values": [C(prop)]}, objects=obj)


def card(x, y, medida, rotulo):
    return visual("card", x, y, 297, 96, {"Values": [Me(medida)]},
                  objects={"labels": [{"properties": {"fontSize": lit("24D"),
                                                      **({"labelDisplayUnits": lit("1D")} if "Renda" in medida else {})}}],
                           "categoryLabels": [{"properties": {"show": lit("true")}}]},
                  vc={"border": [{"properties": {"show": lit("true"), "radius": lit("8D")}}]})


def rotulos():
    return {"labels": [{"properties": {"show": lit("true")}}]}


def filtros(slicers_props):
    out, x = [], 16
    largura = (1280 - 16 * 2 - 12 * (len(slicers_props) - 1)) // len(slicers_props)
    for p in slicers_props:
        sel = {"Faixa etária": ADULTOS, "Período": ["2023 T4"]}.get(p)
        out.append(slicer(x, 64, largura, p, sel, unico=(p == "Período")))
        x += largura + 12
    return out


pag1 = [texto(16, 8, 900, 48, "Escolaridade no Brasil — PNAD Contínua")]
pag1 += filtros(["Período", "Região", "UF", "Faixa etária", "Cor/raça"])
for i, (m, r) in enumerate([("População", "População"), ("% Superior Completo", "Superior completo"),
                            ("Média Anos de Estudo", "Anos de estudo"),
                            ("Renda Média do Trabalho", "Renda do trabalho")]):
    pag1.append(card(16 + i * 312, 140, m, r))
pag1 += [
    visual("hundredPercentStackedBarChart", 16, 248, 616, 200,
           {"Category": [C("Gênero")], "Series": [C("Etapa de ensino")], "Y": [Me("População")]},
           "Etapa de ensino por gênero", rotulos()),
    visual("hundredPercentStackedBarChart", 648, 248, 616, 200,
           {"Category": [C("Classe social")], "Series": [C("Etapa de ensino")], "Y": [Me("População")]},
           "Etapa de ensino por classe social"),
    visual("clusteredColumnChart", 16, 460, 616, 252,
           {"Category": [C("Classe social")], "Series": [C("Gênero")], "Y": [Me("% Superior Completo")]},
           "% com superior completo, por classe e gênero", rotulos()),
    visual("clusteredBarChart", 648, 460, 616, 252,
           {"Category": [C("UF")], "Y": [Me("% Superior Completo")]},
           "% com superior completo, por estado", rotulos(), order=("Measure", "% Superior Completo", True)),
]

pag2 = [texto(16, 8, 900, 48, "Raça, idade e renda")]
pag2 += filtros(["Período", "Região", "Faixa etária", "Gênero"])
pag2 += [
    visual("hundredPercentStackedBarChart", 16, 140, 1248, 250,
           {"Category": [C("Cor/raça")], "Series": [C("Escolaridade")], "Y": [Me("População")]},
           "Escolaridade por cor/raça"),
    visual("clusteredColumnChart", 16, 402, 616, 310,
           {"Category": [C("Cor/raça")], "Series": [C("Gênero")], "Y": [Me("Média Anos de Estudo")]},
           "Média de anos de estudo, por cor/raça e gênero", rotulos()),
    visual("clusteredColumnChart", 648, 402, 616, 310,
           {"Category": [C("Escolaridade")], "Y": [Me("Renda Média do Trabalho")]},
           "Renda média do trabalho, por escolaridade", rotulos()),
]


def secao(nome, titulo, visuais, ordem):
    return {"name": nome, "displayName": titulo, "displayOption": 1, "ordinal": ordem,
            "width": 1280, "height": 720, "config": "{}", "filters": "[]", "visualContainers": visuais}


report = {
    "config": json.dumps({"version": "5.43", "themeCollection": {}, "activeSectionIndex": 0,
                          "defaultDrillFilterOtherVisuals": True,
                          "settings": {"useStylableVisualContainerHeader": True}}),
    "layoutOptimization": 0,
    "sections": [secao("ReportSection1", "Visão geral", pag1, 0),
                 secao("ReportSection2", "Raça, idade e renda", pag2, 1)],
}
RP = OUT / f"{NOME}.Report"
w(RP / "report.json", report)
w(RP / "definition.pbir", {"version": "1.0", "datasetReference": {
    "byPath": {"path": f"../{NOME}.SemanticModel"}, "byConnection": None}})
w(RP / ".platform", platform("Report"))

w(OUT / f"{NOME}.pbip", {"version": "1.0", "artifacts": [{"report": {"path": f"{NOME}.Report"}}],
                         "settings": {"enableAutoRecovery": True}})
w(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
print("ok", OUT)
