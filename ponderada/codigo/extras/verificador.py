#!/usr/bin/env python3
"""
verificador.py

Prova por exploração exaustiva o que um teste só consegue sugerir. Cada thread
vira a sua sequência de operações DOWN (P) e UP (V), repetida em laço, e o
programa percorre todos os estados que qualquer intercalação consegue alcançar.
Deadlock é um estado em que nenhuma thread consegue dar o próximo passo.

Se existe deadlock, a busca em largura devolve o caminho mais curto até ele.
Se não existe, nenhuma intercalação leva a um: isso vale para toda execução
possível do modelo, não só para as que rodaram.

O modelo olha apenas para as operações de semáforo, porque as outras linhas não
bloqueiam. Mantê-lo pequeno é o que torna a busca exaustiva possível.

Uso: python3 verificador.py
"""

from collections import deque
from functools import lru_cache


def proximos(estado, programas, nomes, em_laco):
    """
    Lista os passos possíveis a partir de um estado.

    Parâmetros:
        estado (tuple): (posição de cada thread, valor de cada semáforo).
        programas (list[list]): uma lista de operações (op, semáforo) por thread.
        nomes (list[str]): nomes dos semáforos, na ordem dos valores.
        em_laco (bool): True faz cada thread recomeçar ao chegar ao fim.
    Retorno:
        list[tuple]: pares (descrição do passo, novo estado).
    Funcionamento:
        DOWN só é possível com o semáforo acima de zero. UP é sempre possível.
    """
    posicoes, valores = estado
    saidas = []
    for t, programa in enumerate(programas):
        if posicoes[t] == len(programa):
            continue
        operacao, semaforo = programa[posicoes[t]]
        i = nomes.index(semaforo)
        if operacao == "DOWN" and valores[i] == 0:
            continue
        novos_valores = list(valores)
        novos_valores[i] += 1 if operacao == "UP" else -1
        novas_posicoes = list(posicoes)
        novas_posicoes[t] += 1
        if em_laco:
            novas_posicoes[t] %= len(programa)
        saidas.append(((t, operacao, semaforo), (tuple(novas_posicoes), tuple(novos_valores))))
    return saidas


def explora(programas, iniciais):
    """
    Percorre todos os estados alcançáveis com as threads em laço.

    Parâmetros:
        programas (list[list]): operações de cada thread.
        iniciais (dict): valor inicial de cada semáforo.
    Retorno:
        tuple: (número de estados, lista de deadlocks, dicionário de pais).
    Funcionamento:
        Busca em largura. Guarda o pai de cada estado para reconstruir o
        caminho, que por ser em largura é o mais curto possível.
    """
    nomes = list(iniciais)
    inicio = (tuple(0 for _ in programas), tuple(iniciais.values()))
    pais = {inicio: None}
    fila = deque([inicio])
    deadlocks = []
    while fila:
        estado = fila.popleft()
        saidas = proximos(estado, programas, nomes, True)
        if not saidas:
            deadlocks.append(estado)
        for passo, novo in saidas:
            if novo not in pais:
                pais[novo] = (estado, passo)
                fila.append(novo)
    return len(pais), deadlocks, pais


def caminho(estado, pais):
    """
    Reconstrói os passos do estado inicial até um estado.

    Parâmetros:
        estado (tuple): estado de destino.
        pais (dict): resultado de explora().
    Retorno:
        list[tuple]: passos na ordem de execução.
    Funcionamento:
        Sobe pelos pais até o início e inverte a lista.
    """
    passos = []
    while pais[estado] is not None:
        estado, passo = pais[estado]
        passos.append(passo)
    return passos[::-1]


def conta_execucoes(programas, iniciais):
    """
    Conta as execuções completas de uma rodada de cada thread.

    Parâmetros:
        programas (list[list]): operações de cada thread.
        iniciais (dict): valor inicial de cada semáforo.
    Retorno:
        tuple: (execuções que terminam, execuções que travam).
    Funcionamento:
        Sem laço, os estados formam um grafo sem ciclos, então a contagem é uma
        recursão com memória: cada estado soma as execuções dos seus sucessores.
    """
    nomes = list(iniciais)

    @lru_cache(maxsize=None)
    def conta(estado):
        """
        Conta as execuções que partem de um estado.

        Parâmetros:
            estado (tuple): posição das threads e valor dos semáforos.
        Retorno:
            tuple: (execuções que terminam, execuções que travam).
        Funcionamento:
            Sem saídas, a execução acabou: terminou se todas as threads
            chegaram ao fim e, caso contrário, travou.
        """
        saidas = proximos(estado, programas, nomes, False)
        if not saidas:
            terminou = all(p == len(q) for p, q in zip(estado[0], programas))
            return (1, 0) if terminou else (0, 1)
        parciais = [conta(novo) for _, novo in saidas]
        return sum(p[0] for p in parciais), sum(p[1] for p in parciais)

    return conta((tuple(0 for _ in programas), tuple(iniciais.values())))


