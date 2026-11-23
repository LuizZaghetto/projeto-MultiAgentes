import sys
from pathlib import Path

import pandas as pd
import solara
from matplotlib.figure import Figure

from orq_geral import modelo as central_padrao
from orq_geral import modelo_fuga_rato as central_fuga
from orq_individual import modelo as indiv_padrao
from orq_individual import modelo_fuga_rato as indiv_fuga


JOGOS_POR_CENARIO = 100
LIMITE_TURNOS = 1000
CENARIOS = (
    (central_padrao, "Orquestrador", "Rato Aleatório"),
    (central_fuga, "Orquestrador", "Rato Fuga 3x3"),
    (indiv_padrao, "Individual", "Rato Aleatório"),
    (indiv_fuga, "Individual", "Rato Fuga 3x3"),
)


def jogar_partida(modulo, semente, max_steps=LIMITE_TURNOS, *, ao_registrar_turno=None, cancelamento=None):
    """Executa uma partida e devolve o modelo final e o resultado."""
    modelo = modulo.Modelo(verbose=False, rng=semente)
    while cancelamento is None or not cancelamento.is_set():
        if ao_registrar_turno is not None:
            ao_registrar_turno(modelo)

        if not modelo.agents.select(agent_type=modulo.AgentePresa):
            return modelo, "Vitória dos gatos"
        if not modelo.agents.select(agent_type=modulo.AgentePredador):
            return modelo, "Vitória dos ratos"
        if modelo.steps >= max_steps:
            return modelo, "Limite de turnos"
        modelo.step()

    raise InterruptedError("Experimento interrompido.")


def rodar_experimento(
    modulo, arquitetura, tipo_presa, num_jogos=JOGOS_POR_CENARIO, max_steps=LIMITE_TURNOS,
    *, ao_concluir_partida=None, cancelamento=None, exibir_progresso=True,
):
    if num_jogos < 1:
        raise ValueError("O número de jogos deve ser positivo.")

    vitorias_pred = 0
    vitorias_presa = 0
    empates_timeout = 0

    turnos_totais = []
    turnos_vitoria_pred = []
    energias_vencedoras = []
    redundancias_medias = []
    dispersoes_medias = []
    tempos_step_ms = []

    if exibir_progresso:
        print(f"\nIniciando {num_jogos} jogos -> [{arquitetura} | {tipo_presa}]...")

    for i in range(1, num_jogos + 1):
        modelo, resultado = jogar_partida(modulo, i, max_steps, cancelamento=cancelamento)
        turnos_totais.append(modelo.steps)
        if resultado == "Vitória dos gatos":
            vitorias_pred += 1
            turnos_vitoria_pred.append(modelo.steps)
            sobreviventes = modelo.agents.select(agent_type=modulo.AgentePredador)
            energias_vencedoras.extend(p.energy for p in sobreviventes)
        elif resultado == "Vitória dos ratos":
            vitorias_presa += 1
        else:
            empates_timeout += 1

        # Extrai as séries coletadas pelo DataCollector nesta partida
        df_jogo = modelo.datacollector.get_model_vars_dataframe()
        if "Redundancia_Alvos" in df_jogo.columns:
            # Ignora turnos sem nenhum alvo ativo (redundância == 0)
            ativos = df_jogo[df_jogo["Redundancia_Alvos"] > 0]["Redundancia_Alvos"]
            if not ativos.empty:
                redundancias_medias.append(ativos.mean())

        if "Dispersao_Predadores" in df_jogo.columns:
            dispersoes_medias.append(df_jogo["Dispersao_Predadores"].mean())

        if "Tempo_Step_ms" in df_jogo.columns and len(df_jogo) > 1:
            tempos_step_ms.append(df_jogo["Tempo_Step_ms"].iloc[1:].mean())

        if ao_concluir_partida is not None:
            ao_concluir_partida(i, resultado, modelo.steps)
        if exibir_progresso and (i % 25 == 0 or i == num_jogos):
            print(f"  Progresso: {i}/{num_jogos}")

    return {
        "Arquitetura": arquitetura,
        "Presa": tipo_presa,
        "Jogos": num_jogos,
        "Vitorias_Pred_%": round(vitorias_pred / num_jogos * 100, 1),
        "Vitorias_Presa_%": round(vitorias_presa / num_jogos * 100, 1),
        "Timeouts": empates_timeout,
        "Turnos_Medio_Geral": round(sum(turnos_totais) / len(turnos_totais), 1),
        "Turnos_Medio_Vitoria_Pred": round(sum(turnos_vitoria_pred) / len(turnos_vitoria_pred), 1) if turnos_vitoria_pred else 0.0,
        "Energia_Media_Sobreviventes": round(sum(energias_vencedoras) / len(energias_vencedoras), 1) if energias_vencedoras else 0.0,
        "Redundancia_Gatos_Por_Alvo": round(sum(redundancias_medias) / len(redundancias_medias), 2) if redundancias_medias else 0.0,
        "Dispersao_Media_Grid": round(sum(dispersoes_medias) / len(dispersoes_medias), 2) if dispersoes_medias else 0.0,
        "Tempo_Medio_Step_ms": round(sum(tempos_step_ms) / len(tempos_step_ms), 4) if tempos_step_ms else 0.0,
    }


