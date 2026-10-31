# Solução por decomposição (alternativa)

Um MILP por turno, decomposto de forma exata em duas fases:
**Fase 1** (dimensionamento: quantas meninas/meninos por turma, objetivo lexicográfico) e
**Fase 2** (atribuição aluno → turma, separando homônimos). Detalhes:
[`docs/modelo_matematico.md`](docs/modelo_matematico.md) e
[`docs/Desenho_da_Solucao.pdf`](docs/Desenho_da_Solucao.pdf).

```powershell
# a partir da raiz do repositório
.venv\Scripts\python solucao_decomposicao\app.py
.venv\Scripts\python -m pytest solucao_decomposicao\tests
powershell -ExecutionPolicy Bypass -File solucao_decomposicao\scripts\build_exe.ps1   # dist\Ensalamento_Decomposicao.exe
```
