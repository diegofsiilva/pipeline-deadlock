#!/usr/bin/env python3
"""
contas.py

Recalcula os parâmetros individuais e as contas da questão A1 a partir do nome
completo, para que nenhum número da Parte A dependa de conta feita à mão.
Além das respostas pedidas, testa até onde cada plataforma aguenta: taxa de
falta máxima, número máximo de instruções e tamanho máximo do buffer.

Uso: python3 contas.py "Diego Figueiredo Silva"
"""

import math
import sys

PRAZO_MS = 5.0
ATRASO_SO_MS = 3.0
ACESSOS_POR_INSTRUCAO = 1.3
PENALIDADE_CICLOS = 120
CLOCK_H_HZ = 48e6
CLOCK_V_HZ = 1.2e9
CPI_H = 1.5
FRACAO_FILTRO = 0.6
GANHO_DSP = 5


def parametros(nome):
    """
    Calcula os parâmetros individuais definidos no enunciado.

    Parâmetros:
        nome (str): nome completo, como na lista de chamada.
    Retorno:
        dict: D1, D2, IC (instruções por amostra), m (taxa de falta) e N.
    Funcionamento:
        Conta só letras, ignorando espaços. Acentos e partículas contam.
    """
    palavras = nome.split()
    letras = [sum(c.isalpha() for c in p) for p in palavras]
    d1 = letras[0] % 10
    d2 = sum(letras) % 10
    return {
        "D1": d1,
        "D2": d2,
        "total_letras": sum(letras),
        "IC": 100_000 + 20_000 * d2,
        "m": 0.03 + 0.005 * d1,
        "N": 3 + d2 % 5,
    }


def tempo_ms(ic, cpi, clock_hz):
    """
    Aplica a equação clássica de desempenho.

    Parâmetros:
        ic (float): instruções por amostra.
        cpi (float): ciclos por instrução.
        clock_hz (float): frequência do clock em hertz.
    Retorno:
        float: tempo por amostra em milissegundos.
    Funcionamento:
        T = IC × CPI ÷ f.
    """
    return ic * cpi / clock_hz * 1e3


def cpi_v(m):
    """
    Calcula o CPI efetivo da Plataforma V.

    Parâmetros:
        m (float): taxa de falta na L1, de 0 a 1.
    Retorno:
        float: 1,0 + (acessos por instrução × m × penalidade).
    Funcionamento:
        Fórmula dada pelo enunciado na questão A1.2.
    """
    return 1.0 + ACESSOS_POR_INSTRUCAO * m * PENALIDADE_CICLOS


def amdahl(fracao, ganho):
    """
    Calcula o speedup global pela Lei de Amdahl.

    Parâmetros:
        fracao (float): parte do tempo que é acelerada, de 0 a 1.
        ganho (float): quantas vezes essa parte fica mais rápida.
    Retorno:
        float: speedup global.
    Funcionamento:
        S = 1 ÷ ((1 − fração) + fração ÷ ganho).
    """
    return 1 / ((1 - fracao) + fracao / ganho)


def imprime(rotulo, valor):
    """
    Imprime uma linha alinhada do relatório.

    Parâmetros:
        rotulo (str): descrição do valor.
        valor (str): valor já formatado.
    Retorno:
        None.
    Funcionamento:
        Mantém a coluna de valores alinhada para facilitar a conferência.
    """
    print(f"  {rotulo:<46} {valor}")


def main():
    """
    Lê o nome da linha de comando e imprime todas as contas.

    Parâmetros:
        Nenhum: o nome vem de sys.argv.
    Retorno:
        None.
    Funcionamento:
        Calcula as respostas de A1.1 a A1.3 e, depois, os limites de cada
        plataforma, que a Parte B usa para defender a decisão.
    """
    nome = sys.argv[1] if len(sys.argv) > 1 else "Diego Figueiredo Silva"
    p = parametros(nome)
    ic, m, n = p["IC"], p["m"], p["N"]

    print(f"{nome}: {p['total_letras']} letras")
    imprime("D1 / D2 / N", f"{p['D1']} / {p['D2']} / {n}")
    imprime("IC", f"{ic}")
    imprime("m", f"{m:.3%}")

    print("\nA1.1 Plataforma H")
    t_h = tempo_ms(ic, CPI_H, CLOCK_H_HZ)
    imprime("tempo por amostra", f"{t_h:.3f} ms")
    imprime("margem", f"{PRAZO_MS - t_h:.3f} ms")

    print("\nA1.2 Plataforma V")
    amat = 1 + m * PENALIDADE_CICLOS
    cpi = cpi_v(m)
    t_v = tempo_ms(ic, cpi, CLOCK_V_HZ)
    imprime("AMAT", f"{amat:.2f} ciclos")
    imprime("CPI efetivo", f"{cpi:.2f}")
    imprime("tempo por amostra", f"{t_v:.4f} ms")
    imprime("pior caso", f"{t_v + ATRASO_SO_MS:.4f} ms")
    imprime("margem", f"{PRAZO_MS - t_v - ATRASO_SO_MS:.4f} ms")

    print("\nA1.3 Amdahl")
    s = amdahl(FRACAO_FILTRO, GANHO_DSP)
    t_dsp = t_h / s
    imprime("speedup", f"{s:.4f}")
    imprime("tempo com DSP", f"{t_dsp:.3f} ms")

    print("\nLimites: até onde cada plataforma aguenta")
    cpi_sem_cache = cpi_v(1.0)
    t_sem_cache = tempo_ms(ic, cpi_sem_cache, CLOCK_V_HZ)
    imprime("V sem cache (m = 100%): CPI", f"{cpi_sem_cache:.0f}")
    imprime("V sem cache: tempo por amostra", f"{t_sem_cache:.2f} ms")
    cpi_max = (PRAZO_MS - ATRASO_SO_MS) * 1e-3 * CLOCK_V_HZ / ic
    m_max = (cpi_max - 1) / (ACESSOS_POR_INSTRUCAO * PENALIDADE_CICLOS)
    imprime("V: CPI máximo no pior caso", f"{cpi_max:.2f}")
    imprime("V: m máximo no pior caso", f"{m_max:.2%} ({m_max / m:.2f} × m)")
    ic_h = PRAZO_MS * 1e-3 * CLOCK_H_HZ / CPI_H
    imprime("H: IC máximo", f"{ic_h:.0f} (+{ic_h / ic - 1:.0%})")
    imprime("H + DSP: IC máximo", f"{ic_h * s:.0f} (+{ic_h * s / ic - 1:.0%})")
    ic_v = cpi_max * ic / cpi
    imprime("V: IC máximo no pior caso", f"{ic_v:.0f} (+{ic_v / ic - 1:.0%})")

    print(f"\nBuffer cheio: a última amostra espera N × S (N = {n})")
    casos = [
        ("H", t_h, 0.0),
        ("H + DSP", t_dsp, 0.0),
        ("V", t_v, ATRASO_SO_MS),
    ]
    for rotulo, servico, atraso in casos:
        pior = n * servico + atraso
        n_max = math.floor((PRAZO_MS - atraso) / servico)
        veredito = "atende" if pior <= PRAZO_MS else "NÃO atende"
        imprime(rotulo, f"{pior:.3f} ms, {veredito}; N máximo = {n_max}")


if __name__ == "__main__":
    main()
