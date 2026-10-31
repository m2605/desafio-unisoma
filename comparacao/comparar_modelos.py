"""
Roda as duas soluções (monolítica e decomposição) nas mesmas planilhas e compara.
Cada solução é importada da sua própria pasta, em processos separados, para
garantir que uma não interfere na outra.

Uso (na raiz do repositório):
    python comparacao/comparar_modelos.py dados/instancias [Validador.exe]
Gera comparacao/resultado_comparacao.md
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILHO = r'''
import contextlib, io, json, sys, time
sys.path.insert(0, sys.argv[1])
from {pacote}.pipeline import executar
planilha = sys.argv[2]
res = executar(planilha, gerar_relatorio=False)
saida = {{"segundos": res.segundos, "ensalados": res.ensalados,
          "status": next(iter(res.turnos.values())).status if res.turnos else "-",
          "turmas": [], "aprovado": None}}
for turno in ("Manhã", "Tarde"):
    ests = [e for e in res.estatisticas if e.turno == turno and e.total]
    if not ests:
        continue
    pm = sum(e.meninos for e in ests) / sum(e.total for e in ests)
    for e in ests:
        saida["turmas"].append({{"turno": turno, "total": e.total, "m": e.meninos,
                                 "desvio_pp": abs(e.meninos / e.total - pm) * 100}})
if len(sys.argv) > 3:
    sys.path.insert(0, sys.argv[4])
    from rodar_instancias import carregar_validador
    with contextlib.redirect_stdout(io.StringIO()):
        saida["aprovado"] = bool(carregar_validador(sys.argv[3]).validar(planilha))
print("JSON:" + json.dumps(saida))
'''

SOLUCOES = [("Monolítica (colega)", "solucao_monolitica", "ensalamento_mono"),
            ("Decomposição", "solucao_decomposicao", "ensalamento")]


def rodar(pasta, pacote, planilha, validador):
    args = [sys.executable, "-c", FILHO.format(pacote=pacote), os.path.join(RAIZ, pasta), planilha]
    if validador:
        args += [validador, os.path.join(RAIZ, pasta, "scripts")]
    out = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    linha = next((l for l in out.stdout.splitlines() if l.startswith("JSON:")), None)
    if not linha:
        return {"erro": (out.stderr or out.stdout)[-300:]}
    return json.loads(linha[5:])


def main():
    origem = sys.argv[1]
    validador = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    linhas = ["| Instância | Solução | Tempo (s) | Status | Ensalados | Amplitude de tamanho | "
              "Maior desvio de gênero (p.p.) | Validador |",
              "|---|---|---|---|---|---|---|---|"]
    with tempfile.TemporaryDirectory() as tmp:
        for arq in sorted(glob.glob(os.path.join(origem, "*.xlsx"))):
            for rotulo, pasta, pacote in SOLUCOES:
                copia = os.path.join(tmp, f"{pacote}_{os.path.basename(arq)}")
                shutil.copyfile(arq, copia)
                r = rodar(pasta, pacote, copia, validador)
                if "erro" in r:
                    linhas.append(f"| {os.path.basename(arq)} | {rotulo} | erro: {r['erro']} |||||||")
                    continue
                amp = []
                for turno in ("Manhã", "Tarde"):
                    tam = [t["total"] for t in r["turmas"] if t["turno"] == turno]
                    if tam:
                        amp.append(str(max(tam) - min(tam)))
                desv = max((t["desvio_pp"] for t in r["turmas"]), default=0)
                val = {True: "APROVADO", False: "REPROVADO", None: "-"}[r["aprovado"]]
                linhas.append(f"| {os.path.basename(arq)} | {rotulo} | {r['segundos']:.2f} | "
                              f"{r['status']} | {r['ensalados']} | {' / '.join(amp) or '-'} | "
                              f"{desv:.1f} | {val} |")
                print(linhas[-1], flush=True)
    destino = os.path.join(RAIZ, "comparacao", "resultado_comparacao.md")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("# Comparação: solução monolítica × decomposição\n\n")
        fh.write(f"Planilhas: `{os.path.relpath(origem, RAIZ)}`\n\n")
        fh.write("\n".join(linhas) + "\n")
    print("Gerado:", destino)


if __name__ == "__main__":
    main()
