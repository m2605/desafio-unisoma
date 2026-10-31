"""
Roda o ensalamento em todas as instâncias de uma pasta (em cópias) e, se o
Validador.exe oficial for informado, audita cada resultado com ele.

Uso:
    python scripts/rodar_instancias.py instancias saida_testes [caminho/Validador.exe]
"""
from __future__ import annotations

import contextlib
import glob
import io
import marshal
import os
import shutil
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ensalamento.pipeline import executar  # noqa: E402


def carregar_validador(exe: str):
    """Carrega o módulo 'validar_resultado' de dentro do Validador.exe (PyInstaller)."""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
    arq = CArchiveReader(exe)
    pyz = next(n for n in arq.toc if "PYZ" in n)
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_validador.pyz")
    with open(tmp, "wb") as f:
        f.write(arq.extract(pyz))
    try:
        z = ZlibArchiveReader(tmp)
        dado = z.extract("validar_resultado")
        co = dado[1] if isinstance(dado, tuple) else dado
        if isinstance(co, bytes):
            co = marshal.loads(co)
    finally:
        os.remove(tmp)
    mod = types.ModuleType("validar_resultado")
    exec(co, mod.__dict__)
    return mod


def main():
    origem, destino = sys.argv[1], sys.argv[2]
    exe = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(destino, exist_ok=True)
    val = carregar_validador(exe) if exe else None
    resumo = []
    for arq in sorted(glob.glob(os.path.join(origem, "*.xlsx"))):
        if arq.endswith("_validacao.xlsx") or os.path.basename(arq).startswith("~$"):
            continue
        copia = os.path.join(destino, os.path.basename(arq))
        shutil.copyfile(arq, copia)
        res = executar(copia)
        linha = (f"{os.path.basename(arq):28s} ensalados={res.ensalados:4d}/{res.cenario.total_linhas:<4d} "
                 f"erros={res.contagem('ERRO'):3d} alertas={res.contagem('ALERTA'):3d} "
                 f"corrigidos={res.contagem('CORRIGIDO'):3d} tempo={res.segundos:5.2f}s")
        for e in res.estatisticas:
            linha += f"\n      {e.turma:10s} {e.total:3d}/{e.vagas:<3d} M={e.meninos:3d} F={e.meninas:3d}"
        if val:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                aprovado = val.validar(copia)
            txt = buf.getvalue()
            linha += f"\n   -> VALIDADOR OFICIAL: {'APROVADO' if aprovado else 'REPROVADO'}"
            for ln in txt.splitlines():
                if ln.lstrip().startswith(("❌", "⚠️")) or ln.startswith("      - "):
                    linha += f"\n      {ln.strip()}"
            with open(copia.replace(".xlsx", "_validador.txt"), "w", encoding="utf-8") as fh:
                fh.write(txt)
        resumo.append(linha)
        print(linha, flush=True)


if __name__ == "__main__":
    main()
