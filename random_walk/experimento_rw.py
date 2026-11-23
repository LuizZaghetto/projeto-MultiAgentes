if __package__:
    from .modelo_rw import Modelo, AgentePredador, AgentePresa
else:
    from modelo_rw import Modelo, AgentePredador, AgentePresa


def rodar_experimento(num_jogos=100, max_steps=1000):
    if num_jogos <= 0:
        raise ValueError("num_jogos deve ser maior que zero.")

    vitorias_predadores = 0
    vitorias_presas = 0
    empates_timeout = 0
    turnos_totais = []

    print(f"Iniciando simulação de {num_jogos} jogos...")

    for i in range(1, num_jogos + 1):
        # Cada jogo ganha uma seed diferente ou usa a aleatoriedade padrão do Mesa
        modelo = Modelo(verbose=False)

        while True:
            # Condições de parada
            total_pred = sum(1 for a in modelo.agents if isinstance(a, AgentePredador))
            total_presa = sum(1 for a in modelo.agents if isinstance(a, AgentePresa))

            if total_presa == 0:
                vitorias_predadores += 1
                turnos_totais.append(modelo.steps)
                break
            elif total_pred == 0:
                vitorias_presas += 1
                turnos_totais.append(modelo.steps)
                break
            elif modelo.steps >= max_steps:
                empates_timeout += 1
                turnos_totais.append(modelo.steps)
                break

            modelo.step()

        if i % 20 == 0 or i == num_jogos:
            print(f"Progresso: {i}/{num_jogos} jogos concluídos.")

    # ---------------------------------------------------------
    # 3. Consolidação dos Resultados
    # ---------------------------------------------------------
    media_turnos = sum(turnos_totais) / len(turnos_totais) if turnos_totais else 0

    print("\n" + "=" * 40)
    print("           RESULTADO FINAL")
    print("=" * 40)
    print(f"Total de jogos simulados: {num_jogos}")
    print(f"Vitórias dos Predadores: {vitorias_predadores} ({vitorias_predadores / num_jogos * 100:.1f}%)")
    print(f"Vitórias das Presas:     {vitorias_presas} ({vitorias_presas / num_jogos * 100:.1f}%)")
    if empates_timeout > 0:
        print(f"Empates (Timeout {max_steps} turnos): {empates_timeout}")
    print(f"Duração média dos jogos: {media_turnos:.1f} turnos")
    print("=" * 40)


if __name__ == "__main__":
    rodar_experimento(num_jogos=100)
