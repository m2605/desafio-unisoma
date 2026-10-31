"""
ETL: leitura, limpeza e validação da planilha de entrada.

Responsabilidades
-----------------
* localizar as abas ``Alunos`` e ``Turmas`` (sem diferenciar maiúsculas/acentos);
* localizar o cabeçalho (tolerando cabeçalho digitado errado);
* padronizar Sexo (M/F) e Disponibilidade (Manhã/Tarde);
* registrar TODAS as inconsistências de uma só vez (erros que impedem a
  alocação de um aluno, correções automáticas e alertas), para que a equipe
  da ONG não precise rodar o programa várias vezes até descobrir tudo.

Nenhuma decisão de alocação é tomada aqui: isso é papel do modelo matemático
(``modelo.py``).
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from openpyxl import load_workbook

# --------------------------------------------------------------------------- #
# Dicionários de padronização
# --------------------------------------------------------------------------- #
SEXOS = {"M": "M", "MASCULINO": "M", "F": "F", "FEMININO": "F"}
TURNOS = {"MANHA": "Manhã", "TARDE": "Tarde"}
PERIODO_ROTULO = {"Manhã": "MANHÃ", "Tarde": "TARDE"}
ORDEM_TURNOS = ("Manhã", "Tarde")
CHAVES_CONFIG = {
    "Manhã": ("turmas_manha", "vagas_manha"),
    "Tarde": ("turmas_tarde", "vagas_tarde"),
}

# Tipos de inconsistência
ERRO = "ERRO"            # impede a alocação (de um aluno ou do cenário)
CORRIGIDO = "CORRIGIDO"  # tratado automaticamente pelo programa
ALERTA = "ALERTA"        # não impede a alocação, mas merece conferência


@dataclass
class Inconsistencia:
    tipo: str
    aba: str
    linha: int | None
    nome: str
    campo: str
    valor: str
    descricao: str

    def como_linha(self) -> list[Any]:
        return [self.tipo, self.aba, self.linha if self.linha is not None else "",
                self.nome, self.campo, self.valor, self.descricao]


@dataclass
class Aluno:
    linha: int          # número da linha no Excel
    ordem: int          # ordem de matrícula (0, 1, 2, ...)
    nome: str
    sexo: str           # 'M' | 'F'
    turno: str          # 'Manhã' | 'Tarde'


@dataclass
class Cenario:
    caminho: str
    alunos: list[Aluno] = field(default_factory=list)
    config: dict[str, int] = field(default_factory=dict)
    inconsistencias: list[Inconsistencia] = field(default_factory=list)
    bloqueante: bool = False          # True => não dá para ensalar nada
    total_linhas: int = 0             # linhas de alunos lidas (não vazias)
    invalidos: int = 0                # linhas que não podem ser alocadas
    # títulos de coluna da aba Alunos a corrigir: (linha, coluna 1-based, título, inconsistência)
    titulos_a_corrigir: list[tuple[int, int, str, "Inconsistencia"]] = field(default_factory=list)

    def add(self, *args, **kwargs) -> None:
        self.inconsistencias.append(Inconsistencia(*args, **kwargs))

    def turnos_config(self) -> dict[str, tuple[int, int]]:
        """{turno: (n_turmas, vagas_por_turma)} – apenas se config válida."""
        return {t: (self.config.get(k1, 0), self.config.get(k2, 0))
                for t, (k1, k2) in CHAVES_CONFIG.items()}


# --------------------------------------------------------------------------- #
# Utilidades de texto
# --------------------------------------------------------------------------- #
def normalizar(valor: Any) -> str:
    """Maiúsculas, sem acentos e sem espaços extras: ' Manhã ' -> 'MANHA'."""
    if valor is None:
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def texto_celula(valor: Any) -> str:
    """Célula como texto limpo; 9018.0 vira '9018' e vazio vira ''."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        if valor != valor:  # NaN
            return ""
        if valor.is_integer():
            valor = int(valor)
    return " ".join(str(valor).split())


def mostrar(valor: Any) -> str:
    t = "" if valor is None else str(valor)
    return "(vazio)" if t.strip() == "" else repr(t)


def _achar_aba(wb, nome: str):
    alvo = normalizar(nome)
    for ws in wb.worksheets:
        if normalizar(ws.title) == alvo:
            return ws
    return None


