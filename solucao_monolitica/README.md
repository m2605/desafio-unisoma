# ⭐ Solução monolítica (principal)

Um único modelo MILP para os dois turnos, conforme o documento
[`docs/Modelo_Matematico_Colega.pdf`](docs/Modelo_Matematico_Colega.pdf), com correções
opcionais que garantem as regras do validador oficial. Detalhes:
[`docs/modelo_monolitico.md`](docs/modelo_monolitico.md).

```powershell
# a partir da raiz do repositório
.venv\Scripts\python solucao_monolitica\app.py
.venv\Scripts\python -m pytest solucao_monolitica\tests
.venv\Scripts\python solucao_monolitica\scripts\rodar_instancias.py dados\instancias saida [Validador.exe]
powershell -ExecutionPolicy Bypass -File solucao_monolitica\scripts\build_exe.ps1   # dist\Ensalamento.exe
```

Usar o modelo exatamente como no documento (sem correções):
```python
from ensalamento_mono.modelo_monolitico import Opcoes
from ensalamento_mono.pipeline import executar
executar("planilha.xlsx", opcoes=Opcoes.original())
```
