from pathlib import Path
import solara

if __package__:
    from . import modelo_rw
else:
    import modelo_rw

from interface_comum import InterfaceSimulacao


MODOS = {"Movimento aleatório": modelo_rw}


@solara.component
def Page():
    InterfaceSimulacao(
        titulo="Random walk",
        modos=MODOS,
        pasta_imagens=Path(__file__).resolve().parent,
    )
