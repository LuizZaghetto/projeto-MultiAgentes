"""Interface compartilhada; as regras e as estrategias ficam nos modelos."""

import base64
from functools import lru_cache
from html import escape
from pathlib import Path
from threading import RLock

import gdown
import solara
from matplotlib.figure import Figure


RAIZ = Path(__file__).resolve().parent
LIMITE_TURNOS = 1000


@lru_cache(maxsize=6)
def imagem_agente(pasta, nome):
    caminho = Path(pasta) / nome
    if not caminho.exists():
        identificador = {
            "gato.png": "1-OxS1QX7SndwamrLeNz3vBPwTTetGEhI",
            "rato.png": "1hhXI74sKxfgGSiGZkdyrYF2JomMq-oGo",
        }[nome]
        gdown.download(id=identificador, output=str(caminho), quiet=True)
    return "data:image/png;base64," + base64.b64encode(caminho.read_bytes()).decode("ascii")


class PartidaVisual:
    """Estado de uma sessao, com historico e protecao para reproducao automatica."""

    def __init__(self, modos):
        self.modos = modos
        self.lock = RLock()
        self.reiniciar(next(iter(modos)))

    def reiniciar(self, modo=None):
        with self.lock:
            self.modo = modo or self.modo
            self.modulo = self.modos[self.modo]
            self.modelo = self.modulo.Modelo(verbose=False)
            self.historico = []
            self._registrar()

    def _registrar(self):
        gatos = list(self.modelo.agents.select(agent_type=self.modulo.AgentePredador))
        ratos = list(self.modelo.agents.select(agent_type=self.modulo.AgentePresa))
        redundancia = getattr(self.modelo, "_calcular_redundancia_alvos", None)
        self.historico.append({
            "turno": self.modelo.steps,
            "gatos": len(gatos),
            "ratos": len(ratos),
            "energia": sum(g.energy for g in gatos) / len(gatos) if gatos else 0,
            "redundancia": redundancia() if redundancia else None,
        })

    def resultado(self):
        ultimo = self.historico[-1]
        if ultimo["ratos"] == 0:
            return "Vitória dos predadores", "Todos os ratos foram capturados."
        if ultimo["gatos"] == 0:
            return "Vitória das presas", "Os gatos ficaram sem energia."
        if ultimo["turno"] >= LIMITE_TURNOS:
            return "Limite de turnos atingido", "A partida terminou sem um vencedor."
        return None

    def avancar(self, quantidade=1, modelo_esperado=None, cancelamento=None):
        with self.lock:
            if modelo_esperado is not None and self.modelo is not modelo_esperado:
                return False
            mudou = False
            for _ in range(quantidade):
                if self.resultado() or (cancelamento is not None and cancelamento.is_set()):
                    break
                self.modelo.step()
                self._registrar()
                mudou = True
            return mudou

    def snapshot(self):
        with self.lock:
            return {
                "modelo": self.modelo,
                "modo": self.modo,
                "historico": [registro.copy() for registro in self.historico],
                "resultado": self.resultado(),
                **estado_tabuleiro(self.modelo, self.modulo.AgentePredador),
            }


def estado_tabuleiro(modelo, tipo_predador):
    agentes = []
    for agente in modelo.agents:
        gato = isinstance(agente, tipo_predador)
        alvo = getattr(agente, "alvo_atual", None)
        agentes.append({
            "id": agente.unique_id,
            "gato": gato,
            "posicao": agente.cell.coordinate,
            "valor": agente.energy if gato else agente.peso,
            "alvo": alvo.cell.coordinate if alvo is not None and alvo in modelo.agents else None,
        })
    return {
        "agentes": agentes,
        "dimensoes": (modelo.grid.width, modelo.grid.height),
    }


