/*
 * comum.h
 *
 * Partes comuns às três versões da questão A4: parâmetros do experimento,
 * contabilidade das amostras, vigia de travamento e relatório final.
 *
 * A sincronização fica só em versao1.c, versao2.c e versao3.c. Assim, a única
 * diferença entre as versões é a que o enunciado pede. Os contadores usados
 * para medir são atômicos, para que a medição não crie corridas próprias.
 */

#ifndef COMUM_H
#define COMUM_H

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#ifndef N
#define N 3 /* tamanho do buffer: 3 + (D2 mod 5), com D2 = 0 */
#endif

#define TOTAL_AMOSTRAS 20000
#define PRAZO_TRAVAMENTO_S 1.0
#define INTERVALO_VIGIA_US 1000

static int buffer[N];
static int entrada; /* próxima posição que o produtor escreve */
static int saida;   /* próxima posição que o consumidor lê */

static atomic_int produzidas;
static atomic_int consumidas;
static int vezes_recebida[TOTAL_AMOSTRAS];

/*
 * agora: lê o relógio monotônico.
 *
 * Parâmetros: nenhum.
 * Retorno: tempo em segundos, com origem arbitrária.
 * Funcionamento: o relógio monotônico não sofre ajustes de horário, então a
 * diferença entre duas leituras é sempre uma duração válida.
 */
static double agora(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

/*
 * registra_producao: conta uma amostra colocada no buffer.
 *
 * Parâmetros: nenhum.
 * Retorno: nenhum.
 * Funcionamento: incremento atômico, chamado pelo produtor a cada amostra.
 */
static void registra_producao(void)
{
    atomic_fetch_add(&produzidas, 1);
}

/*
 * registra_consumo: anota que o consumidor recebeu uma amostra.
 *
 * Parâmetros:
 *   amostra: número da amostra lida do buffer.
 * Retorno: nenhum.
 * Funcionamento: só o consumidor escreve em vezes_recebida. O incremento
 * atômico vem por último, para o vigia ver a anotação quando ler o contador.
 */
static void registra_consumo(int amostra)
{
    vezes_recebida[amostra]++;
    atomic_fetch_add(&consumidas, 1);
}

/*
 * vigia: espera o consumidor terminar ou detecta o travamento.
 *
 * Parâmetros: nenhum.
 * Retorno: true se o consumidor passou PRAZO_TRAVAMENTO_S sem receber nada;
 * false se ele recebeu TOTAL_AMOSTRAS.
 * Funcionamento: roda na thread principal e olha só para o progresso do
 * consumidor. Por isso pega qualquer causa de travamento, com o consumidor
 * girando em espera ocupada ou dormindo em um semáforo.
 */
static bool vigia(void)
{
    int ultimo = -1;
    double ultimo_progresso = agora();

    for (;;) {
        int atual = atomic_load(&consumidas);
        if (atual == TOTAL_AMOSTRAS)
            return false;
        if (atual != ultimo) {
            ultimo = atual;
            ultimo_progresso = agora();
        } else if (agora() - ultimo_progresso >= PRAZO_TRAVAMENTO_S) {
            return true;
        }
        usleep(INTERVALO_VIGIA_US);
    }
}

/*
 * relatorio: imprime o resultado de uma execução.
 *
 * Parâmetros:
 *   titulo: nome da versão.
 *   travou: resultado de vigia().
 *   segundos: duração da execução.
 * Retorno: nenhum.
 * Funcionamento: perdida é a amostra de 0 a TOTAL_AMOSTRAS - 1 que o
 * consumidor nunca viu; duplicada é cada recebimento além do primeiro. A linha
 * de produzidas mostra quantas das perdidas nem chegaram a ser geradas.
 */
static void relatorio(const char *titulo, bool travou, double segundos)
{
    int distintas = 0;
    int recebidas = atomic_load(&consumidas);

    for (int i = 0; i < TOTAL_AMOSTRAS; i++)
        if (vezes_recebida[i] > 0)
            distintas++;

    printf("%s (N = %d, %d amostras)\n", titulo, N, TOTAL_AMOSTRAS);
    printf("  produzidas : %d\n", atomic_load(&produzidas));
    printf("  consumidas : %d\n", recebidas);
    printf("  perdidas   : %d\n", TOTAL_AMOSTRAS - distintas);
    printf("  duplicadas : %d\n", recebidas - distintas);
    printf("  travou     : %s\n", travou ? "sim" : "não");
    printf("  tempo      : %.3f s\n", segundos);
}

#endif
