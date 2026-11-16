import mesa


class AgentePredador(mesa.discrete_space.CellAgent):
    def __init__(self, model, energy):
        super().__init__(model)
        self.energy = energy
        self.proxima_celula = None
        self.alvo_atual = None

    def eat(self, presa):
        nutricao = 2 + int(presa.peso)
        custo_abate = int(presa.peso * 0.8)
        ganho_liquido = max(5, nutricao - custo_abate)

        self.energy += ganho_liquido
        if self.model.verbose:
            print(f"[CAPTURA] Gato {self.unique_id} devorou Presa {presa.unique_id}...")
        presa.remove()

    def step(self):
        # Custo proporcional com mínimo de 1 para evitar que ele fique travado com 1 de energia para sempre
        self.energy -= max(2, int(self.energy / 10))

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

        presas_aqui = [
            a for a in self.model.agents
            if isinstance(a, AgentePresa) and a.cell == self.cell
        ]

        if presas_aqui:
            self.eat(presas_aqui[0])

        if self.energy <= 0:
            if self.model.verbose:
                print(f"[MORTE] Predador {self.unique_id} morreu de fome.")
            self.remove()


class AgentePresa(mesa.discrete_space.CellAgent):
    def __init__(self, model, weight):
        super().__init__(model)
        self.peso = weight

    def step(self):
        x_atual, y_atual = self.cell.coordinate
        vizinhos_validos = [
            c for c in self.cell.neighborhood
            if abs(c.coordinate[0] - x_atual) <= 1 and abs(c.coordinate[1] - y_atual) <= 1
        ]
        if vizinhos_validos:
            self.cell = self.random.choice(vizinhos_validos)


class Modelo(mesa.Model):
    def __init__(self, n_pred=5, n_presa=18, verbose=False, **kwargs):
        super().__init__(**kwargs)
        self.verbose = verbose
        self.grid = mesa.discrete_space.OrthogonalMooreGrid((10, 10), torus=False, random=self.random)

        total_agentes = n_pred + n_presa
        total_celulas = self.grid.width * self.grid.height
        if total_agentes > total_celulas:
            raise ValueError(f"O grid ({total_celulas} células) não comporta {total_agentes} agentes sem sobreposição.")

        initial_energy = 15
        initial_weight = self.rng.integers(5, 10, size=n_presa)

        for agent in AgentePredador.create_agents(self, n_pred, initial_energy):
            agent.cell = self.grid.empties.select_random_cell()

        for agent in AgentePresa.create_agents(self, n_presa, initial_weight):
            agent.cell = self.grid.empties.select_random_cell()

        self.orquestrar_predadores()

    def _distancia_chebyshev(self, coord1, coord2):
        return max(abs(coord1[0] - coord2[0]), abs(coord1[1] - coord2[1]))

    def orquestrar_predadores(self):
        predadores = [a for a in self.agents if isinstance(a, AgentePredador)]
        presas = [a for a in self.agents if isinstance(a, AgentePresa)]

        if not presas or not predadores:
            for predador in predadores:
                predador.alvo_atual = None
                predador.proxima_celula = None
            return

        celulas_reservadas = {p.cell for p in predadores}

        for predador in predadores:
            px, py = predador.cell.coordinate
            presa_mais_proxima = min(
                presas,
                key=lambda p: self._distancia_chebyshev((px, py), p.cell.coordinate)
            )

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
        # 1. Todos os ratos agem primeiro
        self.agents.select(agent_type=AgentePresa).shuffle_do("step")

        # 2. Orquestrador lê a nova posição dos ratos e guia os gatos sem sobrepor
        self.orquestrar_predadores()

        # 3. Todos os gatos agem
        self.agents.select(agent_type=AgentePredador).shuffle_do("step")

        # 4. Atualiza as linhas tracejadas para exibição no gráfico
        self.orquestrar_predadores()
