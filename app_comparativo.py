"""Página Solara para executar o comparativo e explorar as partidas."""

from html import escape
from io import BytesIO
from pathlib import Path

import pandas as pd
import solara
from solara.datatypes import ResultState

from experimento_comparativo import (
    CENARIOS,
    JOGOS_POR_CENARIO,
    LIMITE_TURNOS,
    figura_comparativa,
    jogar_partida,
    rodar_experimento,
)
from interface_comum import Tabuleiro, estado_tabuleiro


RAIZ = Path(__file__).resolve().parent
TOTAL_PARTIDAS = len(CENARIOS) * JOGOS_POR_CENARIO
NOMES_CENARIOS = tuple(f"{arquitetura} · {presa}" for _, arquitetura, presa in CENARIOS)
METRICAS = {
    "Vitórias dos gatos": ("Vitorias_Pred_%", "%", 1),
    "Vitórias dos ratos": ("Vitorias_Presa_%", "%", 1),
    "Limites de turnos": ("Timeouts", "", 0),
    "Duração média": ("Turnos_Medio_Geral", " turnos", 1),
    "Duração média nas vitórias dos gatos": ("Turnos_Medio_Vitoria_Pred", " turnos", 1),
    "Energia final dos gatos sobreviventes nas vitórias": ("Energia_Media_Sobreviventes", "", 1),
    "Gatos por alvo": ("Redundancia_Gatos_Por_Alvo", "", 2),
    "Dispersão dos gatos": ("Dispersao_Media_Grid", " células", 2),
    "Tempo médio por turno": ("Tempo_Medio_Step_ms", " ms", 4),
}
ROTULOS_TABELA = {
    chave: f"{nome} ({unidade.strip()})" if unidade else nome
    for nome, (chave, unidade, _) in METRICAS.items()
}
CORES = ("#17665e", "#5c9285", "#244f81", "#7296bb")

ESTILOS = """
.comparativo { width: min(1120px, 100%); margin: 28px auto; padding: 0 20px 24px; }
.comparativo h1 { font-size: 27px; line-height: 1.2; margin: 0 0 8px; }
.comparativo .cmp-sub { color: #535e66; font-size: 14px; }
.comparativo .cmp-painel { border: 1px solid #dce3e6; border-radius: 10px; }
.comparativo .v-btn { text-transform: none; font-weight: 600; letter-spacing: 0; }
.cmp-flex { flex-wrap: wrap; }
.cmp-flex > * { flex: 1 1 220px; min-width: 0; }
.cmp-bar { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 5px 12px; margin: 14px 0; }
.cmp-bar strong { font-variant-numeric: tabular-nums; }
.cmp-track { grid-column: 1 / -1; height: 12px; background: #e8edef; border-radius: 3px; }
.cmp-track span { display: block; height: 100%; border-radius: inherit; }
.cmp-tabuleiro { width: min(530px, 100%); margin: 0 auto; }
@media (max-width: 580px) {
    .comparativo { padding: 0 9px 16px; margin-top: 16px; }
    .comparativo h1 { font-size: 22px; }
}
"""


def executar_comparativo(progresso, cancelamento):
    resumos, partidas = [], []
    for indice, (modulo, arquitetura, presa) in enumerate(CENARIOS):
        jogos = []

        def registrar(semente, resultado, turnos):
            jogos.append((semente, resultado, turnos))
            if semente % 5 == 0 or semente == JOGOS_POR_CENARIO:
                progresso(indice * JOGOS_POR_CENARIO + semente, NOMES_CENARIOS[indice])

        resumos.append(rodar_experimento(
            modulo, arquitetura, presa, ao_concluir_partida=registrar,
            cancelamento=cancelamento, exibir_progresso=False,
        ))
        partidas.append(jogos)
    return pd.DataFrame(resumos), partidas


def reconstituir_partida(modulo, semente):
    quadros = []

    def guardar_quadro(modelo):
        quadros.append(estado_tabuleiro(modelo, modulo.AgentePredador))

    jogar_partida(modulo, semente, ao_registrar_turno=guardar_quadro)
    return quadros


def baixar_graficos(resumo):
    arquivo = BytesIO()
    figura_comparativa(resumo).savefig(arquivo, format="png", dpi=150)
    return arquivo.getvalue()


@solara.component
def Resumo(resultados):
    metrica, set_metrica = solara.use_state(next(iter(METRICAS)))
    coluna, unidade, casas = METRICAS[metrica]
    valores = resultados[coluna].tolist()
    escala = 100 if unidade == "%" else max(valores) or 1
    tabela = resultados.rename(columns={
        "Presa": "Comportamento das presas",
        **ROTULOS_TABELA,
    })

    with solara.Card("Comparar cenários", classes=["cmp-painel"], elevation=0):
        solara.Select("Métrica", values=list(METRICAS), value=metrica, on_value=set_metrica)
        for nome, valor, cor in zip(NOMES_CENARIOS, valores, CORES):
            texto = f"{valor:.{casas}f}".replace(".", ",") + unidade
            solara.HTML(
                classes=["cmp-bar"],
                unsafe_innerHTML=(
                    f"<span>{escape(nome)}</span><strong>{escape(texto)}</strong>"
                    f'<div class="cmp-track" aria-hidden="true">'
                    f'<span style="width:{valor * 100 / escala:.4f}%;background:{cor}"></span></div>'
                ),
            )

    with solara.Card("Tabela de resultados", classes=["cmp-painel"], elevation=0):
        solara.DataFrame(tabela, items_per_page=len(CENARIOS), scrollable=True)
        with solara.Row(classes=["cmp-flex"]):
            solara.FileDownload(
                resultados.to_csv(index=False), filename="resultados_comparativos.csv",
                label="Baixar CSV", mime_type="text/csv",
            )
            solara.FileDownload(
                lambda: baixar_graficos(resultados), filename="comparativo_arquiteturas.png",
                label="Baixar gráficos (PNG)", mime_type="image/png",
            )


