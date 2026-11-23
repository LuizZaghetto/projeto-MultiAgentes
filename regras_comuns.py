"""Regras de populacao, energia e captura compartilhadas pelos cinco modelos."""

import mesa


N_PREDADORES = 5
N_PRESAS = 18
DIMENSOES_GRID = (10, 10)
ENERGIA_INICIAL = 15
PESO_MINIMO = 5
PESO_MAXIMO = 9
CUSTO_MINIMO_TURNO = 2
DIVISOR_CUSTO_TURNO = 10
NUTRICAO_BASE = 2
FATOR_CUSTO_ABATE = 0.8
GANHO_MINIMO_CAPTURA = 5


class PredadorBase(mesa.discrete_space.CellAgent):
    def __init__(self, model, energy):
        super().__init__(model)
        self.energy = energy

    def consumir_energia(self):
        self.energy -= max(CUSTO_MINIMO_TURNO, int(self.energy / DIVISOR_CUSTO_TURNO))

    def eat(self, presa):
        nutricao = NUTRICAO_BASE + int(presa.peso)
        custo_abate = int(presa.peso * FATOR_CUSTO_ABATE)
        self.energy += max(GANHO_MINIMO_CAPTURA, nutricao - custo_abate)
        if self.model.verbose:
            print(f"[CAPTURA] Gato {self.unique_id} devorou Presa {presa.unique_id}...")
        presa.remove()

    def capturar_presa(self, tipo_presa):
        """Come no maximo uma presa na celula atual, apos o movimento."""
        presas_aqui = [
            a for a in self.model.agents
            if isinstance(a, tipo_presa) and a.cell == self.cell
        ]
        if presas_aqui:
            self.eat(presas_aqui[0])
            return True
        return False

    def verificar_inanicao(self):
        """Verifica a morte depois da oportunidade de alimentacao."""
        if self.energy <= 0:
            if self.model.verbose:
                print(f"[MORTE] Predador {self.unique_id} morreu de fome.")
            self.remove()


class PresaBase(mesa.discrete_space.CellAgent):
    def __init__(self, model, weight):
        super().__init__(model)
        self.peso = weight


def inicializar_populacao(modelo, tipo_predador, tipo_presa, n_pred, n_presa):
    """Cria o grid e posiciona os agentes sem sobreposicao inicial."""
    modelo.grid = mesa.discrete_space.OrthogonalMooreGrid(
        DIMENSOES_GRID, torus=False, random=modelo.random
    )
    total_agentes = n_pred + n_presa
    total_celulas = modelo.grid.width * modelo.grid.height
    if total_agentes > total_celulas:
        raise ValueError(
            f"O grid ({total_celulas} células) não comporta {total_agentes} agentes sem sobreposição."
        )

    pesos = modelo.rng.integers(PESO_MINIMO, PESO_MAXIMO + 1, size=n_presa)
    for agente in tipo_predador.create_agents(modelo, n_pred, ENERGIA_INICIAL):
        agente.cell = modelo.grid.empties.select_random_cell()
    for agente in tipo_presa.create_agents(modelo, n_presa, pesos):
        agente.cell = modelo.grid.empties.select_random_cell()
