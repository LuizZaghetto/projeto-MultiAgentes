import mesa


class AgentePredador(mesa.discrete_space.CellAgent):
    def __init__(self, model, energy):
        super().__init__(model)
        self.energy = energy

    def eat(self, presa):
        nutricao = 2 + int(presa.peso * 1.5)
        custo_abate = int(presa.peso * 0.8)
        ganho_liquido = max(5, nutricao - custo_abate)

        self.energy += ganho_liquido
        if self.model.verbose:
            print(f"[CAPTURA] Gato {self.unique_id} devorou Presa {presa.unique_id}...")
        presa.remove()

    def step(self):
        self.energy -= 1

        # Só escolhe entre células vizinhas que não tenham outro gato
        vizinhos_sem_gato = [
            c for c in self.cell.neighborhood
            if not any(isinstance(a, AgentePredador) and a is not self for a in self.model.agents if a.cell == c)
        ]
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
        vizinhos = list(self.cell.neighborhood)
        if vizinhos:
            self.cell = self.random.choice(vizinhos)


class Modelo(mesa.Model):
    def __init__(self, n_pred=5, n_presa=30, verbose=False, **kwargs):
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

    def step(self):
        # 1. Todos os ratos agem primeiro
        self.agents.select(agent_type=AgentePresa).shuffle_do("step")

        # 2. Todos os gatos agem depois
        self.agents.select(agent_type=AgentePredador).shuffle_do("step")
