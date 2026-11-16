from pathlib import Path
import gdown
import solara
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

if __package__:
    from . import modelo as mod_padrao
    from . import modelo_fuga_rato as mod_fuga
else:
    import modelo as mod_padrao
    import modelo_fuga_rato as mod_fuga

ID_GATO = "1-OxS1QX7SndwamrLeNz3vBPwTTetGEhI"
ID_RATO = "1hhXI74sKxfgGSiGZkdyrYF2JomMq-oGo"

def carregar_imagem_drive(file_id, nome_destino):
    destino = Path(__file__).resolve().parent / nome_destino
    if not destino.exists():
        url = f"https://drive.google.com/uc?id={file_id}"
        print(f"Baixando {nome_destino} do Google Drive...")
        gdown.download(url, str(destino), quiet=False)
    return mpimg.imread(destino)

IMG_PREDADOR = carregar_imagem_drive(ID_GATO, "gato.png")
IMG_PRESA = carregar_imagem_drive(ID_RATO, "rato.png")

MODOS = {
    "Rato Padrão (Aleatório)": mod_padrao,
    "Rato com Fuga (Scan 3x3)": mod_fuga
}

modo_selecionado = solara.reactive("Rato Padrão (Aleatório)")
modelo_estado = solara.reactive(mod_padrao.Modelo(n_pred=5, n_presa=18, verbose=False))
forca_update = solara.reactive(0)

@solara.component
def Page():
    modulo_atual = MODOS[modo_selecionado.value]

    def mudar_modo(novo_modo):
        modo_selecionado.set(novo_modo)
        mod = MODOS[novo_modo]
        modelo_estado.set(mod.Modelo(n_pred=5, n_presa=18, verbose=False))
        forca_update.value += 1

    def rodar_step():
        modelo_estado.value.step()
        modelo_estado.set(modelo_estado.value)
        forca_update.value += 1

    def resetar():
        modelo_estado.set(modulo_atual.Modelo(n_pred=5, n_presa=18, verbose=False))
        forca_update.value += 1

    _ = forca_update.value

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 9.5)
    ax.set_xticks(range(10))
    ax.set_yticks(range(10))
    ax.grid(True, linestyle="--", alpha=0.5)

    for agent in modelo_estado.value.agents:
        x, y = agent.cell.coordinate

        if isinstance(agent, modulo_atual.AgentePredador):
            img_box = OffsetImage(IMG_PREDADOR, zoom=0.18)
            ab = AnnotationBbox(img_box, (x, y), frameon=False)
            ax.add_artist(ab)

            ax.annotate(f"E:{agent.energy}", (x, y), textcoords="offset points",
                        xytext=(0, 14), ha='center', fontsize=8, color='darkred', fontweight='bold')

            if getattr(agent, "alvo_atual", None) is not None and agent.alvo_atual in modelo_estado.value.agents:
                ax_alvo, ay_alvo = agent.alvo_atual.cell.coordinate
                ax.plot([x, ax_alvo], [y, ay_alvo], "r--", alpha=0.35, linewidth=1)

        elif isinstance(agent, modulo_atual.AgentePresa):
            fator_zoom = 0.03 + (agent.peso * 0.004)
            img_box = OffsetImage(IMG_PRESA, zoom=fator_zoom)
            ab = AnnotationBbox(img_box, (x, y), frameon=False)
            ax.add_artist(ab)

            ax.annotate(f"{agent.peso}", (x, y), textcoords="offset points",
                        xytext=(0, -14), ha='center', fontsize=7, color='darkgreen')

    total_pred = sum(1 for a in modelo_estado.value.agents if isinstance(a, modulo_atual.AgentePredador))
    total_presa = sum(1 for a in modelo_estado.value.agents if isinstance(a, modulo_atual.AgentePresa))
    ax.set_title(f"[{modo_selecionado.value}] Turno: {modelo_estado.value.steps} | Predadores: {total_pred} | Presas: {total_presa}", fontsize=10)
    plt.close(fig)

    with solara.Column():
        solara.ToggleButtonsSingle(
            value=modo_selecionado.value,
            values=list(MODOS.keys()),
            on_value=mudar_modo
        )
        with solara.Row():
            solara.Button("Avançar Turno (Step)", on_click=rodar_step, color="primary")
            solara.Button("Resetar", on_click=resetar)
        solara.FigureMatplotlib(fig)
