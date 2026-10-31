# ⭐ Solução monolítica (principal)

Um único modelo MILP para os dois turnos, conforme o documento
[`docs/Modelo_Matematico_Colega.pdf`](docs/Modelo_Matematico_Colega.pdf), com correções
opcionais que garantem as regras do validador oficial. Detalhes:
[`docs/modelo_monolitico.md`](docs/modelo_monolitico.md).

## Duas interfaces (mesmo motor de otimização)
| Interface | Arquivo | Executável |
|---|---|---|
| **Enturme** (visual, conforme [design](docs/Design_Interface_Enturme.pdf)): arrastar e soltar, % de alocados, proporção de gênero por turno, botões de baixar | `app_enturme.py` + `enturme_ui.py` | `dist\Enturme.exe` (`scripts\build_enturme.ps1`) |
| Clássica (tabelas detalhadas de turmas, inconsistências e otimização) | `app.py` | `dist\Ensalamento.exe` (`scripts\build_exe.ps1`) |

![Enturme](docs/img/enturme_4_resultado.png)

Na Enturme, o resultado é gravado na própria planilha (abas Ensalamento e Inconsistências) e
uma cópia da planilha e do relatório PDF fica na pasta `Enturme_Arquivos`, ao lado do arquivo.

```powershell
# a partir da raiz do repositório
.venv\Scripts\python solucao_monolitica\app_enturme.py
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
