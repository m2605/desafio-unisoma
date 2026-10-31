# Desenho da Solução — Ensalamento ABC Aprendiz (Desafio UniSoma 2026)

## 1. O problema
Alocar os alunos matriculados nas turmas da **Manhã** e da **Tarde** de forma que:

| Tipo | Regra |
|---|---|
| **Hard** | Aluno só vai para turma do seu turno (disponibilidade) |
| **Hard** | Capacidade de cada turma (vagas) respeitada |
| **Hard** | Todo aluno válido alocado (se houver vaga) — homônimos são pessoas distintas |
| **Hard** | Equilíbrio de quantidade: diferença máx. de **1 aluno** entre turmas do mesmo turno |
| **Hard** | Nomenclatura contínua: `MANHÃ - A, B, …` e a tarde continua `TARDE - C, D, …` |
| **Soft** | Equilíbrio de gênero: proporção de meninos/meninas similar entre turmas do turno |
| **Soft** | Homônimos (possível duplicidade) em turmas diferentes, facilitando a conferência |
| **Soft** | Se faltar vaga, prioridade pela ordem de matrícula |

Como um aluno só pode ir para turmas do seu turno, o problema **se separa em dois subproblemas independentes** (Manhã e Tarde), resolvidos com o mesmo modelo.

## 2. Pipeline

```
Excel ─► ETL (limpeza + inconsistências) ─► MILP Fase 1 (dimensionamento) ─► MILP Fase 2 (atribuição) ─► Excel + Relatório PDF
```

**ETL**: padroniza `manha`/` TARDE`/`MANHÃ` → Manhã/Tarde e `feminino`/` F ` → F; acha abas e cabeçalho sem diferenciar maiúsculas/acentos; aceita números digitados como texto na aba Turmas. Linhas com nome vazio, sexo inválido (`X`, `?`, vazio) ou turno inválido (`Integral`, `Noite`, vazio) **não são alocadas** e vão para a aba *Inconsistências* — todas de uma só vez.

## 3. Modelo matemático (por turno)

### Conjuntos e parâmetros
- $I$: alunos válidos do turno; $I_F, I_M \subseteq I$ meninas/meninos
- $T$: turmas do turno; $C$: vagas por turma
- $w_i = |I| - \text{posição}(i)$: peso de prioridade (maior para quem se matriculou antes)
- $N = \min(|I|,\ |T|\cdot C)$: alunos que cabem
- $G$: grupos de homônimos (mesmo nome, 2+ pessoas)
- $p_F = |I_F|/|I|$: proporção de meninas do turno

### Fase 1 — Dimensionamento das turmas (MILP lexicográfico)
Variáveis: $z_i\in\{0,1\}$ (aluno recebe vaga); $f_t, m_t\in\mathbb{Z}_+$ (meninas/meninos na turma $t$); $S^+,S^-,F^+,F^-,M^+,M^-\ge 0$; $d_t\ge 0$.

$$
\begin{aligned}
&\textstyle\sum_i z_i = N && \text{(aloca todos que cabem)}\\
&\textstyle\sum_t f_t = \sum_{i\in I_F} z_i,\quad \sum_t m_t = \sum_{i\in I_M} z_i && \text{(conservação)}\\
&f_t + m_t \le C && \forall t\ \text{(capacidade)}\\
&S^- \le f_t+m_t \le S^+,\quad F^-\le f_t\le F^+,\quad M^-\le m_t\le M^+ && \forall t\ \text{(lineariza max/min)}\\
&S^+ - S^- \le 1 && \text{(equilíbrio de quantidade)}\\
&f_t+m_t \ge f_{t+1}+m_{t+1} && \text{(quebra de simetria)}\\
&\pm\big(f_t - p_F (f_t+m_t)\big) \le d_t && \forall t\ \text{(lineariza } |\cdot|)
\end{aligned}
$$

**Objetivo lexicográfico** (cada nível é otimizado e seu ótimo vira restrição do próximo):

| Nível | Objetivo | Significado |
|---|---|---|
| N1 (só se faltar vaga) | $\min \sum_i w_i(1-z_i)$ | quem fica sem vaga são os últimos matriculados |
| N2 | $\min S^+ - S^-$ | turmas do mesmo tamanho |
| N3 | $\min (F^+-F^-) + (M^+-M^-)$ | meninas e meninos espalhados igualmente |
| N4 | $\min \sum_t d_t$ | proporção de meninas de cada turma ≈ proporção do turno |

### Fase 2 — Atribuição aluno → turma (MILP)
Variáveis: $x_{i,t}\in\{0,1\}$, $u_g\ge 0$ (maior nº de homônimos do grupo $g$ numa mesma turma).

$$
\begin{aligned}
\min\ & \textstyle\sum_{g} u_g && \text{(espalhar homônimos entre turmas)}\\
\text{s.a. } & \textstyle\sum_t x_{i,t} = z_i^* && \forall i\\
& \textstyle\sum_{i\in I_F} x_{i,t} = f_t^*,\quad \sum_{i\in I_M} x_{i,t} = m_t^* && \forall t\\
& \textstyle\sum_{i\in g} x_{i,t} \le u_g && \forall g\in G,\ t
\end{aligned}
$$

### Por que a decomposição é exata (e rápida)
Alunos do mesmo sexo são intercambiáveis para os critérios N2–N4, portanto todo $(f^*, m^*)$ ótimo da Fase 1 é realizável por alguma atribuição individual; a Fase 2 escolhe a melhor delas para os homônimos. Sem a restrição de homônimos a Fase 2 é um **problema de transporte** (matriz totalmente unimodular → a relaxação linear já é inteira). A decomposição elimina a simetria do modelo $x_{i,t}$ puro (turmas idênticas geram $|T|!$ soluções equivalentes): **900 alunos em 26 turmas resolvidos em ~1 s**, contra >90 s sem solução no modelo monolítico.

## 4. Ferramentas
- **Python 3.12.9**, **PuLP** (modelagem), **HiGHS** (solver MILP branch-and-cut; CBC como alternativa)
- openpyxl (Excel), ReportLab + Matplotlib (relatório PDF), Tkinter (interface), PyInstaller (.exe)

## 5. Resultados nas instâncias fornecidas (validador oficial: todas APROVADAS)

| Instância | Alunos válidos | Turmas | Tamanhos | Maior desvio de gênero |
|---|---|---|---|---|
| 1 | 120/120 | 2+2 | 30/30 · 30/30 | 1,7 p.p. |
| 2 | 160/160 | 3+3 | 25/24/24 · 29/29/29 | 2,4 p.p. |
| 3 | 165/165 | 5+1 | 28×5 · 25 | 2,9 p.p. |
| 4 | 147/155 (8 inválidos) | 3+3 | 27/26/26 · 23/23/22 | 2,2 p.p. |

Os desvios restantes são o mínimo matematicamente possível (ex.: 61 meninos em 5 turmas → 13/12/12/12/12).
