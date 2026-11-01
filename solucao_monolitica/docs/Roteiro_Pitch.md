# Roteiro do pitch — Enturme ABC · Equipe 14 (3 minutos)

> Apresentação: `Apresentacao_Enturme.pdf` (6 slides). Ritmo: ~130 palavras por minuto.
> Tempos acumulados entre colchetes. Ensaiem com cronômetro: se passar de 3 min, encurtem o slide 4.
> Sugestão de divisão: cada integrante fala um bloco (indicado entre parênteses), mas qualquer um pode falar tudo.

---

**Slide 1 — Capa** [0:00–0:10] *(quem abre)*
> Boa tarde! Somos a equipe 14 e vamos apresentar o **Enturme ABC**: o ensalamento automático de turmas da ABC Aprendiz.

**Slide 2 — Nossa equipe** [0:10–0:20]
> Somos Willian, Ester, Maria e Mário. *(cada um acena ao ouvir o nome)* Os QR codes levam ao LinkedIn de cada um, se quiserem falar com a gente.

**Slide 3 — O problema da ONG** [0:20–0:55]
> Todo semestre, a equipe da ABC Aprendiz distribui centenas de jovens em turmas da manhã e da tarde **à mão**. São horas de planilha para respeitar quatro regras: o aluno da manhã só vai para turma da manhã; nenhuma turma passa das vagas; as turmas do mesmo turno têm no máximo um aluno de diferença, com meninos e meninas equilibrados; e todos os erros de cadastro precisam ser avisados. Hoje esses erros, como “manha” sem acento, sexo em branco ou nomes repetidos, só aparecem depois, e geram retrabalho.

**Slide 4 — Como resolvemos** [0:55–2:05]
> O Enturme ABC resolve isso em dois cliques. A pessoa clica em **Procurar**, escolhe a planilha e clica em **Rodar ensalamento**. Em cerca de um segundo as turmas estão prontas, gravadas no próprio Excel, como nesta tela.
>
> Por trás há um **modelo de otimização**, uma Programação Linear Inteira Mista resolvida pelo solver HiGHS em Python, que considera os dois turnos ao mesmo tempo. Ele segue uma ordem de prioridade: primeiro, ninguém sem sala; depois, turmas do mesmo tamanho; por fim, a proporção de meninos e meninas mais parecida possível. Se faltar vaga, quem se matriculou primeiro tem prioridade. E o solver **prova** que a solução é a melhor possível, não é uma divisão “no olho”.
>
> Na tela, a equipe vê os números do resultado, as turmas com a composição de cada uma e, na aba **Inconsistências**, todos os erros de uma vez, com a linha do Excel. Ainda gera um **relatório em PDF** para a coordenação. Rodamos as quatro instâncias oficiais e **todas foram aprovadas pelo validador oficial**. Não precisa instalar nada: é um único executável.

**Slide 5 — Impacto para a ABC Aprendiz** [2:05–2:45]
> Antes: horas de planilha manual, conferência de vagas e proporções, e erros encontrados só depois. Depois: dois cliques, turmas ótimas em segundos e todas as pendências listadas de uma vez. O benefício: a equipe fica livre para focar no que importa, **a formação dos jovens**, com turmas justas e decisões transparentes.

**Slide 6 — Obrigado** [2:45–3:00]
> Enturme ABC: turmas certas, no tempo certo. Muito obrigado!

---

### Perguntas prováveis da banca (respostas curtas)
- **“Por que não é heurística?”** — A solução sai de um solver MILP (HiGHS, branch-and-cut), que prova a otimalidade. Não há regra manual de distribuição.
- **“Por que um modelo só para os dois turnos?”** — O modelo monolítico trata manhã e tarde num único problema, com os mesmos pesos de prioridade, e continua resolvendo em cerca de 1 segundo.
- **“E se faltar vaga?”** — O modelo aloca o máximo possível, priorizando a ordem de matrícula, e lista quem ficou sem vaga na aba Inconsistências.
- **“E dados errados?”** — Corrigimos variações de escrita (manha, feminino). Sexo ou turno inválido e nome vazio não são alocados e aparecem na aba Inconsistências, todos de uma vez.
- **“Escala?”** — As instâncias oficiais rodam em cerca de 1 s. Testamos também cenários extremos, como superlotação, dados sujos, homônimos e 900 alunos.
- **“Homônimos?”** — São tratados como pessoas diferentes: todos são alocados, com um alerta de possível cadastro duplicado.
- **“A ONG consegue usar sozinha?”** — Sim: é um único `.exe`, com botão “Como usar” e manual em PDF. Os botões Abrir planilha, Abrir relatório PDF e Abrir pasta levam direto aos arquivos, sem sair do programa.
