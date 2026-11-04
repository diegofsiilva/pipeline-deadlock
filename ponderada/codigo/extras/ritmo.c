/*
 * ritmo.c
 *
 * Roda o buffer das versões 2 e 3 no ritmo real da pulseira. As versões da
 * questão A4 correm o mais rápido que podem, então o buffer enche na largada.
 * Aqui o sensor gera uma amostra a cada 10 ms e o motor leva 0,8 ms por
 * amostra, o tempo médio da Plataforma V na questão A1.
 *
 * O programa pode pausar o motor uma única vez, para simular um atraso raro, e
 * mede quanto tempo cada amostra levou do sensor até o fim do processamento.
 *
 * Uso: ritmo <versao 2 ou 3> <pausa do motor em ms>
 */

#include <semaphore.h>

#include "../comum.h"

#define PERIODO_NS 10000000L
#define SERVICO_S 0.0008
#define PRAZO_S 0.005
#define AMOSTRA_DA_PAUSA 1000

static sem_t vazio, cheio, mutex;
static int versao;
static int pausa_ms;
static double gerada_em[TOTAL_AMOSTRAS];
static double latencia_maxima;
static atomic_int acima_do_prazo;

/*
 * proximo_periodo: avança um instante absoluto em um período.
 *
 * Parâmetros:
 *   t: instante a ser avançado.
 * Retorno: nenhum.
 * Funcionamento: soma PERIODO_NS e normaliza os nanossegundos. Usar tempo
 * absoluto evita que os atrasos se acumulem.
 */
static void proximo_periodo(struct timespec *t)
{
    t->tv_nsec += PERIODO_NS;
    if (t->tv_nsec >= 1000000000L) {
        t->tv_nsec -= 1000000000L;
        t->tv_sec++;
    }
}

/*
 * gira: ocupa o processador por um intervalo.
 *
 * Parâmetros:
 *   segundos: duração da espera.
 * Retorno: nenhum.
 * Funcionamento: laço no relógio, para simular processamento de verdade.
 */
static void gira(double segundos)
{
    double fim = agora() + segundos;

    while (agora() < fim)
        ;
}

/*
 * produtor: thread do sensor, gera uma amostra a cada 10 ms.
 *
 * Parâmetros:
 *   arg: não usado.
 * Retorno: NULL.
 * Funcionamento: anota o instante de geração e usa, no DOWN, a ordem da versão
 * pedida na linha de comando.
 */
static void *produtor(void *arg)
{
    struct timespec proximo;

    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &proximo);

    for (int amostra = 0; amostra < TOTAL_AMOSTRAS; amostra++) {
        gerada_em[amostra] = agora();

        if (versao == 2) {
            sem_wait(&vazio);
            sem_wait(&mutex);
        } else {
            sem_wait(&mutex);
            sem_wait(&vazio);
        }

        buffer[entrada] = amostra;
        entrada = (entrada + 1) % N;

        sem_post(&mutex);
        sem_post(&cheio);
        registra_producao();

        proximo_periodo(&proximo);
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &proximo, NULL);
    }
    return NULL;
}

/*
 * consumidor: thread do motor, processa cada amostra e mede a latência.
 *
 * Parâmetros:
 *   arg: não usado.
 * Retorno: NULL.
 * Funcionamento: na amostra AMOSTRA_DA_PAUSA, dorme pausa_ms antes de
 * processar. A latência vai da geração da amostra ao fim do processamento.
 */
static void *consumidor(void *arg)
{
    (void)arg;

    for (int i = 0; i < TOTAL_AMOSTRAS; i++) {
        sem_wait(&cheio);
        sem_wait(&mutex);

        int amostra = buffer[saida];
        saida = (saida + 1) % N;

        sem_post(&mutex);
        sem_post(&vazio);

        if (i == AMOSTRA_DA_PAUSA)
            usleep(pausa_ms * 1000);
        gira(SERVICO_S);

        double latencia = agora() - gerada_em[amostra];
        if (latencia > latencia_maxima)
            latencia_maxima = latencia;
        if (latencia > PRAZO_S)
            atomic_fetch_add(&acima_do_prazo, 1);

        registra_consumo(amostra);
    }
    return NULL;
}

/*
 * main: lê os argumentos, cria as threads e entrega o controle ao vigia.
 *
 * Parâmetros:
 *   argc, argv: versão (2 ou 3) e pausa do motor em ms.
 * Retorno: 0, ou 1 se os argumentos estiverem errados.
 * Funcionamento: depois do relatório comum, imprime as medidas de prazo.
 */
int main(int argc, char **argv)
{
    pthread_t sensor, motor;

    if (argc != 3) {
        fprintf(stderr, "uso: %s <versao 2 ou 3> <pausa em ms>\n", argv[0]);
        return 1;
    }
    versao = atoi(argv[1]);
    pausa_ms = atoi(argv[2]);

    sem_init(&vazio, 0, N);
    sem_init(&cheio, 0, 0);
    sem_init(&mutex, 0, 1);

    double inicio = agora();
    pthread_create(&sensor, NULL, produtor, NULL);
    pthread_create(&motor, NULL, consumidor, NULL);

    bool travou = vigia();
    printf("Pausa do motor: %d ms na amostra %d\n", pausa_ms, AMOSTRA_DA_PAUSA);
    relatorio(versao == 2 ? "Versão 2 a 100 Hz" : "Versão 3 a 100 Hz", travou, agora() - inicio);
    printf("  latência máxima : %.2f ms\n", latencia_maxima * 1e3);
    printf("  acima de 5 ms   : %d amostras\n", atomic_load(&acima_do_prazo));
    return 0;
}
