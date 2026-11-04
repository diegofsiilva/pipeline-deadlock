#!/usr/bin/env python3
"""
pipeline.py

Simula o pipeline clássico de 5 estágios (IF, ID, EX, MEM, WB) no trecho do
filtro da questão A2 e gera os diagramas ciclo a ciclo em Markdown.

Também testa as 5.040 ordens possíveis das 7 instruções. Para cada uma, executa
o trecho em um interpretador com 2.000 estados aleatórios, inclusive com
ponteiros iguais, e só aceita a ordem que deixa registradores e memória iguais
aos da ordem original.

Uso: python3 pipeline.py
"""

import itertools
import random
from dataclasses import dataclass

ESTAGIOS = ("IF", "ID", "EX", "MEM", "WB")


@dataclass(frozen=True)
class Instrucao:
    """Uma instrução do trecho: texto, registrador escrito e registradores lidos."""

    texto: str
    destino: str | None
    fontes: tuple
    leitura_memoria: bool = False


TRECHO = (
    Instrucao("lw x5, 0(x10)", "x5", ("x10",), True),
    Instrucao("add x6, x6, x5", "x6", ("x6", "x5")),
    Instrucao("lw x7, 0(x11)", "x7", ("x11",), True),
    Instrucao("sub x6, x6, x7", "x6", ("x6", "x7")),
    Instrucao("sw x6, 0(x12)", None, ("x6", "x12")),
    Instrucao("addi x10, x10, 4", "x10", ("x10",)),
    Instrucao("addi x11, x11, 4", "x11", ("x11",)),
)


def dependencias_raw(ordem):
    """
    Lista as dependências de dados do tipo leitura depois de escrita.

    Parâmetros:
        ordem (sequence[Instrucao]): instruções na ordem de execução.
    Retorno:
        list[tuple]: (produtora, consumidora, registrador, distância), com
        índices a partir de 1.
    Funcionamento:
        Para cada registrador lido, procura para trás a última escrita. Isso
        ignora escritas anteriores que já foram sobrepostas.
    """
    encontradas = []
    for i, instrucao in enumerate(ordem):
        for registrador in instrucao.fontes:
            for j in range(i - 1, -1, -1):
                if ordem[j].destino == registrador:
                    encontradas.append((j + 1, i + 1, registrador, i - j))
                    break
    return encontradas


def simula(ordem, forwarding):
    """
    Calcula o ciclo em que cada instrução sai de cada estágio.

    Parâmetros:
        ordem (sequence[Instrucao]): instruções na ordem de execução.
        forwarding (bool): True liga o adiantamento de resultados.
    Retorno:
        list[dict]: para cada instrução, o último ciclo em cada estágio.
    Funcionamento:
        Sem forwarding, o ID só termina no ciclo do WB da produtora, porque o
        banco escreve na primeira metade do ciclo e lê na segunda. Com
        forwarding, o resultado da ALU vale a partir do ciclo seguinte ao EX e
        o da carga, a partir do ciclo seguinte ao MEM. A instrução seguinte só
        termina o IF quando a anterior termina o ID.
    """
    ciclos = []
    for i, instrucao in enumerate(ordem):
        fim_if = 1 if i == 0 else ciclos[i - 1]["ID"]
        fim_id = fim_if + 1
        for registrador in instrucao.fontes:
            for j in range(i - 1, -1, -1):
                if ordem[j].destino != registrador:
                    continue
                if not forwarding:
                    fim_id = max(fim_id, ciclos[j]["WB"])
                elif ordem[j].leitura_memoria:
                    fim_id = max(fim_id, ciclos[j]["MEM"])
                else:
                    fim_id = max(fim_id, ciclos[j]["EX"])
                break
        ciclos.append({
            "IF": fim_if,
            "ID": fim_id,
            "EX": fim_id + 1,
            "MEM": fim_id + 2,
            "WB": fim_id + 3,
        })
    return ciclos


def total_ciclos(ciclos):
    """
    Conta os ciclos do primeiro IF ao último WB.

    Parâmetros:
        ciclos (list[dict]): resultado de simula().
    Retorno:
        int: o ciclo do último WB, já que o primeiro IF acontece no ciclo 1.
    Funcionamento:
        O pipeline é em ordem, então o último WB é o da última instrução.
    """
    return ciclos[-1]["WB"]


def bolhas(ciclos):
    """
    Conta os ciclos perdidos em relação ao pipeline ideal.

    Parâmetros:
        ciclos (list[dict]): resultado de simula().
    Retorno:
        int: total de ciclos menos o ideal, que é instruções + 4.
    Funcionamento:
        Sem paradas, n instruções levam n + 4 ciclos em 5 estágios.
    """
    return total_ciclos(ciclos) - (len(ciclos) + 4)


def diagrama(ordem, ciclos):
    """
    Monta o diagrama ciclo a ciclo como tabela Markdown.

    Parâmetros:
        ordem (sequence[Instrucao]): instruções na ordem de execução.
        ciclos (list[dict]): resultado de simula().
    Retorno:
        str: tabela Markdown, com as instruções numeradas de I1 a I7 na ordem
        original; IF* e ID* são ciclos parados.
    Funcionamento:
        Uma instrução só entra em IF quando a anterior sai de IF. Depois,
        preenche cada célula do início ao fim de cada estágio. Quando um
        estágio dura mais de um ciclo, os ciclos extras recebem asterisco.
    """
    total = total_ciclos(ciclos)
    cabecalho = "| | " + " | ".join(str(c) for c in range(1, total + 1)) + " |"
    separador = "|---|" + "---|" * total
    linhas = [cabecalho, separador]
    for i, instrucao in enumerate(ordem):
        celulas = [""] * (total + 1)
        inicio = 1 if i == 0 else ciclos[i - 1]["IF"] + 1
        for estagio in ESTAGIOS:
            fim = ciclos[i][estagio]
            for ciclo in range(inicio, fim + 1):
                celulas[ciclo] = estagio if ciclo == fim else estagio + "\\*"
            inicio = fim + 1
        rotulo = f"I{TRECHO.index(instrucao) + 1}"
        linhas.append(f"| {rotulo} | " + " | ".join(celulas[1:]) + " |")
    return "\n".join(linhas)