def figura_resultados(historico):
    """So e chamada depois que a partida termina."""
    figura = Figure(figsize=(15, 6), facecolor="white", layout="constrained")
    eixos = figura.subplots(1, 3)
    turnos = [r["turno"] for r in historico]
    eixos[0].plot(turnos, [r["ratos"] for r in historico], color="#15956c", label="Presas", linewidth=2)
    eixos[0].plot(turnos, [r["gatos"] for r in historico], color="#c16d39", label="Predadores", linewidth=2)
    eixos[0].set_title("População ao longo da partida")
    eixos[0].legend(frameon=False, fontsize=8)
    eixos[1].plot(turnos, [r["energia"] for r in historico], color="#c16d39", linewidth=2)
    eixos[1].set_title("Energia média dos predadores")
    if historico[0]["redundancia"] is not None:
        eixos[2].plot(turnos, [r["redundancia"] for r in historico], color="#6578ad", linewidth=2)
        eixos[2].axhline(1, color="#a6b2be", linestyle=":", linewidth=1)
        eixos[2].set_title("Gatos por alvo")
    else:
        inicial = historico[0]["ratos"]
        eixos[2].plot(turnos, [inicial - r["ratos"] for r in historico], color="#6578ad", linewidth=2)
        eixos[2].set_title("Capturas acumuladas")
    for eixo in eixos:
        eixo.set_xlabel("Turno", color="#657587", fontsize=11)
        eixo.set_facecolor("#f8fafb")
        eixo.grid(axis="y", color="#e4ebef", linewidth=0.7)
        eixo.set_axisbelow(True)
        eixo.tick_params(colors="#657587", labelsize=10)
        eixo.title.set_fontsize(12)
        eixo.title.set_color("#233747")
        eixo.spines[["top", "right"]].set_visible(False)
        eixo.spines[["bottom", "left"]].set_color("#d7e1e7")
        eixo.set_xlim(0, max(1, turnos[-1]))
    return figura


@solara.component
def Tabuleiro(estado, pasta_imagens, mostrar_alvos):
    largura, altura = estado["dimensoes"]
    gato_src = imagem_agente(str(pasta_imagens), "gato.png")
    rato_src = imagem_agente(str(pasta_imagens), "rato.png")
    with solara.v.Html(tag="div", class_="ma-board-frame"):
        with solara.v.Html(
            tag="div", class_="ma-board",
            style_=f"--colunas:{largura};--linhas:{altura};aspect-ratio:{largura}/{altura}",
            attributes={"role": "group", "aria-label": "Tabuleiro da simulação"},
        ):
            grade = [
                f'<line x1="{x * 100 / largura}" y1="0" x2="{x * 100 / largura}" y2="100" />'
                for x in range(1, largura)
            ] + [
                f'<line x1="0" y1="{y * 100 / altura}" x2="100" y2="{y * 100 / altura}" />'
                for y in range(1, altura)
            ]
            solara.HTML(
                unsafe_innerHTML='<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
                + "".join(grade) + "</svg>", classes=["ma-grid"],
            )
            if mostrar_alvos:
                linhas = []
                for agente in estado["agentes"]:
                    if agente["alvo"] is not None:
                        x, y = agente["posicao"]
                        ax, ay = agente["alvo"]
                        linhas.append(
                            f'<line x1="{(x + .5) * 100 / largura}" y1="{(altura - y - .5) * 100 / altura}" '
                            f'x2="{(ax + .5) * 100 / largura}" y2="{(altura - ay - .5) * 100 / altura}" />'
                        )
                solara.HTML(
                    unsafe_innerHTML='<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
                    + "".join(linhas) + "</svg>", classes=["ma-targets"],
                )
            for agente in estado["agentes"]:
                x, y = agente["posicao"]
                gato = agente["gato"]
                nome = "Predador" if gato else "Presa"
                unidade = "Energia" if gato else "Peso"
                with solara.v.Html(
                    tag="div", class_="ma-agent " + ("ma-cat" if gato else "ma-mouse"),
                    style_=f"left:{(x + .5) * 100 / largura}%;top:{(altura - y - .5) * 100 / altura}%;width:{100 / largura}%",
                    attributes={"title": f'{nome} {agente["id"]} · {unidade}: {agente["valor"]} · ({x}, {y})'},
                ).key(f'agente-{agente["id"]}'):
                    solara.v.Html(tag="img", class_="ma-sprite", attributes={
                        "src": gato_src if gato else rato_src,
                        "alt": f'{nome} {agente["id"]}', "draggable": "false",
                    })
                    solara.v.Html(tag="span", class_="ma-agent-value", children=[str(agente["valor"])])
        solara.HTML(
            unsafe_innerHTML="".join(f"<span>{x}</span>" for x in range(largura)),
            classes=["ma-axis"],
        )
        solara.HTML(
            unsafe_innerHTML="".join(f"<span>{y}</span>" for y in reversed(range(altura))),
            classes=["ma-y-axis"],
        )