@solara.component
def Replay(modulo, partida):
    semente, resultado, total_turnos = partida
    quadros = solara.use_memo(lambda: reconstituir_partida(modulo, semente), [modulo, semente])
    turno, set_turno = solara.use_state(0)
    mostrar_alvos, set_mostrar_alvos = solara.use_state(False)
    estado = quadros[turno]
    gatos = sum(agente["gato"] for agente in estado["agentes"])
    ratos = len(estado["agentes"]) - gatos
    pasta_imagens = RAIZ / modulo.__name__.split(".")[0]

    solara.Text(f"{resultado} em {total_turnos} turnos")
    if total_turnos:
        solara.SliderInt("Turno", min=0, max=total_turnos, value=turno, on_value=set_turno)
        with solara.Row(justify="center", classes=["cmp-flex"]):
            solara.Button("Anterior", on_click=lambda: set_turno(turno - 1), disabled=turno == 0, outlined=True)
            solara.Button(
                "Próximo", on_click=lambda: set_turno(turno + 1),
                disabled=turno == total_turnos, outlined=True,
            )
    with solara.Row(justify="center"):
        solara.Text(f"Turno {turno}/{total_turnos} · {gatos} gatos · {ratos} ratos")
    with solara.Row(justify="center"):
        solara.Switch(label="Alvos", value=mostrar_alvos, on_value=set_mostrar_alvos)
    with solara.Column(classes=["cmp-tabuleiro"]):
        Tabuleiro(estado, pasta_imagens, mostrar_alvos)


@solara.component
def Partidas(partidas):
    cenario, set_cenario = solara.use_state(NOMES_CENARIOS[0])
    semente, set_semente = solara.use_state(1)
    indice = NOMES_CENARIOS.index(cenario)
    with solara.Card("Rever uma partida", classes=["cmp-painel"], elevation=0):
        with solara.Row(classes=["cmp-flex"]):
            solara.Select("Cenário", values=list(NOMES_CENARIOS), value=cenario, on_value=set_cenario)
            solara.Select(
                "Partida (semente)", values=list(range(1, JOGOS_POR_CENARIO + 1)),
                value=semente, on_value=set_semente,
            )
        Replay(CENARIOS[indice][0], partidas[indice][semente - 1]).key(f"{indice}-{semente}")


@solara.component
def Page():
    rodada, set_rodada = solara.use_state(0)
    aba, set_aba = solara.use_state("Resultados")
    progresso = solara.use_reactive((0, ""))

    def executar(cancelamento):
        if rodada:
            try:
                dados = executar_comparativo(lambda feitos, nome: progresso.set((feitos, nome)), cancelamento)
            except InterruptedError:
                return None
            return rodada, dados
        return None

    tarefa = solara.use_thread(executar, dependencies=[rodada], intrusive_cancel=False)
    pronto = tarefa.value is not None and tarefa.value[0] == rodada
    carregando = rodada > 0 and not pronto and tarefa.state not in (ResultState.ERROR, ResultState.CANCELLED)
    concluidas, cenario = progresso.value
    limite_formatado = f"{LIMITE_TURNOS:,}".replace(",", ".")

    def iniciar():
        progresso.set((0, ""))
        set_aba("Resultados")
        set_rodada(lambda anterior: anterior + 1)

    solara.Title("Experimento comparativo")
    solara.Style(RAIZ / "interface.css")
    solara.Style(ESTILOS)
    with solara.Column(classes=["comparativo"], gap="18px"):
        solara.HTML(
            unsafe_innerHTML=(
                "<h1>Experimento comparativo</h1>"
                f'<div class="cmp-sub">{len(CENARIOS)} cenários · {JOGOS_POR_CENARIO} partidas por cenário'
                f" · {limite_formatado} turnos no máximo</div>"
            ),
        )
        with solara.Row():
            solara.Button(
                "Rodar novamente" if pronto else f"Simular {TOTAL_PARTIDAS} partidas",
                icon_name="mdi-play", color="#17665e", on_click=iniciar, disabled=carregando,
            )
        if carregando:
            solara.Text(f"{concluidas}/{TOTAL_PARTIDAS} partidas concluídas" + (f" · {cenario}" if cenario else ""))
            solara.ProgressLinear(value=100 * concluidas / TOTAL_PARTIDAS, color="#17665e")
        if tarefa.state == ResultState.ERROR:
            solara.Error(f"Não foi possível concluir o experimento. {tarefa.error}")
        if pronto:
            resumo, partidas = tarefa.value[1]
            solara.ToggleButtonsSingle(value=aba, values=["Resultados", "Partidas"], on_value=set_aba)
            if aba == "Resultados":
                Resumo(resumo).key(str(rodada))
            else:
                Partidas(partidas).key(str(rodada))
