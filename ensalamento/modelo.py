r"""
Modelo matemático de ensalamento - Programação Linear Inteira Mista (MILP).

O problema é separado por turno (um aluno só pode ir para turmas do seu turno,
logo Manhã e Tarde são independentes). Para cada turno usamos uma
DECOMPOSIÇÃO EXATA em duas fases, ambas resolvidas por solver MILP:

-----------------------------------------------------------------------------
FASE 1 - Modelo agregado de dimensionamento das turmas (MILP lexicográfico)
-----------------------------------------------------------------------------
Conjuntos   I (alunos do turno, ordem de matrícula), I_F / I_M, T (turmas)
Parâmetros  C vagas por turma; w_i = |I| − posição de i na ordem de matrícula
            (peso maior para quem se matriculou antes);
            N = min(|I|, |T|·C) alunos que cabem no turno
Variáveis   z_i ∈ {0,1}        aluno i recebe vaga no turno
            f_t, m_t ∈ Z+      nº de meninas / meninos na turma t
            S⁺,S⁻,F⁺,F⁻,M⁺,M⁻ ≥ 0   maior/menor valor entre as turmas
            d_t ≥ 0            desvio |f_t − p_F·(f_t+m_t)|
Restrições
    (1) Σ_i z_i = N                               aloca todos que cabem
    (2) Σ_t f_t = Σ_{i∈I_F} z_i ;  Σ_t m_t = Σ_{i∈I_M} z_i
    (3) f_t + m_t ≤ C                             capacidade
    (4) S⁻ ≤ f_t+m_t ≤ S⁺ ; F⁻ ≤ f_t ≤ F⁺ ; M⁻ ≤ m_t ≤ M⁺   (linearização max/min)
    (5) S⁺ − S⁻ ≤ 1                               equilíbrio de quantidade (hard)
    (6) f_t+m_t ≥ f_{t+1}+m_{t+1}                 quebra de simetria
    (7) ±(f_t − p_F·(f_t+m_t)) ≤ d_t              desvio de proporção
Objetivo lexicográfico (cada nível é otimizado e depois fixado):
    N1 (se faltar vaga) min Σ_i w_i·(1 − z_i)    -> saem os últimos matriculados
    N2 min S⁺ − S⁻                                equilíbrio de quantidade
    N3 min (F⁺ − F⁻) + (M⁺ − M⁻)                  equilíbrio de gênero
    N4 min Σ_t d_t                                proporção de meninas ≈ turno

-----------------------------------------------------------------------------
FASE 2 - Modelo de atribuição aluno -> turma (MILP)
-----------------------------------------------------------------------------
Variáveis   x_{i,t} ∈ {0,1};  u_g ≥ 0 (máx. de homônimos do grupo g numa turma)
    (8)  Σ_t x_{i,t} = z_i*                       ∀ i
    (9)  Σ_{i∈I_F} x_{i,t} = f_t* ; Σ_{i∈I_M} x_{i,t} = m_t*    ∀ t
    (10) Σ_{i∈g} x_{i,t} ≤ u_g                    ∀ g,t
Objetivo  min Σ_g u_g                             espalhar homônimos entre turmas

Por que a decomposição é exata: alunos do mesmo sexo são intercambiáveis para
os critérios N2-N4, então qualquer (f*, m*) ótimo da fase 1 é realizável por
alguma atribuição individual; a fase 2 escolhe, entre elas, a melhor para os
homônimos. Sem (10) a fase 2 é um problema de transporte (matriz totalmente
unimodular). A decomposição elimina a enorme simetria do modelo x_{i,t} puro
(turmas idênticas), permitindo resolver centenas de alunos em segundos.
Solver: HiGHS (branch-and-cut) via PuLP; CBC como alternativa.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pulp

from .etl import Aluno

class ErroOtimizacao(RuntimeError):
    pass


@dataclass
class EtapaInfo:
    nome: str
    valor: float
    status: str
    segundos: float


@dataclass
class ResultadoTurno:
    turno: str
    turmas: list[str]
    vagas: int
    alocacao: dict[int, str]            # ordem do aluno -> nome da turma
    nao_alocados: list[Aluno]
    etapas: list[EtapaInfo] = field(default_factory=list)
    solver: str = ""
    status: str = ""
    n_variaveis: int = 0
    n_restricoes: int = 0
    segundos: float = 0.0


def _solver(tempo_limite: float):
    """HiGHS em processo (sem janelas de console); CBC como reserva."""
    if "HiGHS" in pulp.listSolvers(onlyAvailable=True):
        return pulp.HiGHS(msg=False, timeLimit=tempo_limite, gapRel=0.0), "HiGHS"
    return pulp.PULP_CBC_CMD(msg=False, timeLimit=tempo_limite, gapRel=0.0), "CBC"


def _resolver(prob: pulp.LpProblem, solver, nome: str, expr, res: ResultadoTurno) -> float:
    t0 = time.perf_counter()
    prob.setObjective(expr)
    prob.solve(solver)
    st = pulp.LpStatus[prob.status]
    valor = pulp.value(expr)
    if valor is None or prob.status not in (pulp.LpStatusOptimal, pulp.LpStatusNotSolved):
        raise ErroOtimizacao(f"Solver não encontrou solução viável ({st}) em '{nome}'.")
    if prob.status != pulp.LpStatusOptimal:
        res.status = "Melhor solução no tempo limite"
    res.etapas.append(EtapaInfo(nome, round(float(valor), 4), st, time.perf_counter() - t0))
    return float(valor)


def resolver_turno(turno: str, alunos: list[Aluno], nomes_turmas: list[str], vagas: int,
                   tempo_limite: float = 60.0) -> ResultadoTurno:
    """Resolve o ensalamento ótimo de um turno (fase 1 + fase 2)."""
    inicio = time.perf_counter()
    res = ResultadoTurno(turno=turno, turmas=list(nomes_turmas), vagas=vagas,
                         alocacao={}, nao_alocados=[], status="Ótimo")
    I = sorted(alunos, key=lambda a: a.ordem)
    T = list(range(len(nomes_turmas)))
    if not I:
        res.status = "Sem alunos"
        return res
    if not T or vagas <= 0:
        res.nao_alocados = I
        res.status = "Sem turmas/vagas"
        return res

    solver, res.solver = _solver(tempo_limite)
    cap_total = len(T) * vagas
    N = min(len(I), cap_total)
    sufixo = "Manha" if turno == "Manhã" else "Tarde"

    # ============================ FASE 1 ============================ #
    p1 = pulp.LpProblem(f"Fase1_Dimensionamento_{sufixo}", pulp.LpMinimize)
    z = {a.ordem: pulp.LpVariable(f"z_{a.ordem}", cat=pulp.LpBinary) for a in I}
    f = {t: pulp.LpVariable(f"f_{t}", lowBound=0, upBound=vagas, cat=pulp.LpInteger) for t in T}
    m = {t: pulp.LpVariable(f"m_{t}", lowBound=0, upBound=vagas, cat=pulp.LpInteger) for t in T}
    S_max, S_min = pulp.LpVariable("S_max", 0), pulp.LpVariable("S_min", 0)
    F_max, F_min = pulp.LpVariable("F_max", 0), pulp.LpVariable("F_min", 0)
    M_max, M_min = pulp.LpVariable("M_max", 0), pulp.LpVariable("M_min", 0)
    d = {t: pulp.LpVariable(f"d_{t}", 0) for t in T}

    p1 += pulp.lpSum(z.values()) == N, "aloca_todos_que_cabem"
    p1 += pulp.lpSum(f.values()) == pulp.lpSum(z[a.ordem] for a in I if a.sexo == "F"), "total_F"
    p1 += pulp.lpSum(m.values()) == pulp.lpSum(z[a.ordem] for a in I if a.sexo == "M"), "total_M"
    n_f = sum(1 for a in I if a.sexo == "F")
    p_f = n_f / len(I)
    for t in T:
        s_t = f[t] + m[t]
        p1 += s_t <= vagas, f"capacidade_{t}"
        p1 += s_t <= S_max, f"smax_{t}"
        p1 += s_t >= S_min, f"smin_{t}"
        p1 += f[t] <= F_max, f"fmax_{t}"
        p1 += f[t] >= F_min, f"fmin_{t}"
        p1 += m[t] <= M_max, f"mmax_{t}"
        p1 += m[t] >= M_min, f"mmin_{t}"
        p1 += f[t] - p_f * s_t <= d[t], f"desvio_pos_{t}"
        p1 += p_f * s_t - f[t] <= d[t], f"desvio_neg_{t}"
    p1 += S_max - S_min <= 1, "equilibrio_quantidade"
    for t in T[:-1]:
        p1 += f[t] + m[t] >= f[t + 1] + m[t + 1], f"simetria_{t}"
    if N == len(I):  # todos cabem: z fixo em 1 (o nível N1 é trivial)
        for a in I:
            z[a.ordem].lowBound = 1

    niveis = []
    if N < len(I):
        # peso maior para quem se matriculou antes: w_i = |I| - posição(i)
        niveis.append(("N1 Prioridade por ordem de matrícula",
                       pulp.lpSum((len(I) - pos) * (1 - z[a.ordem]) for pos, a in enumerate(I))))
    niveis += [("N2 Amplitude de quantidade (S+ - S-)", S_max - S_min),
               ("N3 Amplitude de gênero (F+ - F-) + (M+ - M-)", (F_max - F_min) + (M_max - M_min)),
               ("N4 Desvio da proporção de meninas", pulp.lpSum(d.values()))]
    for k, (nome, expr) in enumerate(niveis):
        v = _resolver(p1, solver, nome, expr, res)
        if k < len(niveis) - 1:
            # N1..N3 têm valor ótimo inteiro: fixa exatamente (sem tolerância numérica)
            p1 += expr <= round(v), f"fixa_{nome.split()[0]}"

    z_ot = {i: int(round(z[i].value() or 0)) for i in z}
    f_ot = {t: int(round(f[t].value() or 0)) for t in T}
    m_ot = {t: int(round(m[t].value() or 0)) for t in T}
    nvar, nres = len(p1.variables()), len(p1.constraints)

    # ============================ FASE 2 ============================ #
    p2 = pulp.LpProblem(f"Fase2_Atribuicao_{sufixo}", pulp.LpMinimize)
    sel = [a for a in I if z_ot[a.ordem] == 1]
    x = {(a.ordem, t): pulp.LpVariable(f"x_{a.ordem}_{t}", cat=pulp.LpBinary) for a in sel for t in T}
    for a in sel:
        p2 += pulp.lpSum(x[a.ordem, t] for t in T) == 1, f"uma_turma_{a.ordem}"
    for t in T:
        p2 += pulp.lpSum(x[a.ordem, t] for a in sel if a.sexo == "F") == f_ot[t], f"meninas_{t}"
        p2 += pulp.lpSum(x[a.ordem, t] for a in sel if a.sexo == "M") == m_ot[t], f"meninos_{t}"
    grupos: dict[str, list[Aluno]] = {}
    for a in sel:
        grupos.setdefault(a.nome, []).append(a)
    # u_g = maior nº de homônimos do grupo g numa mesma turma (min -> espalha o grupo)
    u = []
    for gi, membros in enumerate(g for g in grupos.values() if len(g) > 1):
        ug = pulp.LpVariable(f"u_{gi}", 0)
        u.append(ug)
        for t in T:
            p2 += pulp.lpSum(x[a.ordem, t] for a in membros) <= ug, f"homonimos_{gi}_{t}"
    if not u:  # sem homônimos: objetivo nulo, basta uma atribuição viável
        u.append(pulp.LpVariable("u_nulo", 0, 0))
    _resolver(p2, solver, "Fase 2: atribuição (máx. homônimos por turma)", pulp.lpSum(u), res)

    for a in I:
        if z_ot[a.ordem] != 1:
            res.nao_alocados.append(a)
            continue
        for t in T:
            if (x[a.ordem, t].value() or 0) > 0.5:
                res.alocacao[a.ordem] = nomes_turmas[t]
                break
        else:
            raise ErroOtimizacao(f"Aluno {a.nome} sem turma na solução da fase 2.")

    res.n_variaveis = nvar + len(p2.variables())
    res.n_restricoes = nres + len(p2.constraints)
    res.segundos = time.perf_counter() - inicio
    return res


def nomes_das_turmas(n_manha: int, n_tarde: int) -> dict[str, list[str]]:
    """Nomenclatura contínua: manhã recebe as primeiras letras, tarde continua."""
    letras = [chr(ord("A") + i) for i in range(n_manha + n_tarde)]
    return {"Manhã": [f"MANHÃ - {l}" for l in letras[:n_manha]],
            "Tarde": [f"TARDE - {l}" for l in letras[n_manha:]]}
