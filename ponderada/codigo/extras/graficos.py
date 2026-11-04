#!/usr/bin/env python3
"""
graficos.py

Gera os gráficos e diagramas de img/ a partir das contas e de resultados/.
Precisa de matplotlib. As cores vêm de uma paleta validada para daltonismo.

Uso, a partir de ponderada/codigo: python3 extras/graficos.py
"""

import csv
import math
import random
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

from pipeline import ESTAGIOS, TRECHO, bolhas, simula, total_ciclos

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRADE = "#e6e5e0"
AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE = "#1baf7a"
CRITICO = "#d03b3b"

IC = 100_000
M = 0.055
PRAZO_MS = 5.0
ATRASO_SO_MS = 3.0
T_H_MS = IC * 1.5 / 48e6 * 1e3
T_DSP_MS = T_H_MS * 0.52

CODIGO = Path(__file__).resolve().parent.parent
RESULTADOS = CODIGO / "resultados"
IMAGENS = CODIGO.parent / "img"

plt.rcParams.update({
    "font.family": ["Noto Sans", "DejaVu Sans"],
    "font.size": 11,
    "axes.edgecolor": GRADE,
    "axes.linewidth": 1,
    "axes.labelcolor": TINTA_2,
    "axes.facecolor": SUPERFICIE,
    "figure.facecolor": SUPERFICIE,
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
})


def virgula(valor, casas=2):
    """
    Formata um número com vírgula decimal.

    Parâmetros:
        valor (float): número.
        casas (int): casas decimais.
    Retorno:
        str: número no formato brasileiro.
    Funcionamento:
        Formata normalmente e troca o ponto pela vírgula.
    """
    return f"{valor:.{casas}f}".replace(".", ",")


def titulos(figura, titulo, subtitulo):
    """
    Escreve título e subtítulo alinhados à esquerda.

    Parâmetros:
        figura (Figure): figura do matplotlib.
        titulo (str): a conclusão do gráfico.
        subtitulo (str): o que está sendo medido.
    Retorno:
        None.
    Funcionamento:
        Usa coordenadas da figura para alinhar o texto à margem.
    """
    figura.text(0.02, 0.96, titulo, fontsize=14, fontweight="bold", color=TINTA, va="top")
    figura.text(0.02, 0.895, subtitulo, fontsize=11, color=TINTA_2, va="top")


def limpa_eixos(eixos):
    """
    Deixa grade e eixos discretos.

    Parâmetros:
        eixos (Axes): eixos do gráfico.
    Retorno:
        None.
    Funcionamento:
        Remove as bordas de cima e da direita e põe a grade atrás dos dados.
    """
    eixos.spines["top"].set_visible(False)
    eixos.spines["right"].set_visible(False)
    eixos.spines["left"].set_visible(False)
    eixos.grid(True, axis="y", color=GRADE, linewidth=0.8)
    eixos.set_axisbelow(True)


def tempo_v_pior_caso(m):
    """
    Calcula o pior caso da Plataforma V para uma taxa de falta.

    Parâmetros:
        m (float): taxa de falta, de 0 a 1.
    Retorno:
        float: tempo por amostra mais o atraso do sistema, em ms.
    Funcionamento:
        Mesma fórmula da questão A1.2.
    """
    return IC * (1 + 1.3 * m * 120) / 1.2e9 * 1e3 + ATRASO_SO_MS


