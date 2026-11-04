/*
 * versao3.c
 *
 * Questão A4, versão 3: igual à versão 2, com a ordem trocada no produtor.
 *
 *   vazio (começa em N): posições livres; quem espera é o produtor.
 *   cheio (começa em 0): amostras prontas; quem espera é o consumidor.
 *   mutex (começa em 1): exclusão mútua no acesso ao buffer.
 *
 * sem_wait é o DOWN (P) e sem_post é o UP (V) da aula.
 *
 * Uso: make v3
 */

#include <semaphore.h>

#include "comum.h"

static sem_t vazio, cheio, mutex;

/*
 * produtor: thread do sensor, gera as amostras 0, 1, 2, ...
 *
 * Parâmetros:
 *   arg: não usado.
 * Retorno: NULL.
 * Funcionamento: pega o mutex antes de garantir uma posição livre. Com o
 * buffer cheio, dorme em vazio segurando o mutex que o consumidor precisa.
 */
static void *produtor(void *arg)
{
    (void)arg;

    for (int amostra = 0; amostra < TOTAL_AMOSTRAS; amostra++) {
        sem_wait(&mutex);
        sem_wait(&vazio);

        buffer[entrada] = amostra;
        entrada = (entrada + 1) % N;

        sem_post(&mutex);
        sem_post(&cheio);

        registra_producao();
    }
    return NULL;
}

/*
 * consumidor: thread do motor, recebe as amostras do buffer.
 *
 * Parâmetros:
 *   arg: não usado.
 * Retorno: NULL.
 * Funcionamento: primeiro garante uma amostra pronta, depois pega o mutex.
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

        registra_consumo(amostra);
    }
    return NULL;
}

/*
 * imprime_semaforos: mostra o valor final dos três semáforos.
 *
 * Parâmetros: nenhum.
 * Retorno: nenhum.
 * Funcionamento: lê cada um com sem_getvalue, para mostrar quem ficou com o
 * quê quando a execução terminou.
 */
static void imprime_semaforos(void)
{
    int v, c, m;

    sem_getvalue(&vazio, &v);
    sem_getvalue(&cheio, &c);
    sem_getvalue(&mutex, &m);
    printf("  semáforos  : vazio=%d cheio=%d mutex=%d\n", v, c, m);
}

/*
 * main: inicia os semáforos, cria as threads e entrega o controle ao vigia.
 *
 * Parâmetros: nenhum.
 * Retorno: 0.
 * Funcionamento: não faz join, porque uma thread pode ter ficado dormindo em
 * um semáforo. O fim do processo encerra as duas.
 */
int main(void)
{
    pthread_t sensor, motor;

    sem_init(&vazio, 0, N);
    sem_init(&cheio, 0, 0);
    sem_init(&mutex, 0, 1);

    double inicio = agora();
    pthread_create(&sensor, NULL, produtor, NULL);
    pthread_create(&motor, NULL, consumidor, NULL);

    bool travou = vigia();
    relatorio("Versão 3, ordem trocada", travou, agora() - inicio);
    imprime_semaforos();
    return 0;
}
