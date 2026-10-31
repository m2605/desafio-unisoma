"""Orquestra ETL -> modelo de otimização -> gravação no Excel -> relatório."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable

from .etl import ERRO, ORDEM_TURNOS, Cenario, ler_cenario
from .modelo_monolitico import Opcoes, ResultadoTurno, nomes_das_turmas, resolver
from .saida import gravar


@dataclass
class EstatTurma:
    turma: str
    turno: str
    vagas: int
    total: int
    meninos: int
    meninas: int

    @property
    def pct_meninas(self) -> float:
        return self.meninas / self.total if self.total else 0.0


@dataclass
class Resultado:
    cenario: Cenario
    turnos: dict[str, ResultadoTurno] = field(default_factory=dict)
    linhas: list[list[str]] = field(default_factory=list)
    estatisticas: list[EstatTurma] = field(default_factory=list)
    caminho_excel: str = ""
    caminho_relatorio: str = ""
    segundos: float = 0.0

    @property
    def ensalados(self) -> int:
        return len(self.linhas)

    @property
    def nao_ensalados_sem_vaga(self) -> int:
        return sum(len(r.nao_alocados) for r in self.turnos.values())

    def contagem(self, tipo: str) -> int:
        return sum(1 for i in self.cenario.inconsistencias if i.tipo == tipo)


def executar(caminho: str, gerar_relatorio: bool = True, caminho_saida: str | None = None,
             progresso: Callable[[str], None] | None = None,
             opcoes: Opcoes | None = None) -> Resultado:
    t0 = time.perf_counter()
    log = progresso or (lambda _m: None)

    log("Lendo e validando a planilha...")
    cen = ler_cenario(caminho)
    res = Resultado(cenario=cen)

    if not cen.bloqueante:
        cfg = cen.turnos_config()
        nomes = nomes_das_turmas(cfg["Manhã"][0], cfg["Tarde"][0])
        log(f"Otimizando os dois turnos num único modelo ({len(cen.alunos)} alunos, "
            f"{cfg['Manhã'][0] + cfg['Tarde'][0]} turmas)...")
        res.turnos = resolver(cen.alunos, cfg, opcoes)
        for turno in ORDEM_TURNOS:
            n_turmas, vagas = cfg[turno]
            r = res.turnos[turno]
            for a in r.nao_alocados:
                if n_turmas == 0 or vagas == 0:
                    cen.add(ERRO, "Alunos", a.linha, a.nome, "Disponibilidade", turno,
                            f"{a.nome}: não há turmas/vagas configuradas para a {turno}; "
                            "aluno não ensalado.")
                else:
                    cen.add(ERRO, "Alunos", a.linha, a.nome, "Vaga", turno,
                            f"{a.nome}: sem vaga no turno da {turno} (turno lotado; "
                            "prioridade pela ordem de matrícula). Aluno não ensalado.")

        # Ensalamento na ordem original da lista de matriculados
        aloc = {}
        for r in res.turnos.values():
            aloc.update(r.alocacao)
        for a in cen.alunos:
            if a.ordem in aloc:
                res.linhas.append([a.nome, a.sexo, a.turno, aloc[a.ordem]])

        for turno in ORDEM_TURNOS:
            n_turmas, vagas = cfg[turno]
            for nome_t in nomes[turno]:
                membros = [a for a in cen.alunos if aloc.get(a.ordem) == nome_t]
                res.estatisticas.append(EstatTurma(
                    turma=nome_t, turno=turno, vagas=vagas, total=len(membros),
                    meninos=sum(a.sexo == "M" for a in membros),
                    meninas=sum(a.sexo == "F" for a in membros)))
    else:
        log("Foram encontrados erros que impedem o ensalamento.")

    log("Gravando abas 'Ensalamento' e 'Inconsistências'...")
    res.caminho_excel = gravar(cen, res.linhas, caminho_saida)
    res.segundos = time.perf_counter() - t0

    if gerar_relatorio:
        log("Gerando relatório resumo (PDF)...")
        from .relatorio import gerar_pdf
        base = os.path.splitext(res.caminho_excel)[0]
        res.caminho_relatorio = gerar_pdf(res, base + "_relatorio.pdf")
    log("Concluído.")
    return res