def grafico_limites():
    """
    Mostra até que taxa de falta a Plataforma V cumpre o prazo.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Compara a curva da V com os tempos constantes de H e H + DSP.
    """
    figura, eixos = plt.subplots(figsize=(8.6, 4.6), dpi=160)
    figura.subplots_adjust(left=0.07, right=0.97, top=0.76, bottom=0.13)
    titulos(figura, "A Plataforma V só cumpre o prazo com a taxa de falta abaixo de 14,7%",
            "Tempo de pior caso por amostra, com IC = 100.000 instruções")

    m_limite = (((PRAZO_MS - ATRASO_SO_MS) * 1e-3 * 1.2e9 / IC) - 1) / (1.3 * 120)
    xs = [i / 1000 for i in range(0, 201)]
    eixos.plot([x * 100 for x in xs], [tempo_v_pior_caso(x) for x in xs],
               color=AZUL, linewidth=2, label="Plataforma V", solid_capstyle="round")
    eixos.plot([0, 20], [T_H_MS, T_H_MS], color=LARANJA, linewidth=2, label="Plataforma H")
    eixos.plot([0, 20], [T_DSP_MS, T_DSP_MS], color=VERDE, linewidth=2, label="H + DSP")
    eixos.plot([0, 20], [PRAZO_MS, PRAZO_MS], color=TINTA, linewidth=1)

    eixos.scatter([M * 100], [tempo_v_pior_caso(M)], s=64, color=AZUL, zorder=5,
                  edgecolors=SUPERFICIE, linewidths=2)
    eixos.scatter([m_limite * 100], [PRAZO_MS], s=64, color=CRITICO, zorder=5,
                  edgecolors=SUPERFICIE, linewidths=2)

    eixos.annotate("minha taxa, 5,5%: 3,80 ms", (M * 100, tempo_v_pior_caso(M)), xytext=(0, 12),
                   textcoords="offset points", color=TINTA, ha="center", fontsize=10.5)
    eixos.annotate("limite: m = 14,74%", (m_limite * 100, PRAZO_MS), xytext=(0, 12),
                   textcoords="offset points", color=TINTA, ha="center", fontsize=10.5)
    eixos.text(0.15, PRAZO_MS + 0.1, "prazo de 5 ms", color=TINTA, fontsize=10.5)
    eixos.text(19.9, T_H_MS + 0.12, "H: 3,125 ms, em qualquer caso", color=TINTA, fontsize=10.5, ha="right")
    eixos.text(19.9, T_DSP_MS + 0.12, "H + DSP: 1,625 ms", color=TINTA, fontsize=10.5, ha="right")

    eixos.set_xlim(0, 20)
    eixos.set_ylim(0, 6.5)
    eixos.set_xticks([0, 5, 10, 15, 20])
    eixos.set_xticklabels(["0%", "5%", "10%", "15%", "20%"])
    eixos.set_xlabel("Taxa de falta na L1 (m)")
    eixos.set_ylabel("ms por amostra")
    limpa_eixos(eixos)
    eixos.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=3, frameon=False,
                 labelcolor=TINTA_2, fontsize=10.5, handlelength=1.6)
    figura.savefig(IMAGENS / "a1_limites.png")
    plt.close(figura)


def grafico_cache():
    """
    Desenha a escada de latência da hierarquia de memória.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Lê resultados/latencia_cache.tsv e marca os tamanhos de cache do
        núcleo usado no teste, informados pelo lscpu.
    """
    with open(RESULTADOS / "latencia_cache.tsv", encoding="utf-8") as arquivo:
        pontos = [(int(a), float(b)) for a, b in csv.reader(arquivo, delimiter="\t")]
    tamanhos = [p[0] for p in pontos]
    latencias = [p[1] for p in pontos]
    l1 = statistics.median(p[1] for p in pontos if p[0] <= 48)
    razao = latencias[-1] / l1

    figura, eixos = plt.subplots(figsize=(8.6, 4.2), dpi=160)
    figura.subplots_adjust(left=0.08, right=0.97, top=0.76, bottom=0.14)
    titulos(figura, f"Medido na minha máquina: a RAM é {razao:.0f} vezes mais lenta que a L1",
            "Tempo de um acesso à memória, conforme os dados deixam de caber em cada nível")

    eixos.plot(tamanhos, latencias, color=AZUL, linewidth=2, marker="o", markersize=4,
               markerfacecolor=AZUL, markeredgecolor=SUPERFICIE, markeredgewidth=0.8)
    eixos.set_xscale("log", base=2)
    eixos.set_yscale("log", base=10)
    for tamanho, rotulo in ((48, "L1d 48 KiB"), (1280, "L2 1,25 MiB"), (12288, "L3 12 MiB")):
        eixos.axvline(tamanho, color=TINTA_2, linewidth=0.8)
        eixos.text(tamanho * 0.9, 210, rotulo, color=TINTA, fontsize=10.5, ha="right", va="top")

    eixos.set_xticks([8, 64, 512, 4096, 32768, 262144])
    eixos.set_xticklabels(["8 KiB", "64 KiB", "512 KiB", "4 MiB", "32 MiB", "256 MiB"])
    eixos.set_yticks([1, 3, 10, 30, 100])
    eixos.set_yticklabels(["1", "3", "10", "30", "100"])
    eixos.minorticks_off()
    eixos.set_ylim(1, 240)
    eixos.set_xlabel("Tamanho dos dados percorridos")
    eixos.set_ylabel("ns por acesso (escala log)")
    limpa_eixos(eixos)
    figura.savefig(IMAGENS / "a1_cache.png")
    plt.close(figura)