def down(semaforo):
    """
    Escreve a operação DOWN (P) de um semáforo.

    Parâmetros:
        semaforo (str): nome do semáforo.
    Retorno:
        tuple: a operação, no formato usado pelos programas do modelo.
    Funcionamento:
        É só um atalho para os modelos ficarem parecidos com o código.
    """
    return ("DOWN", semaforo)


def up(semaforo):
    """
    Escreve a operação UP (V) de um semáforo.

    Parâmetros:
        semaforo (str): nome do semáforo.
    Retorno:
        tuple: a operação, no formato usado pelos programas do modelo.
    Funcionamento:
        É só um atalho para os modelos ficarem parecidos com o código.
    """
    return ("UP", semaforo)


CONSUMIDOR = [down("cheio"), down("mutex"), up("mutex"), up("vazio")]
PRODUTOR_V2 = [down("vazio"), down("mutex"), up("mutex"), up("cheio")]
PRODUTOR_V3 = [down("mutex"), down("vazio"), up("mutex"), up("cheio")]

A5_RECURSOS = {"i2c": 1, "log": 1, "ble": 1}
A5_ORIGINAL = [
    [down("i2c"), down("log"), up("log"), up("i2c")],
    [down("log"), down("ble"), up("ble"), up("log")],
    [down("ble"), down("i2c"), up("i2c"), up("ble")],
]
A5_ORDEM_GLOBAL = [
    [down("i2c"), down("log"), up("log"), up("i2c")],
    [down("log"), down("ble"), up("ble"), up("log")],
    [down("i2c"), down("ble"), up("ble"), up("i2c")],
]
A5_UM_RECURSO_POR_VEZ = [
    [down("i2c"), up("i2c"), down("log"), up("log")],
    [down("log"), up("log"), down("ble"), up("ble")],
    [down("ble"), up("ble"), down("i2c"), up("i2c")],
]
NOMES_A4 = ("produtor", "consumidor")
NOMES_A5 = ("sensor", "log", "config")


def relata(titulo, programas, iniciais, nomes_threads, conta_rodada=False):
    """
    Explora um modelo e imprime o resultado.

    Parâmetros:
        titulo (str): nome do modelo.
        programas (list[list]): operações de cada thread.
        iniciais (dict): valor inicial de cada semáforo.
        nomes_threads (tuple[str]): nome de cada thread.
        conta_rodada (bool): True conta as execuções de uma rodada de cada
            thread. Só faz sentido na A5: na A4, uma rodada não enche o buffer.
    Retorno:
        None.
    Funcionamento:
        Imprime quantos estados existem, quantos são deadlock e o caminho mais
        curto até o deadlock.
    """
    total, deadlocks, pais = explora(programas, iniciais)
    print(f"{titulo}")
    print(f"  estados alcançáveis : {total}")
    print(f"  estados de deadlock : {len(deadlocks)}")
    if conta_rodada:
        terminam, travam = conta_execucoes(programas, iniciais)
        print(f"  uma rodada de cada  : {terminam + travam} execuções, {travam} travam")
    if deadlocks:
        passos = caminho(min(deadlocks, key=lambda e: len(caminho(e, pais))), pais)
        print(f"  caminho mais curto  : {len(passos)} passos")
        for t, operacao, semaforo in passos:
            print(f"    {nomes_threads[t]}: {operacao}({semaforo})")
    print()


def main():
    """
    Verifica os modelos das questões A4 e A5.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        Depois dos modelos com N = 3, repete as versões 2 e 3 com outros
        tamanhos para testar se aumentar o buffer resolve o deadlock.
    """
    iniciais = {"vazio": 3, "cheio": 0, "mutex": 1}
    relata("A4, versão 2, N = 3", [PRODUTOR_V2, CONSUMIDOR], iniciais, NOMES_A4)
    relata("A4, versão 3, N = 3", [PRODUTOR_V3, CONSUMIDOR], iniciais, NOMES_A4)
    relata("A5, código original", A5_ORIGINAL, A5_RECURSOS, NOMES_A5, True)
    relata("A5, ordem global", A5_ORDEM_GLOBAL, A5_RECURSOS, NOMES_A5, True)
    relata("A5, um recurso por vez", A5_UM_RECURSO_POR_VEZ, A5_RECURSOS, NOMES_A5, True)

    print("Aumentar o buffer resolve? (estados de deadlock e passos até ele)")
    for n in (1, 2, 3, 5, 8, 16, 64):
        iniciais = {"vazio": n, "cheio": 0, "mutex": 1}
        _, deadlocks_v2, _ = explora([PRODUTOR_V2, CONSUMIDOR], iniciais)
        _, deadlocks_v3, pais = explora([PRODUTOR_V3, CONSUMIDOR], iniciais)
        passos = min(len(caminho(e, pais)) for e in deadlocks_v3)
        print(f"  N = {n:2d}: versão 2 = {len(deadlocks_v2)}, "
              f"versão 3 = {len(deadlocks_v3)} ({passos} passos)")


if __name__ == "__main__":
    main()