# --------------------------------------------------------------------------- #
# Leitura da aba Turmas
# --------------------------------------------------------------------------- #
def _numero(valor: Any) -> float | None:
    if valor is None:
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    t = str(valor).strip().replace(" ", "")
    if not t:
        return None
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _ler_turmas(wb, cen: Cenario) -> None:
    ws = _achar_aba(wb, "Turmas")
    if ws is None:
        cen.add(ERRO, "Turmas", None, "", "Aba", "", "Aba 'Turmas' não encontrada. "
                "Crie a aba com as colunas Recursos/Quantidade (turmas_manha, turmas_tarde, "
                "vagas_manha, vagas_tarde).")
        cen.bloqueante = True
        return

    lidos: dict[str, tuple[int, Any]] = {}
    for num, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if not row or len(row) < 1:
            continue
        chave_raw = row[0]
        valor_raw = row[1] if len(row) > 1 else None
        chave = re.sub(r"[\s\-]+", "_", normalizar(chave_raw).lower()) if chave_raw is not None else ""
        if chave in ("", "recursos"):
            continue
        if chave in ("turmas_manha", "turmas_tarde", "vagas_manha", "vagas_tarde"):
            if chave in lidos:
                cen.add(ALERTA, "Turmas", num, "", chave, mostrar(valor_raw),
                        f"Recurso '{chave}' informado mais de uma vez; foi usado o valor da linha "
                        f"{lidos[chave][0]}.")
                continue
            lidos[chave] = (num, valor_raw)
            if texto_celula(chave_raw) != chave:
                cen.add(CORRIGIDO, "Turmas", num, "", "Recursos", mostrar(chave_raw),
                        f"Nome do recurso padronizado para '{chave}'.")

    for chave in ("turmas_manha", "turmas_tarde", "vagas_manha", "vagas_tarde"):
        if chave not in lidos:
            cen.add(ERRO, "Turmas", None, "", chave, "(ausente)",
                    f"Recurso '{chave}' não encontrado na aba 'Turmas'.")
            cen.bloqueante = True
            continue
        num, raw = lidos[chave]
        v = _numero(raw)
        if v is None:
            cen.add(ERRO, "Turmas", num, "", chave, mostrar(raw),
                    f"Quantidade de '{chave}' vazia ou não numérica.")
            cen.bloqueante = True
            continue
        if v < 0 or not float(v).is_integer():
            cen.add(ERRO, "Turmas", num, "", chave, mostrar(raw),
                    f"Quantidade de '{chave}' deve ser um número inteiro maior ou igual a zero.")
            cen.bloqueante = True
            continue
        if isinstance(raw, str):
            cen.add(CORRIGIDO, "Turmas", num, "", chave, mostrar(raw),
                    f"Valor digitado como texto convertido para o número {int(v)}.")
        cen.config[chave] = int(v)

    if cen.bloqueante:
        return

    total = cen.config["turmas_manha"] + cen.config["turmas_tarde"]
    if total > 26:
        cen.add(ERRO, "Turmas", None, "", "turmas_manha + turmas_tarde", str(total),
                "O total de turmas excede as 26 letras do alfabeto usadas na nomenclatura "
                "(MANHÃ - A ... TARDE - Z).")
        cen.bloqueante = True
    for turno, (kt, kv) in CHAVES_CONFIG.items():
        if cen.config[kt] > 0 and cen.config[kv] == 0:
            cen.add(ALERTA, "Turmas", lidos[kv][0], "", kv, "0",
                    f"Há {cen.config[kt]} turma(s) da {turno} configurada(s), mas com 0 vagas.")


# --------------------------------------------------------------------------- #
# Leitura da aba Alunos
# --------------------------------------------------------------------------- #
_CABECALHOS = {"NOME": "nome", "NOME DO ALUNO": "nome", "ALUNO": "nome", "SEXO": "sexo",
               "GENERO": "sexo", "DISPONIBILIDADE": "turno", "TURNO": "turno",
               "PERIODO": "turno"}


def _mapear_cabecalho(row: tuple) -> dict[str, int]:
    m: dict[str, int] = {}
    for idx, v in enumerate(row):
        campo = _CABECALHOS.get(normalizar(v))
        if campo and campo not in m:
            m[campo] = idx
    return m