def grafico_campanha():
    """
    Mostra quantas amostras cada execução perdeu.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Lê resultados/campanha.tsv e desenha um ponto por execução. A posição
        vertical dentro de cada linha é sorteada, com semente fixa, só para
        separar os pontos.
    """
    with open(RESULTADOS / "campanha.tsv", encoding="utf-8") as arquivo:
        execucoes = list(csv.reader(arquivo, delimiter="\t"))

    grupos = [
        ("Versão 3", "v3"),
        ("Versão 1, vários núcleos", "v1 vários"),
        ("Versão 1, um núcleo", "v1 um"),
        ("Versão 2", "v2"),
    ]
    sorteio = random.Random(2026)
    figura, eixos = plt.subplots(figsize=(8.6, 4.2), dpi=160)
    figura.subplots_adjust(left=0.265, right=0.97, top=0.71, bottom=0.14)
    titulos(figura, "A versão 1 muda a cada execução; as outras não",
            "Amostras perdidas de 20.000. Cada ponto é uma execução")

    pontos = {True: ([], []), False: ([], [])}
    rotulos = []
    for linha, (rotulo, prefixo) in enumerate(grupos):
        do_grupo = [e for e in execucoes if e[0].startswith(prefixo)]
        rotulos.append(f"{rotulo} ({len(do_grupo)})")
        for execucao in do_grupo:
            travou = execucao[5] == "sim"
            pontos[travou][0].append(int(execucao[3]))
            pontos[travou][1].append(linha + sorteio.uniform(-0.24, 0.24))

    eixos.scatter(*pontos[False], s=30, color=AZUL, marker="o", edgecolors=SUPERFICIE,
                  linewidths=0.6, label="não travou", zorder=3)
    eixos.scatter(*pontos[True], s=34, color=CRITICO, marker="D", edgecolors=SUPERFICIE,
                  linewidths=0.6, label="travou", zorder=3)

    eixos.set_yticks(range(len(grupos)))
    eixos.set_yticklabels(rotulos, color=TINTA, fontsize=10.5)
    eixos.set_ylim(-0.6, len(grupos) - 0.4)
    eixos.set_xlim(-500, 20800)
    eixos.set_xticks([0, 5000, 10000, 15000, 20000])
    eixos.set_xticklabels(["0", "5.000", "10.000", "15.000", "20.000"])
    eixos.set_xlabel("Amostras perdidas")
    eixos.spines["top"].set_visible(False)
    eixos.spines["right"].set_visible(False)
    eixos.spines["left"].set_visible(False)
    eixos.grid(True, axis="x", color=GRADE, linewidth=0.8)
    eixos.set_axisbelow(True)
    eixos.legend(loc="upper left", bbox_to_anchor=(-0.01, 1.17), ncol=2, frameon=False,
                 labelcolor=TINTA_2, fontsize=10.5, handletextpad=0.3)
    figura.savefig(IMAGENS / "a4_campanha.png")
    plt.close(figura)


