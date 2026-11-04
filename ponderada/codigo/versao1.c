/*
 * versao1.c
 *
 * Questão A4, versão 1: buffer circular sem sincronização.
 *
 * O produtor e o consumidor dividem o contador de posições ocupadas e usam
 * espera ocupada. O sched_yield() entre ler e escrever o contador simula a
 * thread sendo interrompida no pior momento. O vigia encerra a execução se o
 * consumidor passar 1 s sem receber nada.
 *
 * volatile impede o compilador de transformar a espera ocupada em um laço
 * infinito, mas não torna o contador atômico.
 *
 * Uso: make v1
 */

#include "comum.h"

static volatile int ocupadas;

/*
 * produtor: thread do sensor, gera as amostras 0, 1, 2, ...
 *
 * Parâmetros:
 *   arg: não usado.
 * Retorno: NULL.
 * Funcionamento: espera ter posição livre, grava a amostra e soma 1 ao
 * contador em dois passos, ler e escrever, com o sched_yield() entre eles.
 */
static void *produtor(void *arg)
{
    (void)arg;

    for (int amostra = 0; amostra < TOTAL_AMOSTRAS; amostra++) {
        while (ocupadas == N)
            ; /* espera ocupada: buffer cheio */

        buffer[entrada] = amostra;
        entrada = (entrada + 1) % N;

        int lido = ocupadas;
        sched_yield();
        ocupadas = lido + 1;

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
 * Funcionamento: espera ter posição ocupada, lê a amostra e subtrai 1 do
 * contador em dois passos, ler e escrever, com o sched_yield() entre eles.
 */
static void *consumidor(void *arg)
{
    (void)arg;

    for (int i = 0; i < TOTAL_AMOSTRAS; i++) {
        while (ocupadas == 0)
            ; /* espera ocupada: buffer vazio */

        int amostra = buffer[saida];
        saida = (saida + 1) % N;

        int lido = ocupadas;
        sched_yield();
        ocupadas = lido - 1;

        registra_consumo(amostra);
    }
    return NULL;
}

/*
 * main: cria as threads e entrega o controle ao vigia.
 *
 * Parâmetros: nenhum.
 * Retorno: 0.
 * Funcionamento: não faz join, porque uma thread pode ter ficado presa na
 * espera ocupada. O fim do processo encerra as duas.
 */
int main(void)
{
    pthread_t sensor, motor;
    double inicio = agora();

    pthread_create(&sensor, NULL, produtor, NULL);
    pthread_create(&motor, NULL, consumidor, NULL);

    bool travou = vigia();
    relatorio("Versão 1, sem sincronização", travou, agora() - inicio);
    return 0;
}
