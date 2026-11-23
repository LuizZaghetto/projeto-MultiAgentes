import sys
if __package__:
    from . import modelo as mod_padrao
    from . import modelo_fuga_rato as mod_fuga
else:
    import modelo as mod_padrao
    import modelo_fuga_rato as mod_fuga


def rodar_experimento(modulo, nome_modo, num_jogos=100, max_steps=1000):
    if num_jogos <= 0:
        raise ValueError("num_jogos deve ser maior que zero.")

    vitorias_predadores = 0
    vitorias_presas = 0
    empates_timeout = 0
    turnos_totais = []
    energias_vencedoras = []

    print(f"\nIniciando simulação de {num_jogos} jogos [{nome_modo}]...")

    for i in range(1, num_jogos + 1):
        modelo = modulo.Modelo(verbose=False)

        while True:
            total_pred = sum(1 for a in modelo.agents if isinstance(a, modulo.AgentePredador))
            total_presa = sum(1 for a in modelo.agents if isinstance(a, modulo.AgentePresa))

            if total_presa == 0:
                vitorias_predadores += 1
                turnos_totais.append(modelo.steps)
                # Coleta a energia de todos os predadores sobreviventes na vitória
                predadores_sobreviventes = [a for a in modelo.agents if isinstance(a, modulo.AgentePredador)]
                if predadores_sobreviventes:
                    energias_vencedoras.extend([p.energy for p in predadores_sobreviventes])
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

    media_turnos = sum(turnos_totais) / len(turnos_totais) if turnos_totais else 0
    media_energia_vencedores = sum(energias_vencedoras) / len(energias_vencedoras) if energias_vencedoras else 0

    print("\n" + "=" * 45)
    print(f" RESULTADO FINAL - {nome_modo}")
    print("=" * 45)
    print(f"Total de jogos simulados: {num_jogos}")
    print(f"Vitórias dos Predadores: {vitorias_predadores} ({vitorias_predadores / num_jogos * 100:.1f}%)")
    print(f"Vitórias das Presas:     {vitorias_presas} ({vitorias_presas / num_jogos * 100:.1f}%)")
    if empates_timeout > 0:
        print(f"Empates (Timeout {max_steps} turnos): {empates_timeout}")
    print(f"Duração média dos jogos: {media_turnos:.1f} turnos")
    print(f"Energia média dos predadores (vitórias): {media_energia_vencedores:.1f}")
    print("=" * 45)


if __name__ == "__main__":
    escolha = sys.argv[1] if len(sys.argv) > 1 else input(
        "Escolha o modelo:\n"
        "[1] Rato Padrão (modelo.py)\n"
        "[2] Rato com Fuga 3x3 (modelo_fuga.py)\n"
        "[3] Rodar ambos e comparar\n"
        "Opção: "
    ).strip()

    if escolha == "1":
        rodar_experimento(mod_padrao, "Rato Padrão (Aleatório)")
    elif escolha == "2":
        rodar_experimento(mod_fuga, "Rato com Fuga (3x3)")
    else:
        rodar_experimento(mod_padrao, "Rato Padrão (Aleatório)")
        rodar_experimento(mod_fuga, "Rato com Fuga (3x3)")