def diagrama_pipeline(ordem, forwarding, titulo, arquivo):
    """
    Desenha um diagrama de pipeline ciclo a ciclo.

    Parâmetros:
        ordem (sequence[Instrucao]): instruções na ordem de execução.
        forwarding (bool): True liga o adiantamento de resultados.
        titulo (str): título da figura.
        arquivo (str): nome do PNG em img/.
    Retorno:
        None.
    Funcionamento:
        Usa os ciclos calculados por simula(), de pipeline.py. Os três
        diagramas têm a escala de 17 ciclos, para que a redução apareça no
        próprio desenho. Os ciclos parados ficam em laranja.
    """
    ciclos = simula(ordem, forwarding)
    figura, eixos = plt.subplots(figsize=(8.6, 3.6), dpi=160)
    figura.subplots_adjust(left=0.015, right=0.985, top=0.9, bottom=0.01)
    figura.text(0.02, 0.965, titulo, fontsize=13, fontweight="bold", color=TINTA, va="top")
    eixos.set_xlim(-5.2, 17.1)
    eixos.set_ylim(len(ordem) + 0.05, -1.0)
    eixos.axis("off")

    for ciclo in range(1, 18):
        eixos.text(ciclo - 0.5, -0.42, str(ciclo), ha="center", va="center", fontsize=9.5, color=TINTA_2)

    for linha, instrucao in enumerate(ordem):
        rotulo = f"I{TRECHO.index(instrucao) + 1}  {instrucao.texto}"
        eixos.text(-5.15, linha + 0.5, rotulo, va="center", fontsize=9.5, color=TINTA, family="monospace")
        inicio = 1 if linha == 0 else ciclos[linha - 1]["IF"] + 1
        for estagio in ESTAGIOS:
            fim = ciclos[linha][estagio]
            for ciclo in range(inicio, fim + 1):
                parado = ciclo != fim
                eixos.add_patch(FancyBboxPatch(
                    (ciclo - 1 + 0.05, linha + 0.07), 0.9, 0.86,
                    boxstyle="round,pad=0,rounding_size=0.12",
                    facecolor=LARANJA if parado else "#e7effa", edgecolor="none", zorder=2,
                ))
                eixos.text(ciclo - 0.5, linha + 0.5, estagio, ha="center", va="center", fontsize=9,
                           color="#ffffff" if parado else TINTA, zorder=3)
            inicio = fim + 1

    figura.savefig(IMAGENS / arquivo)
    plt.close(figura)


def diagramas_a2():
    """
    Gera os três diagramas da questão A2.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        A ordem sem bolhas é a do enunciado com I2 e I3 trocadas.
    """
    reordenado = (TRECHO[0], TRECHO[2], TRECHO[1], TRECHO[3], TRECHO[4], TRECHO[5], TRECHO[6])
    casos = (
        (TRECHO, False, "a2_sem_forwarding.png"),
        (TRECHO, True, "a2_com_forwarding.png"),
        (reordenado, True, "a2_reordenado.png"),
    )
    for ordem, forwarding, arquivo in casos:
        ciclos = simula(ordem, forwarding)
        nome = "Com forwarding" if forwarding else "Sem forwarding"
        if ordem is reordenado:
            nome = "Com forwarding e reordenado"
        titulo = f"{nome}: {total_ciclos(ciclos)} ciclos, {bolhas(ciclos)} bolhas"
        diagrama_pipeline(ordem, forwarding, titulo, arquivo)


def seta(eixos, origem, destino, cor=TINTA_2, largura=1.6, curva=0.0):
    """
    Desenha uma seta entre dois pontos.

    Parâmetros:
        eixos (Axes): eixos do diagrama.
        origem (tuple): ponto de saída.
        destino (tuple): ponto de chegada.
        cor (str): cor da seta.
        largura (float): espessura da linha.
        curva (float): curvatura; zero é uma reta.
    Retorno:
        None.
    Funcionamento:
        Usa FancyArrowPatch, que mantém a ponta com tamanho fixo.
    """
    eixos.add_patch(FancyArrowPatch(
        origem, destino, arrowstyle="-|>", mutation_scale=14, color=cor, linewidth=largura,
        connectionstyle=f"arc3,rad={curva}", shrinkA=0, shrinkB=0, zorder=2,
    ))


