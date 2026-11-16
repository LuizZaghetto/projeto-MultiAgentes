from pathlib import Path
import gdown
import solara
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
if __package__:
    from .modelo_rw import Modelo, AgentePredador, AgentePresa
else:
    from modelo_rw import Modelo, AgentePredador, AgentePresa

# Configuração dos arquivos de imagem do Google Drive
ID_GATO = "1-OxS1QX7SndwamrLeNz3vBPwTTetGEhI"
ID_RATO = "1hhXI74sKxfgGSiGZkdyrYF2JomMq-oGo"

def carregar_imagem_drive(file_id, nome_destino):
    destino = Path(__file__).resolve().parent / nome_destino
    if not destino.exists():
        url = f"https://drive.google.com/uc?id={file_id}"
        print(f"Baixando {nome_destino} do Google Drive...")
        gdown.download(url, str(destino), quiet=False)
    return mpimg.imread(destino)

# Baixa uma única vez e armazena na memória do script
IMG_PREDADOR = carregar_imagem_drive(ID_GATO, "gato.png")
IMG_PRESA = carregar_imagem_drive(ID_RATO, "rato.png")

modelo_estado = solara.reactive(Modelo(n_pred=5, n_presa=30, verbose=True))
forca_update = solara.reactive(0)

@solara.component
def Page():
    def rodar_step():
        modelo_estado.value.step()
        modelo_estado.set(modelo_estado.value)
        forca_update.value += 1

    def resetar():
        modelo_estado.set(Modelo(n_pred=5, n_presa=30, verbose=True))
        forca_update.value += 1

    _ = forca_update.value

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 9.5)
    ax.set_xticks(range(10))
    ax.set_yticks(range(10))
    ax.grid(True, linestyle="--", alpha=0.5)

    for agent in modelo_estado.value.agents:
        x, y = agent.cell.coordinate

        if isinstance(agent, AgentePredador):
            # Imagem do Gato
            img_box = OffsetImage(IMG_PREDADOR, zoom=0.18)
            ab = AnnotationBbox(img_box, (x, y), frameon=False)
            ax.add_artist(ab)
            ax.annotate(f"E:{agent.energy}", (x, y), textcoords="offset points",
                        xytext=(0, 14), ha='center', fontsize=8, fontweight='bold', color='darkred')

        elif isinstance(agent, AgentePresa):
            # Imagem do Rato escalonada proporcionalmente ao peso
            fator_zoom = 0.03 + (agent.peso * 0.004)
            img_box = OffsetImage(IMG_PRESA, zoom=fator_zoom)
            ab = AnnotationBbox(img_box, (x, y), frameon=False)
            ax.add_artist(ab)
            ax.annotate(f"{agent.peso}", (x, y), textcoords="offset points",
                        xytext=(0, -14), ha='center', fontsize=7, color='darkgreen')

    total_pred = len([a for a in modelo_estado.value.agents if isinstance(a, AgentePredador)])
    total_presa = len([a for a in modelo_estado.value.agents if isinstance(a, AgentePresa)])
    ax.set_title(f"Turno: {modelo_estado.value.steps} | Predadores: {total_pred} | Presas: {total_presa}")
    plt.close(fig)

    with solara.Column():
        with solara.Row():
            solara.Button("Avançar Turno (Step)", on_click=rodar_step, color="primary")
            solara.Button("Resetar", on_click=resetar)
        solara.FigureMatplotlib(fig)