@solara.component
def InterfaceSimulacao(titulo, modos, pasta_imagens):
    controle = solara.use_memo(lambda: PartidaVisual(modos), [])
    revisao = solara.use_reactive(0)
    executando = solara.use_reactive(False)
    mostrar_alvos = solara.use_reactive(False)
    _ = revisao.value
    estado = controle.snapshot()
    terminou = estado["resultado"] is not None
    atual = estado["historico"][-1]
    modelo_atual = estado["modelo"]
    em_execucao = executando.value

    def reproduzir(cancelamento):
        if not em_execucao:
            return
        try:
            while not cancelamento.is_set():
                if not controle.avancar(modelo_esperado=modelo_atual, cancelamento=cancelamento):
                    break
                revisao.set(revisao.value + 1)
                if cancelamento.wait(0.8):
                    return
        finally:
            if not cancelamento.is_set():
                executando.set(False)

    tarefa = solara.use_thread(reproduzir, dependencies=[em_execucao, modelo_atual], intrusive_cancel=False)

    def parar():
        tarefa.cancel()
        executando.set(False)

    def reiniciar(modo=None):
        parar()
        controle.reiniciar(modo)
        revisao.set(revisao.value + 1)

    def avancar(quantidade=1):
        if controle.avancar(quantidade):
            revisao.set(revisao.value + 1)

    figura = solara.use_memo(
        lambda: figura_resultados(estado["historico"]) if terminou else None,
        dependencies=[modelo_atual, terminou, len(estado["historico"]) if terminou else 0],
    )

    solara.Style(RAIZ / "interface.css")
    with solara.Column(classes=["ma-app"] + (["ma-finished"] if terminou else []), gap="16px"):
        solara.HTML(unsafe_innerHTML=f"<h1>{escape(titulo)}</h1>", classes=["ma-heading"])

        if len(modos) > 1:
            with solara.Row(justify="center", classes=["ma-mode-row"]):
                solara.ToggleButtonsSingle(
                    value=estado["modo"], values=list(modos), on_value=reiniciar,
                    classes=["ma-modes"], dense=True,
                )

        solara.HTML(unsafe_innerHTML=(
            f'<span>Turno <strong>{atual["turno"]}</strong></span>'
            f'<span>Gatos <strong>{atual["gatos"]}</strong></span>'
            f'<span>Ratos <strong>{atual["ratos"]}</strong></span>'
        ), classes=["ma-state"])

        Tabuleiro(estado, pasta_imagens, mostrar_alvos.value).key(str(id(modelo_atual)))

        with solara.Row(classes=["ma-controls"], justify="center", gap="8px"):
            solara.Button(
                "Pausar" if em_execucao else "Reproduzir",
                icon_name="mdi-pause" if em_execucao else "mdi-play",
                on_click=parar if em_execucao else lambda: executando.set(True),
                disabled=terminou, color="#333333", classes=["ma-primary"],
            )
            solara.Button("Avançar", on_click=avancar, disabled=terminou or em_execucao, outlined=True)
            solara.Button("+5 turnos", on_click=lambda: avancar(5), disabled=terminou or em_execucao, outlined=True)
            solara.Button("Reiniciar", icon_name="mdi-restart", on_click=lambda: reiniciar(), outlined=True)

        if len(modos) > 1:
            with solara.Row(justify="center", classes=["ma-options"]):
                solara.Switch(label="Alvos", value=mostrar_alvos, color="#555555")

        if tarefa.error:
            solara.Error(f"Não foi possível avançar a simulação: {tarefa.error}")

        if terminou:
            titulo_resultado, _ = estado["resultado"]
            solara.HTML(
                unsafe_innerHTML=f"<strong>{escape(titulo_resultado)}</strong>",
                classes=["ma-result"],
            )
            with solara.Column(classes=["ma-metrics"], gap="16px"):
                inicial = estado["historico"][0]
                capturas = inicial["ratos"] - atual["ratos"]
                solara.HTML(unsafe_innerHTML=(
                    '<div class="ma-summary">'
                    f'<span>Capturas <strong>{capturas}</strong></span>'
                    f'<span>Sobreviventes <strong>{atual["gatos"]} / {inicial["gatos"]}</strong></span>'
                    f'<span>Energia média <strong>{atual["energia"]:.1f}</strong></span></div>'
                ))
                solara.FigureMatplotlib(figura, format="svg")
