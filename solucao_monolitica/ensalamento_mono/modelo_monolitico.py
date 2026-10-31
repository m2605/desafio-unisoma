r"""
Modelo de Programação Linear Inteira Mista - formulação MONOLÍTICA
(implementação do documento "Modelo de Programação Linear Inteira Mista -
Otimização de Ensalamento de Alunos", docs/Modelo_Matematico_Colega.pdf).

Conjuntos e índices
    I            alunos matriculados (válidos), índice i
    I_M ⊆ I      meninos            (I_F = I \ I_M: meninas - não é usado no modelo)
    T            turnos {Manhã, Tarde}, índice t
    I_t ⊆ I      alunos do turno t
    J            todas as turmas, índice j
    J_t ⊆ J      turmas do turno t

Parâmetros
    C_t          vagas de cada turma do turno t
    P_t          proporção global de meninos no turno t
    W1 > W2 > W3 pesos da função objetivo

Variáveis
    x_ij ∈ {0,1} aluno i na turma j
    z_i  ∈ {0,1} aluno i sem turma (folga)
    D^t_max, D^t_min ≥ 0   maior / menor turma do turno t
    v ≥ 0        maior desvio absoluto (em nº de meninos) entre a turma e o esperado

Função objetivo (1)
    min Z = W1·Σ_i z_i + W2·Σ_t (D^t_max − D^t_min) + W3·v

Restrições
    (2) Σ_{j∈J} x_ij + z_i = 1                          ∀ i ∈ I
    (3) Σ_i x_ij ≤ C_t                                  ∀ t, j ∈ J_t
    (4) x_ij = 0                                        ∀ t, i ∈ I_t, j ∉ J_t
    (5) Σ_i x_ij ≤ D^t_max                              ∀ t, j ∈ J_t
    (6) Σ_i x_ij ≥ D^t_min                              ∀ t, j ∈ J_t
    (7) Σ_{i∈I_M} x_ij − P_t·Σ_i x_ij ≤ v               ∀ t, j ∈ J_t
    (8) P_t·Σ_i x_ij − Σ_{i∈I_M} x_ij ≤ v               ∀ t, j ∈ J_t

Correções opcionais (classe ``Opcoes``; todas ligadas por padrão, para cumprir
as regras do validador oficial):
    equilibrio_rigido     (9)  D^t_max − D^t_min ≤ 1                (regra hard do desafio)
    cobertura_rigida      (11) Σ_{i∈I_t} z_i ≤ max(0, |I_t| − |J_t|·C_t)
                          ninguém fica sem turma se houver vaga, mesmo quando o tempo
                          limite interrompe o solver (o ótimo do modelo original já cumpre)
    pesos_automaticos     W3 = 1;  W2 = W3·vmax + 1;  W1 = W2·Σ_t C_t + W3·vmax + 1
                          garante a hierarquia W1 ≫ W2 ≫ W3 (um termo menos importante
                          nunca compensa piorar um mais importante). Desligado: 10000/100/1.
    prioridade_matricula  no termo W1, z_i recebe peso w_i = |I_t| − posição(i):
                          se faltar vaga, saem os últimos matriculados.
    quebra_simetria       (10) Σ_i x_ij ≥ Σ_i x_i,j+1   (turmas do mesmo turno são idênticas)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pulp

from .etl import Aluno

TURNOS = ("Manhã", "Tarde")


class ErroOtimizacao(RuntimeError):
    pass


@dataclass
class Opcoes:
    equilibrio_rigido: bool = True
    cobertura_rigida: bool = True
    pesos_automaticos: bool = True
    prioridade_matricula: bool = True
    quebra_simetria: bool = True
    tempo_limite: float = 20.0

    @classmethod
    def original(cls) -> "Opcoes":
        """Exatamente o modelo do documento, sem nenhuma correção (pesos 10000/100/1)."""
        return cls(equilibrio_rigido=False, cobertura_rigida=False, pesos_automaticos=False,
                   prioridade_matricula=False, quebra_simetria=False)


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
    alocacao: dict[int, str]
    nao_alocados: list[Aluno]
    etapas: list[EtapaInfo] = field(default_factory=list)
    solver: str = ""
    status: str = ""
    n_variaveis: int = 0
    n_restricoes: int = 0
    segundos: float = 0.0


def _solver(tempo_limite: float):
    if "HiGHS" in pulp.listSolvers(onlyAvailable=True):
        return pulp.HiGHS(msg=False, timeLimit=tempo_limite, gapRel=0.0), "HiGHS"
    return pulp.PULP_CBC_CMD(msg=False, timeLimit=tempo_limite, gapRel=0.0), "CBC"


def nomes_das_turmas(n_manha: int, n_tarde: int) -> dict[str, list[str]]:
    """MANHÃ recebe as primeiras letras; TARDE continua a sequência."""
    letras = [chr(ord("A") + i) for i in range(n_manha + n_tarde)]
    return {"Manhã": [f"MANHÃ - {l}" for l in letras[:n_manha]],
            "Tarde": [f"TARDE - {l}" for l in letras[n_manha:]]}


def resolver(alunos: list[Aluno], config: dict[str, tuple[int, int]],
             opcoes: Opcoes | None = None) -> dict[str, ResultadoTurno]:
    """Resolve o modelo monolítico (os dois turnos num único MILP).

    config: {turno: (n_turmas, vagas_por_turma)}
    """
    op = opcoes or Opcoes()
    inicio = time.perf_counter()
    nomes = nomes_das_turmas(config["Manhã"][0], config["Tarde"][0])

    # ---------------- conjuntos ----------------
    I = sorted(alunos, key=lambda a: a.ordem)
    T = TURNOS
    I_t = {t: [a for a in I if a.turno == t] for t in T}
    I_M = {a.ordem for a in I if a.sexo == "M"}
    J_t = {t: list(nomes[t]) for t in T}
    J = [j for t in T for j in J_t[t]]
    C = {t: config[t][1] for t in T}
    P = {t: (sum(a.ordem in I_M for a in I_t[t]) / len(I_t[t]) if I_t[t] else 0.0) for t in T}
    turno_da_turma = {j: t for t in T for j in J_t[t]}

    res = {t: ResultadoTurno(turno=t, turmas=J_t[t], vagas=C[t], alocacao={}, nao_alocados=[])
           for t in T}
    if not I:
        for r in res.values():
            r.status = "Sem alunos"
        return res

    # ---------------- pesos ----------------
    vmax = max([C[t] for t in T if J_t[t]] or [1])
    if op.pesos_automaticos:
        W3 = 1.0
        W2 = W3 * vmax + 1
        W1 = W2 * sum(C[t] for t in T if J_t[t]) + W3 * vmax + 1
    else:
        W1, W2, W3 = 10000.0, 100.0, 1.0

    prob = pulp.LpProblem("Ensalamento_Monolitico", pulp.LpMinimize)

    # ---------------- variáveis ----------------
    jidx = {j: k for k, j in enumerate(J)}
    x = {(a.ordem, j): pulp.LpVariable(f"x_{a.ordem}_{jidx[j]}", cat=pulp.LpBinary)
         for a in I for j in J}
    z = {a.ordem: pulp.LpVariable(f"z_{a.ordem}", cat=pulp.LpBinary) for a in I}
    D_max = {t: pulp.LpVariable(f"Dmax_{k}", lowBound=0) for k, t in enumerate(T)}
    D_min = {t: pulp.LpVariable(f"Dmin_{k}", lowBound=0) for k, t in enumerate(T)}
    v = pulp.LpVariable("v", lowBound=0)

    # ---------------- função objetivo (1) ----------------
    if op.prioridade_matricula:
        peso_z = {}
        for t in T:
            n = len(I_t[t])
            for pos, a in enumerate(I_t[t]):
                peso_z[a.ordem] = n - pos            # 1º matriculado tem o maior peso
        termo_z = pulp.lpSum(peso_z[i] * z[i] for i in z)
    else:
        termo_z = pulp.lpSum(z.values())
    termo_D = pulp.lpSum(D_max[t] - D_min[t] for t in T if J_t[t])
    prob += W1 * termo_z + W2 * termo_D + W3 * v

    # ---------------- restrições ----------------
    for a in I:                                                                  # (2)
        prob += pulp.lpSum(x[a.ordem, j] for j in J) + z[a.ordem] == 1, f"R2_cobertura_{a.ordem}"
    for t in T:
        for a in I_t[t]:                                                         # (4)
            for j in J:
                if turno_da_turma[j] != t:
                    prob += x[a.ordem, j] == 0, f"R4_turno_{a.ordem}_{jidx[j]}"
        for k, j in enumerate(J_t[t]):
            S = pulp.lpSum(x[a.ordem, j] for a in I)
            S_M = pulp.lpSum(x[a.ordem, j] for a in I if a.ordem in I_M)
            prob += S <= C[t], f"R3_capacidade_{jidx[j]}"                        # (3)
            prob += S <= D_max[t], f"R5_dmax_{jidx[j]}"                          # (5)
            prob += S >= D_min[t], f"R6_dmin_{jidx[j]}"                          # (6)
            prob += S_M - P[t] * S <= v, f"R7_genero_pos_{jidx[j]}"              # (7)
            prob += P[t] * S - S_M <= v, f"R8_genero_neg_{jidx[j]}"              # (8)
            if op.quebra_simetria and k + 1 < len(J_t[t]):                       # (10)
                S_prox = pulp.lpSum(x[a.ordem, J_t[t][k + 1]] for a in I)
                prob += S >= S_prox, f"R10_simetria_{jidx[j]}"
        if op.equilibrio_rigido and J_t[t]:                                      # (9)
            prob += D_max[t] - D_min[t] <= 1, f"R9_equilibrio_{T.index(t)}"
        if op.cobertura_rigida:                                                  # (11)
            sobra = max(0, len(I_t[t]) - len(J_t[t]) * C[t])
            prob += pulp.lpSum(z[a.ordem] for a in I_t[t]) <= sobra, f"R11_cobertura_{T.index(t)}"

    # ---------------- solução ----------------
    # prob.sol_status: 1 = ótimo provado; 2 = solução viável sem prova (tempo esgotado);
    # 0 = nenhuma solução. Sem solução, tenta de novo com mais tempo (até 3 tentativas).
    t0 = time.perf_counter()
    limite = op.tempo_limite
    for _tentativa in range(3):
        solver, nome_solver = _solver(limite)
        prob.solve(solver)
        if prob.sol_status in (pulp.LpSolutionOptimal, pulp.LpSolutionIntegerFeasible) \
                and pulp.value(prob.objective) is not None:
            break
        if prob.status == pulp.LpStatusInfeasible:
            raise ErroOtimizacao("Modelo inviável: verifique turmas e vagas.")
        limite *= 2
    else:
        raise ErroOtimizacao("O solver não encontrou solução dentro do tempo limite.")
    seg = time.perf_counter() - t0
    if prob.sol_status == pulp.LpSolutionOptimal:
        st, status = "Optimal", "Ótimo (provado)"
    else:
        st, status = "Time limit", "Melhor solução encontrada no tempo limite (sem prova de ótimo)"

    for a in I:
        for j in J:
            if (x[a.ordem, j].value() or 0) > 0.5:
                res[turno_da_turma[j]].alocacao[a.ordem] = j
                break
        else:
            res[a.turno].nao_alocados.append(a)

    etapas = [
        EtapaInfo(f"Z = W1·Σz + W2·Σ(Dmax−Dmin) + W3·v  (W1={W1:g}, W2={W2:g}, W3={W3:g})",
                  round(pulp.value(prob.objective), 4), st, seg),
        EtapaInfo("  Σ z  (alunos sem turma)", sum(round(z[i].value() or 0) for i in z), st, 0.0),
        EtapaInfo("  Σ (Dmax − Dmin)  (diferença de tamanho)",
                  round(pulp.value(termo_D) or 0, 4), st, 0.0),
        EtapaInfo("  v  (maior desvio de meninos, em alunos)", round(v.value() or 0, 4), st, 0.0),
    ]
    total = time.perf_counter() - inicio
    for r in res.values():
        r.etapas = etapas
        r.solver = nome_solver
        r.status = status
        r.n_variaveis = len(prob.variables())
        r.n_restricoes = len(prob.constraints)
        r.segundos = total
    return res
