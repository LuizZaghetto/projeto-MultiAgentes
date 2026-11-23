# Projeto MultiAgentes

Simulação de predadores (gatos) e presas (ratos) em Python, desenvolvida com Mesa. O projeto reúne cinco modelos, três interfaces em Solara e experimentos em lote para comparar a sobrevivência e o comportamento dos agentes.

## Modelos

| Arquitetura | Decisão dos gatos | Comportamento dos ratos |
|---|---|---|
| Random walk | Movimento aleatório entre vizinhos sem outro gato | Aleatório |
| Central | Orquestrador com visão global e distribuição de alvos | Aleatório |
| Central com fuga | Mesmo orquestrador central | Fuga ao detectar gatos na área 3×3 |
| Individual | Cada gato prioriza a presa visível mais próxima sem outro perseguidor, com alcance de 3 células | Aleatório |
| Individual com fuga | Mesma decisão individual com consulta aos alvos dos outros gatos | Fuga ao detectar gatos na área 3×3 |

O orquestrador central prioriza presas ainda sem um gato designado. Quando todas já têm um predador atribuído, permite compartilhar alvos. No modelo individual, cada gato consulta os alvos atuais dos demais e escolhe a presa visível mais próxima que esteja livre. Se todas as presas visíveis já tiverem um perseguidor, volta à sua primeira escolha, a presa mais próxima. A consulta ocorre na vez de cada gato, seguindo a ordem aleatória do turno.

Todos utilizam um grid 10×10, sem conexão entre bordas, com movimentos nas oito direções. Os ratos agem primeiro e os gatos depois, em ordem aleatória dentro de cada grupo. Cada gato pode capturar no máximo uma presa por turno.

## Instalação

O ambiente de desenvolvimento utiliza Python 3.14. Na raiz do projeto, execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No Linux e no macOS, substitua `.\.venv\Scripts\python.exe` por `.venv/bin/python` e `.\.venv\Scripts\solara.exe` por `.venv/bin/solara` nos comandos abaixo.

## Interfaces visuais

Execute uma interface por vez e abra o endereço exibido no terminal.

```powershell
# Orquestrador central
.\.venv\Scripts\solara.exe run orq_geral/app.py

# Decisão individual
.\.venv\Scripts\solara.exe run orq_individual/app.py

# Random walk
.\.venv\Scripts\solara.exe run random_walk/app_rw.py
```

As interfaces central e individual permitem alternar entre ratos aleatórios e ratos com fuga. Os controles compartilhados são:

- **Reproduzir / Pausar:** avança automaticamente a cada 0,8 segundo.
- **Avançar:** executa um turno.
- **+5 turnos:** executa até cinco turnos, parando se a partida terminar.
- **Reiniciar:** inicia outra partida no modo selecionado.
- **Alvos:** mostra ou oculta as linhas de perseguição nas interfaces central e individual.

Durante a partida, o tabuleiro permanece centralizado, com grid e coordenadas visíveis. Os números junto aos gatos indicam energia; os dos ratos, peso. Cada sessão do navegador mantém sua própria partida.

Os gráficos aparecem somente após o encerramento. Em telas largas, o tabuleiro encolhe e os resultados ocupam a área principal ao lado; em telas menores, ficam abaixo do tabuleiro reduzido. São apresentados:

- Resultado, capturas, gatos sobreviventes e energia média final.
- Evolução das populações e da energia média dos gatos.
- Gatos por alvo nos modelos de perseguição ou capturas acumuladas no random walk.

A partida termina quando não restam presas, não restam predadores ou o limite de 1.000 turnos é atingido. O avanço fica bloqueado após o encerramento. Trocar de modo inicia uma nova partida.

Para encerrar o servidor, pressione **Ctrl+C** no terminal. As imagens já estão incluídas; se estiverem ausentes, a interface tenta baixá-las do Google Drive.

## Regras compartilhadas

As regras comuns aos cinco modelos estão em `regras_comuns.py`.

| Parâmetro | Valor padrão |
|---|---|
| Predadores iniciais | 5 |
| Presas iniciais | 18 |
| Energia inicial por gato | 15 |
| Peso dos ratos | Inteiro de 5 a 9 |
| Gasto de energia por turno | `max(2, int(energia / 10))` |
| Nutrição da presa | `2 + int(peso)` |
| Custo de abate | `int(peso * 0.8)` |
| Ganho líquido da captura | `max(5, nutrição - custo_abate)` |