def _ler_alunos(wb, cen: Cenario) -> None:
    ws = _achar_aba(wb, "Alunos")
    if ws is None:
        cen.add(ERRO, "Alunos", None, "", "Aba", "", "Aba 'Alunos' não encontrada.")
        cen.bloqueante = True
        return

    linhas = list(ws.iter_rows(values_only=True))
    if not linhas:
        cen.add(ERRO, "Alunos", None, "", "Aba", "", "Aba 'Alunos' está vazia.")
        cen.bloqueante = True
        return

    # Cabeçalho: procura nas 10 primeiras linhas a que tem mais títulos reconhecidos.
    melhor_idx, melhor_map = 0, _mapear_cabecalho(linhas[0])
    for i, row in enumerate(linhas[:10]):
        mp = _mapear_cabecalho(row)
        if len(mp) > len(melhor_map):
            melhor_idx, melhor_map = i, mp
    if len(melhor_map) == 0:
        melhor_idx = 0  # sem cabeçalho reconhecível: assume linha 1 e posições A/B/C
    cab = dict(melhor_map)
    faltando = [c for c in ("nome", "sexo", "turno") if c not in cab]
    if faltando:
        livres = [i for i in range(max(3, len(linhas[melhor_idx]))) if i not in cab.values()]
        padrao = {"nome": 0, "sexo": 1, "turno": 2}
        for c in faltando:
            idx = padrao[c] if padrao[c] in livres else livres[0]
            livres.remove(idx)
            cab[c] = idx
            titulo = linhas[melhor_idx][idx] if idx < len(linhas[melhor_idx]) else None
            rotulo = {"nome": "Nome", "sexo": "Sexo", "turno": "Disponibilidade"}[c]
            cen.add(ALERTA, "Alunos", melhor_idx + 1, "", "Cabeçalho", mostrar(titulo),
                    f"Coluna '{rotulo}' não encontrada pelo título; usada a coluna "
                    f"{chr(65 + idx)} (posição padrão do modelo). Corrija o título para '{rotulo}'.")
            cen.titulos_a_corrigir.append((melhor_idx + 1, idx + 1, rotulo, cen.inconsistencias[-1]))
    if melhor_idx > 0:
        cen.add(CORRIGIDO, "Alunos", melhor_idx + 1, "", "Cabeçalho", "",
                f"Cabeçalho encontrado na linha {melhor_idx + 1} (linhas acima foram ignoradas).")

    def cel(row, campo):
        i = cab[campo]
        return row[i] if i < len(row) else None

    nomes_linhas: dict[str, list[int]] = defaultdict(list)
    nomes_parecidos: dict[str, set[str]] = defaultdict(set)
    ordem = 0
    for idx in range(melhor_idx + 1, len(linhas)):
        row = linhas[idx]
        num = idx + 1
        if row is None or all(texto_celula(v) == "" for v in row):
            continue  # linha totalmente em branco
        nome_raw, sexo_raw, turno_raw = cel(row, "nome"), cel(row, "sexo"), cel(row, "turno")
        if all(texto_celula(v) == "" for v in (nome_raw, sexo_raw, turno_raw)):
            # Só há conteúdo fora das colunas usadas (ex.: anotações)
            cen.add(ALERTA, "Alunos", num, "", "Linha", "",
                    f"Linha {num} tem conteúdo apenas fora das colunas Nome/Sexo/Disponibilidade; ignorada.")
            continue
        cen.total_linhas += 1
        nome = texto_celula(nome_raw)
        sexo = SEXOS.get(normalizar(sexo_raw))
        turno = TURNOS.get(normalizar(turno_raw))
        ref = nome if nome else f"Linha {num}"
        problemas = []

        if not nome:
            problemas.append("nome")
            cen.add(ERRO, "Alunos", num, "", "Nome", "(vazio)",
                    f"Linha {num} sem nome do aluno: não pode ser ensalada. Preencha o nome.")
        elif isinstance(nome_raw, str) and nome_raw != nome:
            cen.add(CORRIGIDO, "Alunos", num, nome, "Nome", mostrar(nome_raw),
                    f"Espaços extras removidos do nome de {nome}.")
        if nome and not re.search(r"[A-Za-zÀ-ÿ]", nome):
            cen.add(ALERTA, "Alunos", num, nome, "Nome", mostrar(nome_raw),
                    f"Nome '{nome}' (linha {num}) não contém letras; confira o cadastro.")

        if sexo is None:
            problemas.append("sexo")
            cen.add(ERRO, "Alunos", num, nome, "Sexo", mostrar(sexo_raw),
                    f"{ref}: sexo inválido {mostrar(sexo_raw)} (esperado M ou F). "
                    "Aluno não ensalado até o cadastro ser corrigido.")
        elif texto_celula(sexo_raw) != sexo:
            cen.add(CORRIGIDO, "Alunos", num, nome, "Sexo", mostrar(sexo_raw),
                    f"{ref}: sexo {mostrar(sexo_raw)} interpretado como '{sexo}'.")

        if turno is None:
            problemas.append("turno")
            extra = ""
            if normalizar(turno_raw) in ("INTEGRAL", "NOITE", "NOTURNO", "AMBOS", "MANHA/TARDE",
                                         "MANHA E TARDE", "QUALQUER"):
                extra = " A ONG oferece apenas turmas da Manhã e da Tarde."
            cen.add(ERRO, "Alunos", num, nome, "Disponibilidade", mostrar(turno_raw),
                    f"{ref}: disponibilidade inválida {mostrar(turno_raw)} (esperado Manhã ou Tarde)."
                    f"{extra} Aluno não ensalado até o cadastro ser corrigido.")
        elif texto_celula(turno_raw) not in (turno, PERIODO_ROTULO[turno]):
            cen.add(CORRIGIDO, "Alunos", num, nome, "Disponibilidade", mostrar(turno_raw),
                    f"{ref}: disponibilidade {mostrar(turno_raw)} interpretada como '{turno}'.")

        if problemas:
            cen.invalidos += 1
            if nome and normalizar(nome) in ("TOTAL", "TOTAIS", "SOMA", "TOTAL GERAL"):
                cen.add(ALERTA, "Alunos", num, nome, "Linha", "",
                        f"Linha {num} ('{nome}') parece ser uma linha de totalização, não um aluno. "
                        "Remova-a da lista de matriculados.")
            continue

        cen.alunos.append(Aluno(linha=num, ordem=ordem, nome=nome, sexo=sexo, turno=turno))
        ordem += 1
        nomes_linhas[nome].append(num)
        nomes_parecidos[normalizar(nome)].add(nome)

    if cen.total_linhas == 0:
        cen.add(ERRO, "Alunos", None, "", "Aba", "", "Nenhum aluno encontrado na aba 'Alunos'.")
        cen.bloqueante = True

    # Homônimos / possíveis duplicidades
    por_nome = defaultdict(list)
    for a in cen.alunos:
        por_nome[a.nome].append(a)
    for nome, grupo in por_nome.items():
        if len(grupo) < 2:
            continue
        linhas_txt = ", ".join(str(a.linha) for a in grupo)
        iguais = len({(a.sexo, a.turno) for a in grupo}) == 1
        detalhe = ("mesmo sexo e mesmo turno: forte indício de cadastro duplicado"
                   if iguais else "dados diferentes: provavelmente pessoas distintas")
        for a in grupo:
            cen.add(ALERTA, "Alunos", a.linha, nome, "Nome", nome,
                    f"Nome repetido {len(grupo)}x (linhas {linhas_txt}) – {detalhe}. "
                    "Todos foram ensalados (em turmas diferentes sempre que possível); "
                    "confira se não é erro de cadastro.")
    for _, grafias in nomes_parecidos.items():
        if len(grafias) > 1:
            lista = " / ".join(sorted(grafias))
            for g in sorted(grafias):
                for ln in nomes_linhas[g]:
                    cen.add(ALERTA, "Alunos", ln, g, "Nome", g,
                            f"Nomes quase iguais (diferem só em maiúsculas/acentos): {lista}. "
                            "Possível duplicidade de cadastro; todos foram ensalados.")


