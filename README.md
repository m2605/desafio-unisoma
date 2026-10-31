# Desafio UniSoma 2026 — Ensalamento ABC Aprendiz · Equipe 14

Aplicativo que distribui os alunos matriculados da **ABC Aprendiz** nas turmas da Manhã e da
Tarde usando **Programação Linear Inteira Mista (MILP)**: respeita turno, capacidade e
nomenclatura, deixa as turmas do mesmo turno com no máximo 1 aluno de diferença, equilibra
meninos e meninas e aponta todas as inconsistências da planilha de uma vez.

O repositório tem **duas soluções independentes** (cada uma com seu código, testes e `.exe`),
que chegam ao mesmo resultado por formulações diferentes:

| | ⭐ [Solução monolítica](solucao_monolitica/) — **principal** | [Solução por decomposição](solucao_decomposicao/) — alternativa |
|---|---|---|
| Modelo | um único MILP para os dois turnos, objetivo ponderado $W_1\sum z + W_2\sum(D_{max}-D_{min}) + W_3 v$ | um MILP por turno, em 2 fases (dimensionamento + atribuição), objetivo lexicográfico |
| Documento | [modelo_monolitico.md](solucao_monolitica/docs/modelo_monolitico.md) | [modelo_matematico.md](solucao_decomposicao/docs/modelo_matematico.md) |
| Executável | `Ensalamento.exe` | `Ensalamento_Decomposicao.exe` |
| Instâncias oficiais | 4/4 aprovadas · 0,1–1,1 s | 4/4 aprovadas · 0,1–0,2 s |
| 900 alunos / 26 turmas | ~145 s | ~1 s |
| Extras | — | separa homônimos em turmas diferentes |

Comparação completa: [`comparacao/resultado_comparacao.md`](comparacao/resultado_comparacao.md).

## Estrutura
```
dados/
  instancias/             4 instâncias oficiais (usadas pelas duas soluções)
  cenarios_teste/         10 cenários extremos (superlotação, dados sujos, 900 alunos…)
solucao_monolitica/       ⭐ principal (modelo do colega, com correções opcionais)
  app.py                  interface gráfica
  ensalamento_mono/       etl · modelo_monolitico · saida · relatorio · pipeline
  tests/  scripts/  docs/  assets/
solucao_decomposicao/     alternativa (decomposição exata em 2 fases)
  app.py
  ensalamento/            etl · modelo · saida · relatorio · pipeline
  tests/  scripts/  docs/  assets/
comparacao/
  comparar_modelos.py     roda as duas nas mesmas planilhas (+ validador oficial)
```

## Como usar (equipe da ONG)
1. Abra `Ensalamento.exe`.
2. Clique em **Procurar...** e escolha a planilha (`.xlsx`) com as abas **Alunos** e **Turmas**.
3. Clique em **▶ Rodar ensalamento**.
4. O resultado vai para a própria planilha (abas **Ensalamento** e **Inconsistências**) e o
   relatório `<planilha>_relatorio.pdf` é criado na mesma pasta.

## Desenvolvimento (Python 3.12.9)
```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r solucao_monolitica\requirements.txt
.venv\Scripts\python solucao_monolitica\app.py                     # interface
.venv\Scripts\python -m pytest solucao_monolitica\tests solucao_decomposicao\tests
powershell -ExecutionPolicy Bypass -File solucao_monolitica\scripts\build_exe.ps1     # dist\Ensalamento.exe
powershell -ExecutionPolicy Bypass -File solucao_decomposicao\scripts\build_exe.ps1   # dist\Ensalamento_Decomposicao.exe
.venv\Scripts\python comparacao\comparar_modelos.py dados\instancias [Validador.exe]
```