O custo de abate é descontado no cálculo do ganho, sem uma cobrança adicional. Com os pesos atuais, cada captura concede 5 unidades de energia. O gasto do turno acontece mesmo se o gato não conseguir se mover. A morte por energia menor ou igual a zero é verificada depois da oportunidade de captura.

Não há reprodução nem consumo de energia pelos ratos. As células começam sem sobreposição; durante a simulação, ratos podem compartilhar células, enquanto os gatos evitam entrar em células já ocupadas por outro gato.

As interfaces e os experimentos usam as quantidades padrão dos modelos. Para alterar a população em conjunto, edite `N_PREDADORES` e `N_PRESAS` em `regras_comuns.py` antes de iniciar a aplicação. O arquivo também centraliza as dimensões do grid, energia inicial, pesos, consumo, alimentação, captura e morte. As estratégias de movimento e escolha dos alvos permanecem nos respectivos modelos.

## Experimentos em lote

Os experimentos de cada pasta executam 100 partidas, com limite de 1.000 turnos por partida, sem semente fixa. Os resultados são apresentados no terminal.

```powershell
# Random walk
.\.venv\Scripts\python.exe -m random_walk.experimento_rw

# Central: 1 = ratos aleatórios; 2 = fuga; 3 = ambos
.\.venv\Scripts\python.exe -m orq_geral.experimento 3

# Individual: 1 = ratos aleatórios; 2 = fuga; 3 = ambos
.\.venv\Scripts\python.exe -m orq_individual.experimento 3
```

São calculadas vitórias dos gatos, vitórias dos ratos, empates por limite de turnos e duração média. Os experimentos central e individual também informam a energia média dos gatos sobreviventes nas vitórias.

### Comparação entre arquiteturas

Para abrir o comparativo interativo no Solara:

```powershell
.\.venv\Scripts\solara.exe run experimento_comparativo.py
```

Clique em **Simular 400 partidas**. Ao concluir, use **Resultados** para explorar as métricas e baixar o CSV ou o PNG. Em **Partidas**, selecione o cenário e a semente para rever o tabuleiro turno a turno. A interface oferece os arquivos para download e guarda o resultado da execução na sessão.

Para rodar pelo terminal e salvar os arquivos na pasta de execução:

```powershell
.\.venv\Scripts\python.exe experimento_comparativo.py
```

Esse script executa 100 partidas para cada um dos quatro modelos de perseguição, totalizando 400. Utiliza sementes de 1 a 100 para repetir as condições iniciais entre as arquiteturas. O random walk não está incluído nesse comparativo.

Além das vitórias, registra duração, energia dos sobreviventes, gatos por alvo, dispersão dos gatos e tempo médio por turno. Salva, na pasta de execução:

- `resultados_comparativos.csv`: tabela consolidada.
- `comparativo_arquiteturas.png`: gráficos comparativos.

Executar o script substitui esses dois arquivos. Os tempos dependem da máquina e não incluem o custo da coleta de métricas ao final de cada turno. A comparação também envolve uma diferença de informação: o central tem visão global e o individual tem alcance de 3 células. A métrica de gatos por alvo no individual pode incluir referências a presas capturadas por outro gato no mesmo turno.

## Estrutura

```text
orq_geral/
  app.py                      # Interface central
  modelo.py                   # Ratos aleatórios
  modelo_fuga_rato.py          # Ratos com fuga
  experimento.py
  gato.png
  rato.png
orq_individual/
  app.py                      # Interface individual
  modelo.py                   # Ratos aleatórios
  modelo_fuga_rato.py          # Ratos com fuga
  experimento.py
  gato.png
  rato.png
random_walk/
  app_rw.py                   # Interface de movimento aleatório
  modelo_rw.py
  experimento_rw.py
  gato.png
  rato.png
regras_comuns.py               # Regras e inicialização dos cinco modelos
interface_comum.py             # Estado e componentes das interfaces
interface.css                  # Estilos compartilhados e layout final
experimento_comparativo.py     # Comparação dos quatro modelos de perseguição
app_comparativo.py             # Comparativo interativo e replay das partidas
resultados_comparativos.csv
comparativo_arquiteturas.png
requirements.txt
```
