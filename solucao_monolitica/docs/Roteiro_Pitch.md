# Roteiro do pitch — Enturme · Equipe 14 (3 minutos)

> Ritmo: ~130 palavras por minuto. Tempos acumulados entre colchetes.
> Dica: ensaiar com cronômetro; se estourar, encurte os slides 4 e 9.

---

**Slide 1 — Capa** [0:00–0:10]
> Boa tarde! Somos a equipe 14 e apresentamos o **Enturme**: o ensalamento automático de turmas da ABC Aprendiz.

**Slide 2 — Equipe** [0:10–0:18]
> Somos Willian, Ester, Mário e Maria. *(cada um acena ao ouvir o nome)*

**Slide 3 — O problema da ONG** [0:18–0:40]
> Todo semestre, a equipe da ABC Aprendiz distribui centenas de jovens em turmas da manhã e da tarde **à mão**. São horas de planilha para respeitar o turno de cada aluno, as vagas, deixar as turmas do mesmo tamanho e com meninos e meninas equilibrados. E os erros de cadastro — “manha” sem acento, sexo em branco, nomes repetidos — só aparecem depois, gerando retrabalho.

**Slide 4 — Nossa solução** [0:40–1:00]
> O Enturme resolve isso em dois cliques. A ONG arrasta a planilha, confirma, e em segundos as turmas estão prontas, gravadas no próprio Excel. Três diferenciais: o resultado é **ótimo, provado matematicamente**, não “no olho”; o programa **aponta todos os erros de uma vez**; e entrega um **relatório em PDF** para a coordenação.

**Slide 5 — Modelagem matemática** [1:00–1:40]
> Por trás está um modelo de **Programação Linear Inteira Mista**, resolvido pelo solver HiGHS em Python. A variável x indica se o aluno *i* vai para a turma *j*. As restrições garantem que cada aluno fica numa única turma do seu turno, que nenhuma turma passa das vagas e que as turmas do mesmo turno têm **no máximo um aluno de diferença**. A função objetivo, em ordem de prioridade: ninguém sem sala; turmas do mesmo tamanho; e o menor desvio de gênero possível. Os pesos são calculados para que um critério nunca sacrifique o anterior — e se faltar vaga, quem se matriculou primeiro tem prioridade.

**Slide 6 — Nosso aplicativo** [1:40–2:05]
> Esta é a tela de resultado. A equipe vê na hora o percentual de alunos alocados, a proporção de meninos e meninas por turno e um aviso com as inconsistências encontradas. Com um clique baixa a planilha das turmas e o relatório. Não precisa instalar nada: é um único executável.

**Slide 7 — Resultados** [2:05–2:35]
> Rodamos as quatro instâncias oficiais: **todas aprovadas pelo validador oficial**, cada uma em **até 1,1 segundo**, com prova de solução ótima. O desvio de gênero ficou em no máximo 3 pontos percentuais — o mínimo possível com números inteiros. E testamos mais dez cenários extremos: superlotação, dados sujos, homônimos e até 900 alunos.

**Slide 8 — Impacto** [2:35–2:52]
> Antes: horas de trabalho manual e erros descobertos tarde. Depois: dois cliques e turmas justas em segundos. O ganho: a equipe da ABC Aprendiz volta a focar no que importa — **a formação dos jovens**.

**Slide 9 — Encerramento** [2:52–3:00]
> Enturme: turmas certas, no tempo certo. Obrigado!

---

### Perguntas prováveis da banca (respostas curtas)
- **“Por que não é heurística?”** — A solução sai de um solver MILP (HiGHS, branch-and-cut), que prova a otimalidade; não há regra manual de distribuição.
- **“E se faltar vaga?”** — O modelo aloca o máximo possível priorizando a ordem de matrícula e lista quem ficou sem vaga na aba Inconsistências.
- **“E dados errados?”** — Corrigimos variações de escrita (manha, feminino); sexo/turno inválidos ou nome vazio não são alocados e aparecem na aba Inconsistências, todos de uma vez.
- **“Escala?”** — Instâncias reais em ~1 s; testamos 900 alunos em 26 turmas.
- **“Homônimos?”** — São pessoas diferentes: todos são alocados, com alerta de possível cadastro duplicado.
