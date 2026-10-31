"""Gravação do resultado nas abas 'Ensalamento' e 'Inconsistências' do próprio Excel."""
from __future__ import annotations

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .etl import ALERTA, CORRIGIDO, ERRO, Cenario, normalizar

CABECALHO_ENSALAMENTO = ["Nome", "Sexo", "Disponibilidade", "Turma"]
CABECALHO_INCONSISTENCIAS = ["Tipo", "Aba", "Linha", "Nome", "Campo", "Valor encontrado",
                             "Descrição / Tratamento"]

_AZUL = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
_CORES_TIPO = {
    ERRO: PatternFill("solid", start_color="FFC7CE", end_color="FFC7CE"),
    ALERTA: PatternFill("solid", start_color="FFEB9C", end_color="FFEB9C"),
    CORRIGIDO: PatternFill("solid", start_color="DDEBF7", end_color="DDEBF7"),
}


class PlanilhaAbertaError(RuntimeError):
    pass


def _formatar_cabecalho(ws, larguras):
    for i, w in enumerate(larguras, start=1):
        c = ws.cell(row=1, column=i)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = _AZUL
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _corrigir_cabecalho_alunos(wb, cen: Cenario) -> None:
    """Se o título de alguma coluna da aba Alunos estiver errado, corrige só o título."""
    ws = next((w for w in wb.worksheets if normalizar(w.title) == "ALUNOS"), None)
    if ws is None:
        return
    for linha, coluna, titulo, inc in cen.titulos_a_corrigir:
        ws.cell(row=linha, column=coluna, value=titulo)
        letra = get_column_letter(coluna)
        inc.tipo = CORRIGIDO
        inc.descricao = (f"Título da coluna {letra} era {inc.valor}; corrigido para '{titulo}' "
                         "(somente o título; os dados dos alunos não foram alterados).")


def gravar(cen: Cenario, linhas_ensalamento: list[list[str]], caminho_saida: str | None = None) -> str:
    caminho_saida = caminho_saida or cen.caminho
    wb = load_workbook(cen.caminho)
    _corrigir_cabecalho_alunos(wb, cen)

    # remove versões anteriores das abas de resultado (ex.: rodada anterior / template)
    for ws in list(wb.worksheets):
        if normalizar(ws.title) in ("ENSALAMENTO", "INCONSISTENCIAS"):
            wb.remove(ws)

    ws = wb.create_sheet("Ensalamento")
    ws.append(CABECALHO_ENSALAMENTO)
    for linha in linhas_ensalamento:
        ws.append(linha)
    _formatar_cabecalho(ws, [45, 8, 17, 14])

    wi = wb.create_sheet("Inconsistências")
    wi.append(CABECALHO_INCONSISTENCIAS)
    ordem_tipo = {ERRO: 0, ALERTA: 1, CORRIGIDO: 2}
    incs = sorted(cen.inconsistencias,
                  key=lambda i: (ordem_tipo.get(i.tipo, 9), i.aba, i.linha or 0))
    if not incs:
        wi.append(["OK", "", "", "", "", "", "Nenhuma inconsistência encontrada nos dados de entrada."])
    for inc in incs:
        wi.append(inc.como_linha())
        fill = _CORES_TIPO.get(inc.tipo)
        if fill:
            wi.cell(row=wi.max_row, column=1).fill = fill
    _formatar_cabecalho(wi, [12, 10, 7, 40, 18, 22, 110])
    for row in wi.iter_rows(min_row=2, min_col=7, max_col=7):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")

    try:
        wb.save(caminho_saida)
    except PermissionError as exc:
        raise PlanilhaAbertaError(
            "Não foi possível salvar: a planilha parece estar aberta no Excel. "
            "Feche o arquivo e clique em 'Rodar ensalamento' novamente.") from exc
    finally:
        wb.close()
    return caminho_saida
