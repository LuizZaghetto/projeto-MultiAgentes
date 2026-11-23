from pathlib import Path
import sys

# Permite executar os scripts diretamente a partir de suas pastas.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regras_comuns import (
    N_PREDADORES, N_PRESAS, PredadorBase, PresaBase, inicializar_populacao,
)

import time
import mesa


class AgentePredador(PredadorBase):
    def __init__(self, model, energy):
        super().__init__(model, energy)
        self.proxima_celula = None
        self.alvo_atual = None

    def step(self):
        # Custo proporcional com mínimo de 2 para evitar que ele fique travado com 1 de energia para sempre
        self.consumir_energia()

        # Filtra vizinhos que NÃO possuem outro predador
        vizinhos_sem_gato = [
            c for c in self.cell.neighborhood
            if not any(isinstance(a, AgentePredador) and a is not self for a in self.model.agents if a.cell == c)
        ]

        if self.proxima_celula is not None:
            # Só avança para a célula do orquestrador se não houver outro gato nela
            ocupada_por_gato = any(
                isinstance(a, AgentePredador) and a is not self and a.cell == self.proxima_celula
                for a in self.model.agents
            )
            if not ocupada_por_gato:
                self.cell = self.proxima_celula
            elif vizinhos_sem_gato:
                self.cell = self.random.choice(vizinhos_sem_gato)
            self.proxima_celula = None
        else:
            if vizinhos_sem_gato:
                self.cell = self.random.choice(vizinhos_sem_gato)

        self.capturar_presa(AgentePresa)

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

        # Orquestra alvos iniciais antes da coleta do turno 0
        self.orquestrar_predadores()

        # Configuração do DataCollector para análise das métricas
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
        self.datacollector.collect(self)

    def _distancia_chebyshev(self, coord1, coord2):
        return max(abs(coord1[0] - coord2[0]), abs(coord1[1] - coord2[1]))

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
        return len(alvos) / len(set(alvos))

    def _calcular_dispersao_predadores(self):
        """Distância média de Chebyshev entre todos os pares de predadores vivos."""
        predadores = [a for a in self.agents if isinstance(a, AgentePredador)]
        n = len(predadores)
        if n < 2:
            return 0.0
        distancias = [
            max(abs(predadores[i].cell.coordinate[0] - predadores[j].cell.coordinate[0]),
                abs(predadores[i].cell.coordinate[1] - predadores[j].cell.coordinate[1]))
            for i in range(n)
            for j in range(i + 1, n)
        ]
        return sum(distancias) / len(distancias)

    # Orquestração dos predadores, sendo que uma presa não pode ser alvo de mais de um predador
    def orquestrar_predadores(self):
        predadores = [a for a in self.agents if isinstance(a, AgentePredador)]
        presas = [a for a in self.agents if isinstance(a, AgentePresa)]

        if not presas or not predadores:
            for predador in predadores:
                predador.alvo_atual = None
                predador.proxima_celula = None
            return

        # Ordena os predadores para que quem já está mais perto de alguma presa escolha primeiro
        predadores_ordenados = sorted(
            predadores,
            key=lambda pred: min(
                self._distancia_chebyshev(pred.cell.coordinate, presa.cell.coordinate)
                for presa in presas
            )
        )

        celulas_reservadas = {p.cell for p in predadores}
        presas_alvejadas = set()

        for predador in predadores_ordenados:
            px, py = predador.cell.coordinate

            # Prioriza presas que ainda não têm um predador designado
            presas_disponiveis = [p for p in presas if p not in presas_alvejadas]
            if not presas_disponiveis:
                presas_disponiveis = presas

            presa_mais_proxima = min(
                presas_disponiveis,
                key=lambda p: self._distancia_chebyshev((px, py), p.cell.coordinate)
            )

            presas_alvejadas.add(presa_mais_proxima)
            predador.alvo_atual = presa_mais_proxima
            alvo_coord = presa_mais_proxima.cell.coordinate

            celulas_reservadas.discard(predador.cell)
            vizinhos_livres = [
                c for c in predador.cell.neighborhood
                if c not in celulas_reservadas
            ]

            if vizinhos_livres:
                melhor_celula = min(
                    vizinhos_livres,
                    key=lambda c: self._distancia_chebyshev(c.coordinate, alvo_coord)
                )
                predador.proxima_celula = melhor_celula
                celulas_reservadas.add(melhor_celula)
            else:
                predador.proxima_celula = predador.cell
                celulas_reservadas.add(predador.cell)

    def step(self):
        inicio = time.perf_counter()

        # 1. Todos os ratos agem primeiro
        self.agents.select(agent_type=AgentePresa).shuffle_do("step")

        # 2. Orquestrador lê a nova posição dos ratos e guia os gatos sem sobrepor
        self.orquestrar_predadores()

        # 3. Todos os gatos agem
        self.agents.select(agent_type=AgentePredador).shuffle_do("step")

        # 4. Atualiza as linhas tracejadas para exibição no gráfico
        self.orquestrar_predadores()

        # 5. Registra o tempo do turno e coleta as métricas
        self.tempo_ultimo_step_ms = (time.perf_counter() - inicio) * 1000
        self.datacollector.collect(self)
