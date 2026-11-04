#!/usr/bin/env python3
"""
print_terminal.py

Gera os prints de img/ a partir das saídas reais guardadas em resultados/.
Cada imagem mostra o comando e o texto exato que o terminal imprimiu. Os filtros
de grep e sed aparecem no próprio comando do print.

Uso, a partir de ponderada/codigo: python3 extras/print_terminal.py
"""

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ESCALA = 2
TAMANHO_FONTE = 14
ALTURA_LINHA = 20
MARGEM = 18
ALTURA_BARRA = 30
LARGURA_MINIMA_COLUNAS = 62
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

COR_FUNDO = "#1e1e1e"
COR_BARRA = "#323232"
COR_TEXTO = "#e4e4e4"
COR_USUARIO = "#8ae234"
COR_CAMINHO = "#729fcf"
BOTOES = ("#ff5f56", "#ffbd2e", "#27c93f")

USUARIO = "diegofsiilva@Diego-Latitude-3450"
PASTA = ".../ponderada/codigo"

CODIGO = Path(__file__).resolve().parent.parent
RESULTADOS = CODIGO / "resultados"
IMAGENS = CODIGO.parent / "img"


def desenha_print(comando, saida, destino):
    """
    Desenha uma janela de terminal com um comando e a sua saída.

    Parâmetros:
        comando (str): comando mostrado depois do prompt; pode ter várias linhas.
        saida (str): texto impresso pelo comando.
        destino (Path): arquivo PNG a gravar.
    Retorno:
        None.
    Funcionamento:
        Calcula o tamanho da janela pela maior linha e desenha o texto em dobro
        da resolução, para ficar nítido. A saída não recebe cor, porque o
        programa também não imprime cor.
    """
    fonte = ImageFont.truetype(FONTE, TAMANHO_FONTE * ESCALA)
    largura_char = fonte.getlength("M")
    prompt = f"{USUARIO}:{PASTA}$ "
    linhas_comando = comando.split("\n")
    linhas_saida = saida.rstrip("\n").split("\n")

    colunas = max(
        LARGURA_MINIMA_COLUNAS,
        len(prompt) + len(linhas_comando[0]),
        *(len(linha) for linha in linhas_comando[1:]),
        *(len(linha) for linha in linhas_saida),
    )
    total_linhas = len(linhas_comando) + len(linhas_saida)
    largura = int(colunas * largura_char + 2 * MARGEM * ESCALA)
    altura = (ALTURA_BARRA + 2 * MARGEM + total_linhas * ALTURA_LINHA) * ESCALA

    imagem = Image.new("RGB", (largura, altura), COR_FUNDO)
    caneta = ImageDraw.Draw(imagem)
    caneta.rectangle((0, 0, largura, ALTURA_BARRA * ESCALA), fill=COR_BARRA)
    for i, cor in enumerate(BOTOES):
        centro_x = (MARGEM + i * 20) * ESCALA
        centro_y = ALTURA_BARRA // 2 * ESCALA
        raio = 6 * ESCALA
        caneta.ellipse((centro_x - raio, centro_y - raio, centro_x + raio, centro_y + raio), fill=cor)

    x = MARGEM * ESCALA
    y = (ALTURA_BARRA + MARGEM) * ESCALA
    caneta.text((x, y), USUARIO, font=fonte, fill=COR_USUARIO)
    x += fonte.getlength(USUARIO)
    caneta.text((x, y), ":", font=fonte, fill=COR_TEXTO)
    x += fonte.getlength(":")
    caneta.text((x, y), PASTA, font=fonte, fill=COR_CAMINHO)
    x += fonte.getlength(PASTA)
    caneta.text((x, y), "$ " + linhas_comando[0], font=fonte, fill=COR_TEXTO)

    y += ALTURA_LINHA * ESCALA
    for linha in linhas_comando[1:] + linhas_saida:
        caneta.text((MARGEM * ESCALA, y), linha, font=fonte, fill=COR_TEXTO)
        y += ALTURA_LINHA * ESCALA

    imagem.save(destino)


def execucao(versao, rodada=1):
    """
    Extrai uma execução oficial de resultados/execucoes.txt.

    Parâmetros:
        versao (int): número da versão.
        rodada (int): número da execução, de 1 a 3.
    Retorno:
        str: o texto que o terminal imprimiu naquela execução.
    Funcionamento:
        Cada execução começa com uma linha de separação gravada pelo script
        medir_tudo.sh.
    """
    texto = (RESULTADOS / "execucoes.txt").read_text(encoding="utf-8")
    marca = f"--- versão {versao}, execução {rodada}\n"
    return texto.split(marca)[1].split("--- versão")[0]


def filtra_tsan():
    """
    Filtra o relatório do ThreadSanitizer da versão 1.

    Parâmetros:
        Nenhum.
    Retorno:
        str: linhas com as corridas, sem o trecho final de endereços.
    Funcionamento:
        Aplica o mesmo filtro que aparece no comando do print.
    """
    texto = (RESULTADOS / "tsan_v1.txt").read_text(encoding="utf-8")
    padrao = re.compile(r"WARNING|of size 4 at|#0 (consumidor|produtor)|Location")
    linhas = [re.sub(r" \(versao1_tsan.*", "", l) for l in texto.splitlines() if padrao.search(l)]
    return "\n".join(linhas)


def filtra_gdb():
    """
    Filtra as pilhas das threads no gdb da versão 3.

    Parâmetros:
        Nenhum.
    Retorno:
        str: para cada thread presa, o semáforo e a linha do código.
    Funcionamento:
        Aplica o mesmo filtro que aparece no comando do print.
    """
    texto = (RESULTADOS / "gdb_v3.txt").read_text(encoding="utf-8")
    padrao = re.compile(r"^Thread [23] |^#7 |^#8 ")
    return "\n".join(l for l in texto.splitlines() if padrao.search(l))


def main():
    """
    Gera todos os prints do trabalho.

    Parâmetros:
        Nenhum.
    Retorno:
        None.
    Funcionamento:
        O print de cada versão é a primeira das execuções oficiais.
    """
    desenha_print(
        "lscpu | grep -E '^Nome do modelo|^cache de'; echo; lscpu -C",
        (RESULTADOS / "lscpu.txt").read_text(encoding="utf-8"),
        IMAGENS / "a1_lscpu.png",
    )
    for versao in (1, 2, 3):
        desenha_print(f"make v{versao}", execucao(versao), IMAGENS / f"a4_v{versao}.png")
    desenha_print(
        "make tsan1 2>&1 \\\n"
        "  | grep -E 'WARNING|of size 4 at|#0 (consumidor|produtor)|Location' \\\n"
        "  | sed 's/ (versao1_tsan.*//'",
        filtra_tsan(),
        IMAGENS / "a4_tsan.png",
    )
    desenha_print(
        "gdb -q -batch -ex 'break relatorio' -ex run \\\n"
        "  -ex 'thread apply all bt' ./versao3 | grep -E '^Thread [23] |^#7 |^#8 '",
        filtra_gdb(),
        IMAGENS / "a4_gdb.png",
    )


if __name__ == "__main__":
    main()