def executa(ordem, estado):
    """
    Executa o trecho em um interpretador mínimo de RISC-V.

    Parâmetros:
        ordem (sequence[Instrucao]): instruções na ordem de execução.
        estado (tuple): (registradores, memória); não são alterados.
    Retorno:
        tuple: registradores e memória finais.
    Funcionamento:
        Interpreta só as cinco operações que aparecem no trecho, usando o
        texto da instrução para extrair os operandos.
    """
    registradores, memoria = dict(estado[0]), dict(estado[1])
    for instrucao in ordem:
        operacao, resto = instrucao.texto.split(" ", 1)
        operandos = resto.split(", ")
        if operacao in ("lw", "sw"):
            base = operandos[1].split("(")[1].rstrip(")")
            if operacao == "lw":
                registradores[operandos[0]] = memoria[registradores[base]]
            else:
                memoria[registradores[base]] = registradores[operandos[0]]
        elif operacao == "add":
            registradores[operandos[0]] = registradores[operandos[1]] + registradores[operandos[2]]
        elif operacao == "sub":
            registradores[operandos[0]] = registradores[operandos[1]] - registradores[operandos[2]]
        elif operacao == "addi":
            registradores[operandos[0]] = registradores[operandos[1]] + int(operandos[2])
    return registradores, memoria


def estados_de_teste(quantidade, semente=2026):
    """
    Sorteia estados iniciais para comparar as ordens.

    Parâmetros:
        quantidade (int): quantos estados gerar.
        semente (int): semente do gerador, para o resultado ser reproduzível.
    Retorno:
        list[tuple]: pares (registradores, memória).
    Funcionamento:
        Os ponteiros vêm de um conjunto pequeno de endereços, para que x10, x11
        e x12 às vezes apontem para o mesmo lugar. Assim uma ordem que troca
        uma leitura com a escrita é reprovada.
    """
    gerador = random.Random(semente)
    enderecos = [100, 104, 108]
    estados = []
    for _ in range(quantidade):
        registradores = {f"x{r}": gerador.randint(-999, 999) for r in (5, 6, 7)}
        for ponteiro in ("x10", "x11", "x12"):
            registradores[ponteiro] = gerador.choice(enderecos)
        memoria = {e: gerador.randint(-999, 999) for e in range(100, 116, 4)}
        estados.append((registradores, memoria))
    return estados


def ordens_equivalentes(ordem_original, estados):
    """
    Encontra as permutações que preservam o resultado.

    Parâmetros:
        ordem_original (sequence[Instrucao]): a ordem do enunciado.
        estados (list[tuple]): estados iniciais de estados_de_teste().
    Retorno:
        list[tuple]: permutações com o mesmo estado final em todos os testes.
    Funcionamento:
        Compara os estados finais por força bruta. Com 7 instruções são 5.040
        permutações, então não é preciso nenhuma poda.
    """
    finais = [executa(ordem_original, estado) for estado in estados]
    return [
        ordem for ordem in itertools.permutations(ordem_original)
        if all(executa(ordem, e) == f for e, f in zip(estados, finais))
    ]


def deslocamento(ordem):
    """
    Mede o quanto uma ordem se afasta da ordem original.

    Parâmetros:
        ordem (tuple[Instrucao]): permutação do trecho.
    Retorno:
        int: soma de quantas posições cada instrução andou.
    Funcionamento:
        Serve para escolher, entre as ordens sem bolhas, a que muda menos.
    """
    return sum(abs(ordem.index(ins) - TRECHO.index(ins)) for ins in TRECHO)


def main():
    """
    Imprime as dependências, os três diagramas e o resultado da busca.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        A saída é Markdown, pronta para ser colada no ponderada-tato.md.
    """
    print("## Dependências RAW\n")
    for produtora, consumidora, registrador, distancia in dependencias_raw(TRECHO):
        print(f"- I{consumidora} depende de I{produtora} por {registrador} (distância {distancia})")

    for titulo, forwarding in (("Sem forwarding", False), ("Com forwarding", True)):
        ciclos = simula(TRECHO, forwarding)
        print(f"\n## {titulo}: {total_ciclos(ciclos)} ciclos, {bolhas(ciclos)} bolhas\n")
        print(diagrama(TRECHO, ciclos))

    validas = ordens_equivalentes(TRECHO, estados_de_teste(2000))
    sem_bolhas = [o for o in validas if bolhas(simula(o, True)) == 0]
    print(f"\n## Busca: {len(validas)} ordens válidas de 5040, {len(sem_bolhas)} sem bolhas\n")

    distribuicao = {}
    for ordem in validas:
        b = bolhas(simula(ordem, True))
        distribuicao[b] = distribuicao.get(b, 0) + 1
    print("Ordens válidas por número de bolhas:", dict(sorted(distribuicao.items())))

    melhor = min(sem_bolhas, key=deslocamento)
    ciclos = simula(melhor, True)
    print(f"\n## Reordenado: {total_ciclos(ciclos)} ciclos, {bolhas(ciclos)} bolhas\n")
    print(diagrama(melhor, ciclos))


if __name__ == "__main__":
    main()
