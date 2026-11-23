from pathlib import Path
import sys

# Permite executar os scripts diretamente a partir de suas pastas.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regras_comuns import (
    N_PREDADORES, N_PRESAS, PredadorBase, PresaBase, inicializar_populacao,
)

import mesa
import time


class AgentePredador(PredadorBase):
    def __init__(self, model, energy, raio_visao=3):
        super().__init__(model, energy)
        self.raio_visao = raio_visao
        self.alvo_atual = None

    def _distancia_chebyshev(self, coord1, coord2):
        return max(abs(coord1[0] - coord2[0]), abs(coord1[1] - coord2[1]))

    def step(self):
        self.consumir_energia()

        # Filtra células vizinhas que não estão ocupadas por outro gato no momento
        vizinhos_sem_gato = [
            c for c in self.cell.neighborhood
            if not any(isinstance(a, AgentePredador) and a is not self for a in self.model.agents if a.cell == c)
        ]

        # 1. Percepção individual: busca presas dentro do seu raio de visão
        px, py = self.cell.coordinate
        presas_visiveis = [
            a for a in self.model.agents
            if isinstance(a, AgentePresa)
            and self._distancia_chebyshev((px, py), a.cell.coordinate) <= self.raio_visao
        ]

        if presas_visiveis and vizinhos_sem_gato:
            # Prioriza presas visíveis que ainda não são alvo de outro gato.
            alvos_dos_outros = {
                a.alvo_atual for a in self.model.agents
                if isinstance(a, AgentePredador) and a is not self
            }
            presas_livres = [p for p in presas_visiveis if p not in alvos_dos_outros]
            alvo = min(
                presas_livres or presas_visiveis,
                key=lambda p: self._distancia_chebyshev((px, py), p.cell.coordinate)
            )
            self.alvo_atual = alvo
            alvo_coord = alvo.cell.coordinate

            # Avança para o vizinho livre que mais reduz a distância até o alvo
            melhor_celula = min(
                vizinhos_sem_gato,
                key=lambda c: self._distancia_chebyshev(c.coordinate, alvo_coord)
            )
            self.cell = melhor_celula
        else:
            # Sem presas à vista: patrulha aleatoriamente
            self.alvo_atual = None
            if vizinhos_sem_gato:
                self.cell = self.random.choice(vizinhos_sem_gato)

        # 2. Verifica captura na nova célula
        if self.capturar_presa(AgentePresa):
            self.alvo_atual = None

        # 3. Verifica inanição
        self.verificar_inanicao()

class AgentePresa(PresaBase):
    def step(self):
        x_atual, y_atual = self.cell.coordinate
        vizinhos_validos = [
            c for c in self.cell.neighborhood
            if abs(c.coordinate[0] - x_atual) <= 1 and abs(c.coordinate[1] - y_atual) <= 1
        ]
        if vizinhos_validos:
            self.cell = self.random.choice(vizinhos_validos)


class Modelo(mesa.Model):
    def __init__(self, n_pred=N_PREDADORES, n_presa=N_PRESAS, verbose=False, **kwargs):
        super().__init__(**kwargs)
        self.verbose = verbose
        self.tempo_ultimo_step_ms = 0.0
        inicializar_populacao(self, AgentePredador, AgentePresa, n_pred, n_presa)

        # utilizando o data collector pra analisar as métricas

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Presas_Vivas": lambda m: sum(1 for a in m.agents if isinstance(a, AgentePresa)),
                "Predadores_Vivos": lambda m: sum(1 for a in m.agents if isinstance(a, AgentePredador)),
                "Energia_Media_Predadores": self._calcular_energia_media,
                "Redundancia_Alvos": self._calcular_redundancia_alvos,
                "Dispersao_Predadores": self._calcular_dispersao_predadores,
                "Tempo_Step_ms": lambda m: m.tempo_ultimo_step_ms,
            }
        )

        # coleta do estado inicial
        self.datacollector.collect(self)

    def _calcular_energia_media(self):
        predadores = [a for a in self.agents if isinstance(a, AgentePredador)]
        if not predadores:
            return 0.0
        return sum(p.energy for p in predadores) / len(predadores)

    def _calcular_redundancia_alvos(self):
        """Média de predadores perseguindo o mesmo alvo (1.0 = coordenação perfeita sem conflito)."""
        alvos = [
            a.alvo_atual for a in self.agents
            if isinstance(a, AgentePredador) and getattr(a, "alvo_atual", None) is not None
        ]
        if not alvos:
            return 0.0
        alvos_unicos = set(alvos)
        return len(alvos) / len(alvos_unicos)

    def _calcular_dispersao_predadores(self):
        """Distância média de Chebyshev entre todos os pares de predadores vivos."""
        predadores = [a for a in self.agents if isinstance(a, AgentePredador)]
        n = len(predadores)
        if n < 2:
            return 0.0
        distancias = []
        for i in range(n):
            for j in range(i + 1, n):
                c1 = predadores[i].cell.coordinate
                c2 = predadores[j].cell.coordinate
                distancias.append(max(abs(c1[0] - c2[0]), abs(c1[1] - c2[1])))
        return sum(distancias) / len(distancias)


    def step(self):
        inicio = time.perf_counter()
        # 1. Presas agem primeiro
        self.agents.select(agent_type=AgentePresa).shuffle_do("step")

        # 2. Predadores agem individualmente, sem orquestração central
        self.agents.select(agent_type=AgentePredador).shuffle_do("step")

        self.tempo_ultimo_step_ms = (time.perf_counter() - inicio) * 1000
        self.datacollector.collect(self)