def caixa_estado(eixos, centro, texto, destaque=False):
    """
    Desenha um estado do diagrama.

    Parâmetros:
        eixos (Axes): eixos do diagrama.
        centro (tuple): centro da caixa.
        texto (str): nome do estado.
        destaque (bool): True pinta o estado em que a thread do sensor fica.
    Retorno:
        None.
    Funcionamento:
        Caixa de cantos arredondados, com o texto centralizado.
    """
    largura, altura = 1.5, 0.62
    x, y = centro[0] - largura / 2, centro[1] - altura / 2
    eixos.add_patch(FancyBboxPatch(
        (x, y), largura, altura, boxstyle="round,pad=0,rounding_size=0.1",
        facecolor=AZUL if destaque else "#f1f0ec", edgecolor=AZUL if destaque else "#c9c8c1",
        linewidth=1, zorder=3,
    ))
    eixos.text(centro[0], centro[1], texto, ha="center", va="center", fontsize=12, zorder=4,
               color="#ffffff" if destaque else TINTA, fontweight="bold" if destaque else "normal")


def diagrama_estados():
    """
    Desenha o diagrama de estados de um processo.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Usa os estados e os nomes de transição do slide da aula e destaca o
        estado em que a thread do sensor passa a maior parte do tempo.
    """
    figura, eixos = plt.subplots(figsize=(8.6, 4.3), dpi=160)
    figura.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    eixos.set_xlim(0, 10)
    eixos.set_ylim(-0.15, 5)
    eixos.axis("off")

    criacao, terminado = (1.4, 4.3), (8.6, 4.3)
    pronto, execucao, espera = (2.6, 2.5), (7.4, 2.5), (5.0, 0.7)
    caixa_estado(eixos, criacao, "Criação")
    caixa_estado(eixos, terminado, "Terminado")
    caixa_estado(eixos, pronto, "Pronto")
    caixa_estado(eixos, execucao, "Execução")
    caixa_estado(eixos, espera, "Espera", destaque=True)

    seta(eixos, (1.65, 3.99), (2.35, 2.81))
    eixos.text(2.2, 3.5, "admitido", fontsize=10.5, color=TINTA_2)
    seta(eixos, (7.65, 2.81), (8.35, 3.99))
    eixos.text(8.2, 3.3, "termina", fontsize=10.5, color=TINTA_2)
    seta(eixos, (3.35, 2.68), (6.65, 2.68))
    eixos.text(5.0, 2.8, "o escalonador escolhe", fontsize=10.5, color=TINTA_2, ha="center")
    seta(eixos, (6.65, 2.32), (3.35, 2.32))
    eixos.text(5.0, 2.05, "acaba a fatia de tempo", fontsize=10.5, color=TINTA_2, ha="center")
    seta(eixos, (7.1, 2.19), (5.6, 1.01))
    eixos.text(6.85, 1.42, "pede I/O ou\nespera um evento", fontsize=10.5, color=TINTA_2, va="center")
    seta(eixos, (4.4, 1.01), (2.9, 2.19))
    eixos.text(3.15, 1.42, "o evento\nacontece", fontsize=10.5, color=TINTA_2, va="center", ha="right")
    eixos.text(5.0, 0.08, "A thread do sensor fica aqui em 92% do tempo: dorme até a próxima amostra",
               fontsize=10.5, color=TINTA, ha="center")
    figura.savefig(IMAGENS / "a3_estados.png")
    plt.close(figura)


def no_thread(eixos, centro, nome):
    """
    Desenha uma thread do grafo de alocação.

    Parâmetros:
        eixos (Axes): eixos do diagrama.
        centro (tuple): centro do círculo.
        nome (str): nome da thread.
    Retorno:
        None.
    Funcionamento:
        Na notação da aula, processos e threads são círculos.
    """
    eixos.add_patch(Circle(centro, 0.62, facecolor="#f1f0ec", edgecolor="#c9c8c1", linewidth=1, zorder=3))
    eixos.text(centro[0], centro[1], nome, ha="center", va="center", fontsize=10.5, color=TINTA, zorder=4)


