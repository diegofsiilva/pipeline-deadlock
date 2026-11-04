/*
 * jitter.c
 *
 * Testa a premissa da Plataforma V de que o Linux atrasa a tarefa em até 3 ms.
 * Simula a thread do sensor: acorda a cada 10 ms, trabalha 0,8 ms e dorme. Mede
 * o atraso de cada despertar e usa as contas do PCB mostradas na aula: nvcsw
 * (saiu por conta própria) e nivcsw (foi tirada pelo sistema).
 *
 * Uso: jitter <segundos>
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <time.h>

#define PERIODO_NS 10000000L
#define TRABALHO_S 0.0008

/*
 * segundos: converte um timespec para segundos.
 *
 * Parâmetros:
 *   t: instante.
 * Retorno: o mesmo instante, em segundos.
 * Funcionamento: soma as duas partes do timespec.
 */
static double segundos(const struct timespec *t)
{
    return t->tv_sec + t->tv_nsec / 1e9;
}

/*
 * agora: lê o relógio monotônico.
 *
 * Parâmetros: nenhum.
 * Retorno: tempo em segundos, com origem arbitrária.
 * Funcionamento: é o mesmo relógio usado para agendar o despertar.
 */
static double agora(void)
{
    struct timespec t;

    clock_gettime(CLOCK_MONOTONIC, &t);
    return segundos(&t);
}

/*
 * compara: critério de ordenação para o qsort.
 *
 * Parâmetros:
 *   a, b: ponteiros para double.
 * Retorno: negativo, zero ou positivo, como o qsort espera.
 * Funcionamento: compara os dois valores.
 */
static int compara(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;

    return (x > y) - (x < y);
}

/*
 * main: executa a tarefa periódica e imprime as medidas.
 *
 * Parâmetros:
 *   argc, argv: duração do teste em segundos.
 * Retorno: 0, ou 1 se faltar o argumento.
 * Funcionamento: o despertar usa tempo absoluto, então um atraso não desloca
 * os períodos seguintes. A fração em espera vem do tempo de CPU da thread.
 */
int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "uso: %s <segundos>\n", argv[0]);
        return 1;
    }

    int n = atoi(argv[1]) * 100;
    double *atrasos = malloc(n * sizeof *atrasos);
    struct timespec proximo;
    double inicio = agora();

    clock_gettime(CLOCK_MONOTONIC, &proximo);
    for (int i = 0; i < n; i++) {
        proximo.tv_nsec += PERIODO_NS;
        if (proximo.tv_nsec >= 1000000000L) {
            proximo.tv_nsec -= 1000000000L;
            proximo.tv_sec++;
        }
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &proximo, NULL);
        atrasos[i] = agora() - segundos(&proximo);

        double fim = agora() + TRABALHO_S;
        while (agora() < fim)
            ;
    }
    double total = agora() - inicio;

    struct rusage uso;
    getrusage(RUSAGE_THREAD, &uso);
    double cpu = uso.ru_utime.tv_sec + uso.ru_utime.tv_usec / 1e6 +
                 uso.ru_stime.tv_sec + uso.ru_stime.tv_usec / 1e6;

    int acima_margem = 0, acima_3ms = 0;
    for (int i = 0; i < n; i++) {
        acima_margem += atrasos[i] > 0.0012;
        acima_3ms += atrasos[i] > 0.003;
    }
    qsort(atrasos, n, sizeof atrasos[0], compara);

    printf("amostras            : %d\n", n);
    printf("atraso mediano      : %.0f us\n", atrasos[n / 2] * 1e6);
    printf("atraso p99          : %.0f us\n", atrasos[n * 99 / 100] * 1e6);
    printf("atraso máximo       : %.0f us\n", atrasos[n - 1] * 1e6);
    printf("acima de 1,2 ms     : %d\n", acima_margem);
    printf("acima de 3 ms       : %d\n", acima_3ms);
    printf("saiu por conta      : %ld (nvcsw)\n", uso.ru_nvcsw);
    printf("tirada pelo sistema : %ld (nivcsw)\n", uso.ru_nivcsw);
    printf("fora do processador : %.1f%% do tempo\n", (1 - cpu / total) * 100);
    free(atrasos);
    return 0;
}
