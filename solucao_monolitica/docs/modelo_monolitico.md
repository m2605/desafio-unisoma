# Modelo monolítico (solução principal)

Implementação de [`Modelo_Matematico_Colega.pdf`](Modelo_Matematico_Colega.pdf) em
[`ensalamento_mono/modelo_monolitico.py`](../ensalamento_mono/modelo_monolitico.py).
Os dois turnos são resolvidos **num único MILP**.

## Conjuntos
| Símbolo | Significado | Usado em |
|---|---|---|
| $I$ | alunos matriculados (válidos) | (2) |
| $I_M \subseteq I$ | meninos | (7), (8) |
| $I_F \subseteq I$ | meninas — definido no documento, **não usado** no modelo ($I_F = I \setminus I_M$) | — |
| $T$ | turnos {Manhã, Tarde} | $D^t$, $C_t$, $P_t$ |
| $I_t$ | alunos do turno $t$ | (4) |
| $J$, $J_t$ | turmas / turmas do turno $t$ | (2)–(8) |

## Parâmetros e variáveis
$C_t$ vagas por turma; $P_t$ proporção de meninos do turno; $W_1 > W_2 > W_3$ pesos.
$x_{ij}\in\{0,1\}$; $z_i\in\{0,1\}$ (aluno sem turma); $D^t_{max}, D^t_{min} \ge 0$; $v \ge 0$.

## Modelo do documento
$$\min Z = W_1\sum_i z_i + W_2\sum_t (D^t_{max}-D^t_{min}) + W_3\, v \qquad (1)$$

| Nº | Restrição |
|---|---|
| (2) | $\sum_{j\in J} x_{ij} + z_i = 1 \quad \forall i$ |
| (3) | $\sum_i x_{ij} \le C_t \quad \forall t, j\in J_t$ |
| (4) | $x_{ij} = 0 \quad \forall t, i\in I_t, j\notin J_t$ |
| (5)(6) | $D^t_{min} \le \sum_i x_{ij} \le D^t_{max} \quad \forall t, j\in J_t$ |
| (7)(8) | $\pm\big(\sum_{i\in I_M} x_{ij} - P_t\sum_i x_{ij}\big) \le v \quad \forall t, j\in J_t$ |

## Correções (classe `Opcoes`, todas ligadas por padrão; `Opcoes.original()` desliga todas)
| Opção | O que acrescenta | Por quê |
|---|---|---|
| `equilibrio_rigido` | (9) $D^t_{max}-D^t_{min} \le 1$ | o validador oficial **reprova** diferença > 1; no documento é só um peso |
| `cobertura_rigida` | (11) $\sum_{i\in I_t} z_i \le \max(0, \lvert I_t\rvert - \lvert J_t\rvert C_t)$ | sem ela, se o tempo limite interrompe o solver, a solução pode deixar alunos sem turma **havendo vaga** (observado: 895/900). Também deixa o modelo muito mais rápido (instância 3: 27 s → 1 s) |
| `pesos_automaticos` | $W_3=1$, $W_2=W_3 v_{max}+1$, $W_1=W_2\sum_t C_t+W_3 v_{max}+1$ | "W1 > W2 > W3" não basta: os pesos precisam garantir que um termo nunca compense o anterior |
| `prioridade_matricula` | $z_i$ com peso $w_i = \lvert I_t\rvert - \text{posição}(i)$ | se faltar vaga, saem os **últimos** matriculados (no original, a escolha é arbitrária) |
| `quebra_simetria` | (10) $\sum_i x_{ij} \ge \sum_i x_{i,j+1}$ | turmas do mesmo turno são idênticas; reduz a busca do branch-and-bound |

Status honesto: o PuLP reporta "Optimal" quando o HiGHS para por tempo; o código usa
`prob.sol_status` para distinguir **ótimo provado** de **melhor solução no tempo limite** e
repete com mais tempo (até 3×) se nenhuma solução foi encontrada.

## Desempenho (HiGHS, padrão `Opcoes()`)
| Instância | Tempo | Status | Validador |
|---|---|---|---|
| 1 | 0,1 s | ótimo provado | APROVADO |
| 2 | 0,3 s | ótimo provado | APROVADO |
| 3 | 1,1 s | ótimo provado | APROVADO |
| 4 | 0,4 s | ótimo provado | APROVADO |
| 900 alunos / 26 turmas (cenário extremo) | ~145 s | melhor solução no tempo limite | APROVADO |
