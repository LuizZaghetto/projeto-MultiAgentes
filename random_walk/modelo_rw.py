from pathlib import Path
import sys

# Permite executar os scripts diretamente a partir de suas pastas.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regras_comuns import (
    N_PREDADORES, N_PRESAS, PredadorBase, PresaBase, inicializar_populacao,
)

import mesa


class AgentePredador(PredadorBase):
    def step(self):
        self.consumir_energia()

        # Só escolhe entre células vizinhas que não tenham outro gato
        vizinhos_sem_gato = [
            c for c in self.cell.neighborhood
            if not any(isinstance(a, AgentePredador) and a is not self for a in self.model.agents if a.cell == c)
        ]
        if vizinhos_sem_gato:
            self.cell = self.random.choice(vizinhos_sem_gato)

        self.capturar_presa(AgentePresa)

        self.verificar_inanicao()


class AgentePresa(PresaBase):
    def step(self):
        vizinhos = list(self.cell.neighborhood)
        if vizinhos:
            self.cell = self.random.choice(vizinhos)


class Modelo(mesa.Model):
    def __init__(self, n_pred=N_PREDADORES, n_presa=N_PRESAS, verbose=False, **kwargs):
        super().__init__(**kwargs)
        self.verbose = verbose
        inicializar_populacao(self, AgentePredador, AgentePresa, n_pred, n_presa)

    def step(self):
        # 1. Todos os ratos agem primeiro
        self.agents.select(agent_type=AgentePresa).shuffle_do("step")

        # 2. Todos os gatos agem depois
        self.agents.select(agent_type=AgentePredador).shuffle_do("step")
