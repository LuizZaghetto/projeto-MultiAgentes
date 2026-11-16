# Projeto MultiAgentes

Simulação de um sistema multiagente de predadores (gatos) e presas (ratos), desenvolvida em Python com Mesa. O projeto oferece interfaces interativas com Solara e experimentos em lote para observar a sobrevivência dos agentes.

## Modelos

- **Movimento aleatório:** gatos e ratos escolhem células vizinhas aleatoriamente.
- **Perseguição coordenada:** um orquestrador direciona os gatos à presa mais próxima, considerando as posições reservadas pelos demais gatos; os ratos se movem aleatoriamente.
- **Perseguição com fuga:** os gatos seguem o orquestrador e os ratos tentam se afastar dos gatos detectados em uma área de 3×3 células.

O ambiente é um grid de 10×10 células, sem conexão entre bordas. A cada turno, os ratos agem primeiro e os gatos depois. Os gatos gastam energia, recuperam energia ao capturar presas e podem morrer de fome.

## Estrutura

```text
orq_geral/
  app.py                # Interface dos dois modelos coordenados
  modelo.py             # Perseguição com ratos aleatórios
  modelo_fuga_rato.py    # Perseguição com ratos que fogem
  experimento.py        # Experimentos dos modelos coordenados
  gato.png
  rato.png
random_walk/
  app_rw.py             # Interface do movimento aleatório
  modelo_rw.py          # Modelo de movimento aleatório
  experimento_rw.py     # Experimentos do movimento aleatório
  gato.png
  rato.png
requirements.txt
```

## Instalação

O ambiente de desenvolvimento utilizado tem Python 3.14. Execute os comandos abaixo na raiz do projeto.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No Linux e no macOS, substitua `.\.venv\Scripts\python.exe` por `.venv/bin/python` e `.\.venv\Scripts\solara.exe` por `.venv/bin/solara` nos comandos.

## Interfaces interativas

Para os modelos com perseguição coordenada:

```powershell
.\.venv\Scripts\solara.exe run orq_geral/app.py
```

Para o modelo de movimento aleatório:

```powershell
.\.venv\Scripts\solara.exe run random_walk/app_rw.py
```

Abra no navegador o endereço exibido no terminal. As interfaces permitem avançar um turno e reiniciar a simulação. A interface coordenada também permite alternar entre ratos aleatórios e ratos com fuga.

As imagens já estão incluídas no projeto. Se uma imagem estiver ausente, a interface tenta baixá-la do Google Drive.

## Experimentos em lote

Cada opção executa 100 jogos, com limite de 1.000 turnos por jogo.

```powershell
# Movimento aleatório
.\.venv\Scripts\python.exe -m random_walk.experimento_rw

# Perseguição coordenada com ratos aleatórios
.\.venv\Scripts\python.exe -m orq_geral.experimento 1

# Perseguição coordenada com ratos que fogem
.\.venv\Scripts\python.exe -m orq_geral.experimento 2

# Executar os dois modelos coordenados
.\.venv\Scripts\python.exe -m orq_geral.experimento 3
```

Os resultados são apresentados no terminal e incluem vitórias dos predadores, vitórias das presas, empates por limite de turnos e duração média dos jogos. Os modelos coordenados também informam a energia média dos predadores sobreviventes nas vitórias.

## Parâmetros atuais

O experimento de movimento aleatório utiliza 5 gatos e 30 ratos. Os experimentos coordenados utilizam 5 gatos e 18 ratos. As regras de gasto e recuperação de energia também diferem entre esses grupos; considere essas diferenças ao comparar os resultados. Os experimentos usam aleatoriedade sem uma semente fixa.
