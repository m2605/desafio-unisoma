# Desafio UniSoma 2026 — Ensalamento ABC Aprendiz

Aplicativo que distribui automaticamente os alunos matriculados da **ABC Aprendiz** nas turmas da
Manhã e da Tarde usando **otimização matemática (Programação Linear Inteira Mista – MILP)**.

- ✅ Respeita turno, capacidade e nomenclatura (`MANHÃ - A`, `MANHÃ - B`, `TARDE - C`, …)
- ✅ Turmas do mesmo turno com no máximo **1 aluno de diferença**
- ✅ Proporção de meninos/meninas **ótima** em cada turma
- ✅ Detecta e explica **todas** as inconsistências de uma vez (aba *Inconsistências*)
- ✅ Gera **Relatório Resumo em PDF** com gráficos
- ✅ Executável único (`Ensalamento.exe`), sem instalar nada

## Como usar (equipe da ONG)
1. Abra `Ensalamento.exe`.
2. Clique em **Procurar...** e escolha a planilha (`.xlsx`) com as abas **Alunos** e **Turmas**.
3. Clique em **▶ Rodar ensalamento**.
4. O resultado é gravado na própria planilha (abas **Ensalamento** e **Inconsistências**) e o
   relatório `<planilha>_relatorio.pdf` é criado na mesma pasta.

Veja o manual completo em [`docs/Manual_do_Usuario.pdf`](docs/Manual_do_Usuario.pdf).

## Modelo matemático
Decomposição exata em dois MILPs por turno (detalhes em
[`docs/modelo_matematico.md`](docs/modelo_matematico.md) e
[`docs/Desenho_da_Solucao.pdf`](docs/Desenho_da_Solucao.pdf)):

| Fase | Variáveis | Objetivo |
|---|---|---|
| 1 – Dimensionamento | $f_t, m_t \in \mathbb{Z}_+$ (meninas/meninos por turma), $z_i\in\{0,1\}$ | Lexicográfico: prioridade de matrícula → equilíbrio de quantidade → equilíbrio de gênero → proporção de meninas |
| 2 – Atribuição | $x_{i,t}\in\{0,1\}$ | Espalhar homônimos entre turmas, respeitando as quantidades ótimas |

Solver **HiGHS** (branch-and-cut) via **PuLP**; CBC como alternativa. 900 alunos / 26 turmas em ~1 s.

## Estrutura
```
app.py                     interface gráfica (Tkinter)
ensalamento/
  etl.py                   leitura, limpeza e inconsistências
  modelo.py                modelo de otimização (MILP)
  saida.py                 gravação das abas no Excel
  relatorio.py             relatório resumo (PDF)
  pipeline.py              orquestração
instancias/                instâncias de teste fornecidas
scripts/
  build_exe.ps1            gera dist/Ensalamento.exe
  rodar_instancias.py      roda todas as instâncias (+ validador oficial, se informado)
  gerar_cenarios_teste.py  cenários extremos para testes
tests/                     testes automatizados (pytest)
docs/                      desenho da solução, modelo e manual
```

## Desenvolvimento
```powershell
py -3.12 -m venv .venv            # Python 3.12.9
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py       # abre a interface
.venv\Scripts\python -m pytest    # testes
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1   # gera o .exe
```

## Resultados nas instâncias fornecidas
Todas **aprovadas** pelo validador oficial.

| Instância | Ensalados | Tamanhos das turmas | Maior desvio de gênero |
|---|---|---|---|
| 1 | 120/120 | 30, 30 · 30, 30 | 1,7 p.p. |
| 2 | 160/160 | 25, 24, 24 · 29, 29, 29 | 2,4 p.p. |
| 3 | 165/165 | 28 ×5 · 25 | 2,9 p.p. |
| 4 | 147/155 (8 linhas inválidas) | 27, 26, 26 · 23, 23, 22 | 2,2 p.p. |