# --------------------------------------------------------------------------- #
# Verificações de cenário (capacidade por turno)
# --------------------------------------------------------------------------- #
def _checar_capacidade(cen: Cenario) -> None:
    if cen.bloqueante:
        return
    for turno, (n_turmas, vagas) in cen.turnos_config().items():
        n = sum(1 for a in cen.alunos if a.turno == turno)
        cap = n_turmas * vagas
        if n > cap:
            cen.add(ERRO, "Turmas", None, "", f"vagas_{'manha' if turno == 'Manhã' else 'tarde'}",
                    f"{n} alunos / {cap} vagas",
                    f"Turno da {turno}: há {n} alunos válidos para apenas {cap} vagas "
                    f"({n_turmas} turma(s) x {vagas} vagas). {n - cap} aluno(s) ficarão sem turma "
                    "(os últimos pela ordem de matrícula). Abra novas turmas ou vagas e rode novamente.")


def ler_cenario(caminho: str) -> Cenario:
    """Lê a planilha e devolve o cenário limpo com todas as inconsistências."""
    cen = Cenario(caminho=caminho)
    try:
        wb = load_workbook(caminho, read_only=True, data_only=True)
    except Exception as exc:  # arquivo corrompido, não-xlsx etc.
        cen.add(ERRO, "Arquivo", None, "", "Arquivo", caminho,
                f"Não foi possível abrir a planilha: {exc}")
        cen.bloqueante = True
        return cen
    try:
        _ler_turmas(wb, cen)
        _ler_alunos(wb, cen)
    finally:
        wb.close()
    _checar_capacidade(cen)
    return cen