def no_recurso(eixos, centro, nome):
    """
    Desenha um recurso do grafo de alocação.

    Parâmetros:
        eixos (Axes): eixos do diagrama.
        centro (tuple): centro do quadrado.
        nome (str): nome do recurso.
    Retorno:
        None.
    Funcionamento:
        Na notação da aula, recursos são quadrados com uma bolinha por unidade.
    """
    lado = 0.86
    eixos.add_patch(Rectangle((centro[0] - lado / 2, centro[1] - lado / 2), lado, lado,
                              facecolor=SUPERFICIE, edgecolor=TINTA_2, linewidth=1.2, zorder=3))
    eixos.add_patch(Circle((centro[0], centro[1] - 0.2), 0.08, color=TINTA, zorder=4))
    eixos.text(centro[0], centro[1] + 0.17, nome, ha="center", va="center", fontsize=11,
               color=TINTA, fontweight="bold", zorder=4)


def ponto_na_borda(origem, destino, raio_origem, raio_destino):
    """
    Encurta um segmento para ele parar na borda dos nós.

    Parâmetros:
        origem (tuple): centro do nó de saída.
        destino (tuple): centro do nó de chegada.
        raio_origem (float): folga na saída.
        raio_destino (float): folga na chegada.
    Retorno:
        tuple: pontos de início e de fim da seta.
    Funcionamento:
        Anda a partir de cada centro na direção do outro nó.
    """
    dx, dy = destino[0] - origem[0], destino[1] - origem[1]
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    return ((origem[0] + ux * raio_origem, origem[1] + uy * raio_origem),
            (destino[0] - ux * raio_destino, destino[1] - uy * raio_destino))


def grafo_deadlock():
    """
    Desenha o grafo de alocação de recursos do deadlock da questão A5.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Coloca threads e recursos alternados em um hexágono, o que faz o ciclo
        aparecer como uma volta completa. Azul indica posse; laranja, pedido.
    """
    figura, eixos = plt.subplots(figsize=(8.6, 5.2), dpi=160)
    figura.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    eixos.set_xlim(-5, 5)
    eixos.set_ylim(-3.1, 2.95)
    eixos.axis("off")

    raio = 2.25
    posicoes = {}
    nomes = ["thread_sensor", "log", "thread_log", "ble", "thread_config", "i2c"]
    for i, nome in enumerate(nomes):
        angulo = math.radians(120 - i * 60)
        posicoes[nome] = (raio * 1.35 * math.cos(angulo), raio * math.sin(angulo))

    for nome in nomes:
        if nome.startswith("thread"):
            no_thread(eixos, posicoes[nome], nome.replace("thread_", "thread\n"))
        else:
            no_recurso(eixos, posicoes[nome], nome)

    pedidos = [("thread_sensor", "log"), ("thread_log", "ble"), ("thread_config", "i2c")]
    posses = [("log", "thread_log"), ("ble", "thread_config"), ("i2c", "thread_sensor")]
    for origem, destino in pedidos:
        a, b = ponto_na_borda(posicoes[origem], posicoes[destino], 0.66, 0.62)
        seta(eixos, a, b, cor=LARANJA, largura=2.2)
    for origem, destino in posses:
        a, b = ponto_na_borda(posicoes[origem], posicoes[destino], 0.62, 0.66)
        seta(eixos, a, b, cor=AZUL, largura=2.2)

    seta(eixos, (-3.4, -2.85), (-2.8, -2.85), cor=AZUL, largura=2.2)
    eixos.text(-2.7, -2.85, "recurso → thread: está com ela", fontsize=10.5, color=TINTA, va="center")
    seta(eixos, (0.5, -2.85), (1.1, -2.85), cor=LARANJA, largura=2.2)
    eixos.text(1.2, -2.85, "thread → recurso: está pedindo", fontsize=10.5, color=TINTA, va="center")
    figura.savefig(IMAGENS / "a5_grafo.png")
    plt.close(figura)


def main():
    """
    Gera todas as figuras.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Cada função grava um PNG em img/.
    """
    grafico_limites()
    grafico_cache()
    grafico_campanha()
    diagramas_a2()
    diagrama_estados()
    grafo_deadlock()


if __name__ == "__main__":
    main()
