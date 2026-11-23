from pathlib import Path
import solara

if __package__:
    from . import modelo as mod_padrao
    from . import modelo_fuga_rato as mod_fuga
else:
    import modelo as mod_padrao
    import modelo_fuga_rato as mod_fuga

from interface_comum import InterfaceSimulacao


MODOS = {
    "Rato aleatório": mod_padrao,
    "Fuga 3×3": mod_fuga,
}


@solara.component
def Page():
    InterfaceSimulacao(
        titulo="Orquestrador central",
        modos=MODOS,
        pasta_imagens=Path(__file__).resolve().parent,
    )