def figura_comparativa(df_resumo):
    fig = Figure(figsize=(12, 8))
    axes = fig.subplots(2, 2)
    cenarios = [f"{r['Arquitetura']}\n({r['Presa']})" for _, r in df_resumo.iterrows()]
    cores = ["#2b5c8f", "#1f77b4", "#d95f02", "#e6ab02"]

    # 1. Taxa de Vitória dos Predadores (%)
    axes[0, 0].bar(cenarios, df_resumo["Vitorias_Pred_%"], color=cores)
    axes[0, 0].set_title("Taxa de Vitória dos Predadores (%)")
    axes[0, 0].set_ylim(0, 105)
    axes[0, 0].grid(axis="y", linestyle="--", alpha=0.4)

    # 2. Turnos Médios até Vitória dos Predadores
    axes[0, 1].bar(cenarios, df_resumo["Turnos_Medio_Vitoria_Pred"], color=cores)
    axes[0, 1].set_title("Eficiência Temporal (Turnos Médios p/ Caçar Todas)")
    axes[0, 1].grid(axis="y", linestyle="--", alpha=0.4)

    # 3. Redundância de Alvos (Gatos por Alvo)
    axes[1, 0].bar(cenarios, df_resumo["Redundancia_Gatos_Por_Alvo"], color=cores)
    axes[1, 0].axhline(1.0, color="black", linestyle=":", label="Ideal (Sem conflito = 1.0)")
    axes[1, 0].set_title("Conflito de Alvos (Média de Gatos por Presa)")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(axis="y", linestyle="--", alpha=0.4)

    # 4. Custo Computacional (ms por turno)
    axes[1, 1].bar(cenarios, df_resumo["Tempo_Medio_Step_ms"], color=cores)
    axes[1, 1].set_title("Custo Computacional (ms por Turno)")
    axes[1, 1].grid(axis="y", linestyle="--", alpha=0.4)

    for ax in axes.flat:
        ax.tick_params(axis="x", labelsize=8)

    fig.tight_layout()
    return fig


def gerar_graficos_comparativos(df_resumo, arquivo_saida="comparativo_arquiteturas.png"):
    figura_comparativa(df_resumo).savefig(arquivo_saida, dpi=150)
    print(f"\nGráfico comparativo salvo em: {arquivo_saida}")


@solara.component
def Page():
    from app_comparativo import Page as PaginaComparativo

    PaginaComparativo()


def executar_no_terminal():
    resultados = [
        rodar_experimento(mod, arq, presa)
        for mod, arq, presa in CENARIOS
    ]

    df_final = pd.DataFrame(resultados)
    print("\n" + "=" * 90)
    print("TABELA COMPARATIVA FINAL")
    print("=" * 90)
    print(df_final.to_string(index=False))

    df_final.to_csv("resultados_comparativos.csv", index=False)
    print("\nTabela salva em: resultados_comparativos.csv")
    gerar_graficos_comparativos(df_final)


# O Solara também usa __name__ == "__main__" ao carregar páginas Python.
# O lote no terminal só começa quando o Python executa este arquivo diretamente.
if __name__ == "__main__" and Path(sys.argv[0]).resolve() == Path(__file__).resolve():
    executar_no_terminal()
