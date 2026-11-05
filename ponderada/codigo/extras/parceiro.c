/*
 * parceiro.c
 *
 * Evidência do memorando da Parte B, dilema 3. Responde a duas perguntas com
 * medida, usando um módulo de parceiro simulado:
 *
 *   parceiro latencia: quanto tempo uma amostra leva para chegar ao módulo,
 *   como thread, como processo com memória somente leitura, em prioridade
 *   normal e mínima, e como processo com pipe. Rode com taskset, para as duas
 *   pontas dividirem um núcleo.
 *
 *   parceiro falhas: injeta três falhas no módulo, como thread e como processo,
 *   e conta o que acontece com o laço de 100 Hz que aciona o motor.
 *
 * No modo processo, a amostra fica em um memfd selado: o núcleo escreve e o
 * módulo só consegue mapear para leitura. Quem impede a escrita é a MMU, e nem
 * um mprotect do próprio módulo consegue reverter isso.
 *
 * Uso: parceiro latencia | parceiro falhas
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <semaphore.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <pthread.h>
#include <sched.h>
#include <time.h>
#include <unistd.h>

#define PAGINA 4096
#define AMOSTRAS 300
#define AMOSTRA_DA_FALHA 100
#define PERIODO_NS 10000000L
#define PROCESSAMENTO_S 0.0008
#define PRAZO_S 0.005
#define ESPERA_MAXIMA_S 5.0
#define OBSTACULO_MM 800
#define CAMINHO_LIVRE_MM 4000
#define LIMITE_VIBRACAO_MM 1500
#define MENSAGENS 50000
#define INTERVALO_MENSAGEM_NS 200000L

enum modo { THREAD, PROCESSO };
enum falha { ACESSO_INVALIDO, CORROMPE_AMOSTRA, TRAVA_NA_REGIAO };

/* Amostra publicada pelo núcleo. versao é ímpar enquanto ela está sendo escrita. */
struct amostra {
    atomic_uint versao;
    int numero;
    int distancia_mm;
    double gerada_em;
};

/* Área de escrita comum às duas pontas. Nada aqui bloqueia o núcleo no modo processo. */
struct controle {
    sem_t aviso;
    sem_t trava;
};

/* Contadores lidos pelo programa principal, que sobrevivem à morte da pulseira. */
struct placar {
    atomic_int processadas;
    atomic_int no_prazo;
    atomic_int falsas;
    atomic_int sinal_do_modulo;
};

/* Tudo o que o módulo do parceiro recebe. */
struct cenario {
    enum modo modo;
    enum falha falha;
    struct amostra *amostra;
    struct controle *controle;
};

/*
 * agora: lê o relógio monotônico.
 *
 * Parâmetros: nenhum.
 * Retorno: tempo em segundos, com origem arbitrária.
 * Funcionamento: esse relógio é o mesmo para todos os processos da máquina.
 */
static double agora(void)
{
    struct timespec t;

    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

/*
 * compartilhada: reserva memória anônima dividida com os processos filhos.
 *
 * Parâmetros:
 *   tamanho: bytes a reservar.
 * Retorno: ponteiro para a área zerada.
 * Funcionamento: MAP_SHARED mantém a área comum depois do fork.
 */
static void *compartilhada(size_t tamanho)
{
    return mmap(NULL, tamanho, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
}

/*
 * cria_area_selada: cria a página da amostra.
 *
 * Parâmetros:
 *   fd: recebe o descritor do memfd.
 * Retorno: mapeamento de escrita, que só o núcleo usa.
 * Funcionamento: F_SEAL_FUTURE_WRITE mantém este mapeamento e impede que
 * qualquer outro, criado depois, seja de escrita.
 */
static struct amostra *cria_area_selada(int *fd)
{
    *fd = memfd_create("amostras", MFD_ALLOW_SEALING);
    if (ftruncate(*fd, PAGINA) != 0)
        exit(1);
    struct amostra *area = mmap(NULL, PAGINA, PROT_READ | PROT_WRITE, MAP_SHARED, *fd, 0);
    fcntl(*fd, F_ADD_SEALS, F_SEAL_FUTURE_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL);
    return area;
}

/*
 * mapeia_somente_leitura: troca, no módulo, o mapeamento herdado pelo de leitura.
 *
 * Parâmetros:
 *   area_escrita: mapeamento herdado do fork.
 *   fd: descritor do memfd selado.
 * Retorno: mapeamento somente leitura.
 * Funcionamento: um programa carregado com exec já nasceria sem o mapeamento
 * de escrita; aqui o munmap faz esse papel.
 */
static struct amostra *mapeia_somente_leitura(struct amostra *area_escrita, int fd)
{
    munmap(area_escrita, PAGINA);
    return mmap(NULL, PAGINA, PROT_READ, MAP_SHARED, fd, 0);
}

/*
 * publica: grava uma amostra de um jeito que o leitor detecte a escrita.
 *
 * Parâmetros:
 *   a: área da amostra.
 *   numero: número da amostra.
 *   distancia_mm: distância lida do sensor.
 * Retorno: nenhum.
 * Funcionamento: é um seqlock. A versão fica ímpar durante a escrita. O núcleo
 * nunca espera ninguém para publicar.
 */
static void publica(struct amostra *a, int numero, int distancia_mm)
{
    atomic_fetch_add(&a->versao, 1);
    a->numero = numero;
    a->distancia_mm = distancia_mm;
    a->gerada_em = agora();
    atomic_fetch_add(&a->versao, 1);
}

/*
 * le_sem_trava: lê uma amostra sem nunca bloquear quem escreve.
 *
 * Parâmetros:
 *   a: área da amostra, que pode ser somente leitura.
 *   copia: recebe a amostra lida.
 * Retorno: nenhum.
 * Funcionamento: repete a leitura se a versão mudou ou estava ímpar.
 */
static void le_sem_trava(const struct amostra *a, struct amostra *copia)
{
    unsigned antes, depois;

    do {
        antes = atomic_load(&a->versao);
        copia->numero = a->numero;
        copia->distancia_mm = a->distancia_mm;
        copia->gerada_em = a->gerada_em;
        depois = atomic_load(&a->versao);
    } while (antes != depois || (antes & 1));
}

/*
 * modulo_parceiro: código do parceiro, igual nos dois modos.
 *
 * Parâmetros:
 *   arg: ponteiro para struct cenario.
 * Retorno: não retorna.
 * Funcionamento: lê cada amostra nova. Como thread, divide uma trava com o
 * núcleo, porque lê a memória dele diretamente. Como processo, não existe
 * trava comum. A partir de AMOSTRA_DA_FALHA, executa o defeito do cenário.
 */
static void *modulo_parceiro(void *arg)
{
    struct cenario *c = arg;
    struct amostra lida;

    for (;;) {
        sem_wait(&c->controle->aviso);
        if (c->modo == THREAD)
            sem_wait(&c->controle->trava);
        le_sem_trava(c->amostra, &lida);

        if (lida.numero >= AMOSTRA_DA_FALHA) {
            if (c->falha == ACESSO_INVALIDO) {
                *(volatile int *)0 = 1;
            } else if (c->falha == CORROMPE_AMOSTRA) {
                if (mprotect(c->amostra, PAGINA, PROT_READ | PROT_WRITE) != 0)
                    perror("módulo: mprotect recusado");
                if (c->modo == THREAD)
                    sem_post(&c->controle->trava);
                for (;;)
                    ((volatile struct amostra *)c->amostra)->distancia_mm = CAMINHO_LIVRE_MM;
            } else {
                for (;;)
                    pause();
            }
        }
        if (c->modo == THREAD)
            sem_post(&c->controle->trava);
    }
    return NULL;
}

/*
 * dorme_ate_o_proximo: espera o próximo tique de 10 ms.
 *
 * Parâmetros:
 *   t: instante do tique atual, avançado por esta função.
 * Retorno: nenhum.
 * Funcionamento: usa tempo absoluto, para os atrasos não se acumularem.
 */
static void dorme_ate_o_proximo(struct timespec *t)
{
    t->tv_nsec += PERIODO_NS;
    if (t->tv_nsec >= 1000000000L) {
        t->tv_nsec -= 1000000000L;
        t->tv_sec++;
    }
    clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, t, NULL);
}

/*
 * laco_do_nucleo: o laço de 100 Hz que lê o sensor e aciona o motor.
 *
 * Parâmetros:
 *   c: cenário em execução.
 *   p: placar.
 * Retorno: nenhum.
 * Funcionamento: o obstáculo está sempre a 0,8 m, então o motor deveria vibrar
 * em toda amostra. Se a distância lida disser caminho livre, a amostra conta
 * como falsa. Como thread, cada acesso passa pela trava dividida com o módulo.
 */
static void laco_do_nucleo(struct cenario *c, struct placar *p)
{
    struct timespec tique;
    struct amostra lida;

    clock_gettime(CLOCK_MONOTONIC, &tique);
    for (int i = 0; i < AMOSTRAS; i++) {
        double inicio = agora();

        if (c->modo == THREAD)
            sem_wait(&c->controle->trava);
        publica(c->amostra, i, OBSTACULO_MM);
        if (c->modo == THREAD)
            sem_post(&c->controle->trava);
        sem_post(&c->controle->aviso);

        while (agora() < inicio + PROCESSAMENTO_S)
            ;

        if (c->modo == THREAD)
            sem_wait(&c->controle->trava);
        le_sem_trava(c->amostra, &lida);
        if (c->modo == THREAD)
            sem_post(&c->controle->trava);

        if (lida.distancia_mm >= LIMITE_VIBRACAO_MM)
            atomic_fetch_add(&p->falsas, 1);
        atomic_fetch_add(&p->processadas, 1);
        if (agora() - inicio <= PRAZO_S)
            atomic_fetch_add(&p->no_prazo, 1);

        dorme_ate_o_proximo(&tique);
    }
}

/*
 * pulseira: processo que simula a pulseira inteira em um cenário.
 *
 * Parâmetros:
 *   modo: como o módulo roda.
 *   falha: defeito do módulo.
 *   p: placar.
 * Retorno: não retorna.
 * Funcionamento: cria o módulo como thread ou como processo filho e roda o
 * laço. Roda em um processo próprio porque, como thread, o módulo pode matar
 * a pulseira toda, e o placar precisa sobreviver a isso. No fim, anota se o
 * sistema matou o módulo.
 */
static void pulseira(enum modo modo, enum falha falha, struct placar *p)
{
    int fd;
    struct cenario c = {.modo = modo, .falha = falha};

    c.amostra = cria_area_selada(&fd);
    c.controle = compartilhada(sizeof *c.controle);
    sem_init(&c.controle->aviso, 1, 0);
    sem_init(&c.controle->trava, 1, 1);

    pid_t modulo = 0;
    if (modo == THREAD) {
        pthread_t t;
        pthread_create(&t, NULL, modulo_parceiro, &c);
    } else {
        modulo = fork();
        if (modulo == 0) {
            c.amostra = mapeia_somente_leitura(c.amostra, fd);
            modulo_parceiro(&c);
        }
    }

    laco_do_nucleo(&c, p);

    if (modulo != 0) {
        int status = 0;
        if (waitpid(modulo, &status, WNOHANG) == modulo && WIFSIGNALED(status))
            atomic_store(&p->sinal_do_modulo, WTERMSIG(status));
        kill(modulo, SIGKILL);
    }
    _exit(0);
}

/*
 * roda_cenario: executa um cenário e imprime uma linha de resultado.
 *
 * Parâmetros:
 *   nome_falha: descrição do defeito.
 *   modo: como o módulo roda.
 *   falha: defeito do módulo.
 * Retorno: nenhum.
 * Funcionamento: espera a pulseira terminar. Se ela não terminar em
 * ESPERA_MAXIMA_S, registra que congelou e encerra o processo.
 */
static void roda_cenario(const char *nome_falha, enum modo modo, enum falha falha)
{
    struct placar *p = compartilhada(sizeof *p);
    pid_t pid = fork();

    if (pid == 0)
        pulseira(modo, falha, p);

    int status = 0;
    double limite = agora() + ESPERA_MAXIMA_S;
    while (waitpid(pid, &status, WNOHANG) == 0) {
        if (agora() >= limite) {
            kill(pid, SIGKILL);
            waitpid(pid, NULL, 0);
            status = -1;
            break;
        }
        usleep(10000);
    }

    const char *fim = "terminou normalmente";
    if (status == -1)
        fim = "congelou";
    else if (WIFSIGNALED(status))
        fim = strsignal(WTERMSIG(status));

    char modulo[64] = "";
    int sinal = atomic_load(&p->sinal_do_modulo);
    if (sinal != 0)
        snprintf(modulo, sizeof modulo, " (módulo morto: %s)", strsignal(sinal));

    printf("%-9s %4d/%d %8d %7d   %s: %s%s\n", modo == THREAD ? "thread" : "processo",
           atomic_load(&p->processadas), AMOSTRAS, atomic_load(&p->no_prazo),
           atomic_load(&p->falsas), nome_falha, fim, modulo);
    munmap(p, sizeof *p);
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
 * imprime_latencias: resume as latências de um arranjo.
 *
 * Parâmetros:
 *   rotulo: nome do arranjo.
 *   latencias: vetor com MENSAGENS valores em segundos.
 * Retorno: nenhum.
 * Funcionamento: ordena o vetor e imprime mediana, p99 e máximo.
 */
static void imprime_latencias(const char *rotulo, double *latencias)
{
    qsort(latencias, MENSAGENS, sizeof *latencias, compara);
    printf("%9.1f %9.1f %9.1f   %s\n", latencias[MENSAGENS / 2] * 1e6,
           latencias[MENSAGENS * 99 / 100] * 1e6, latencias[MENSAGENS - 1] * 1e6, rotulo);
}

/* Parâmetros da leitora no teste de latência. */
struct leitora {
    struct amostra *amostra;
    struct controle *controle;
    double *latencias;
};

/*
 * le_com_aviso: ponta do módulo no teste de latência com semáforo.
 *
 * Parâmetros:
 *   arg: ponteiro para struct leitora.
 * Retorno: NULL.
 * Funcionamento: dorme no semáforo, lê a amostra e anota há quanto tempo ela
 * foi gerada.
 */
static void *le_com_aviso(void *arg)
{
    struct leitora *l = arg;
    struct amostra lida;

    for (int i = 0; i < MENSAGENS; i++) {
        sem_wait(&l->controle->aviso);
        le_sem_trava(l->amostra, &lida);
        l->latencias[i] = agora() - lida.gerada_em;
    }
    return NULL;
}

/*
 * escreve_com_aviso: ponta do núcleo no teste de latência com semáforo.
 *
 * Parâmetros:
 *   a: área da amostra.
 *   controle: semáforo de aviso.
 * Retorno: nenhum.
 * Funcionamento: publica uma amostra a cada INTERVALO_MENSAGEM_NS e avisa.
 */
static void escreve_com_aviso(struct amostra *a, struct controle *controle)
{
    struct timespec pausa = {0, INTERVALO_MENSAGEM_NS};

    for (int i = 0; i < MENSAGENS; i++) {
        publica(a, i, OBSTACULO_MM);
        sem_post(&controle->aviso);
        nanosleep(&pausa, NULL);
    }
}

/*
 * latencia_thread: mede o arranjo que a parceira exige.
 *
 * Parâmetros:
 *   latencias: vetor de resultado.
 * Retorno: nenhum.
 * Funcionamento: thread no mesmo processo, lendo a memória diretamente.
 */
static void latencia_thread(double *latencias)
{
    int fd;
    struct leitora l = {cria_area_selada(&fd), compartilhada(sizeof(struct controle)), latencias};
    pthread_t t;

    sem_init(&l.controle->aviso, 1, 0);
    pthread_create(&t, NULL, le_com_aviso, &l);
    escreve_com_aviso(l.amostra, l.controle);
    pthread_join(t, NULL);
}

/*
 * latencia_memoria: mede o arranjo proposto no memorando.
 *
 * Parâmetros:
 *   latencias: vetor de resultado, em memória compartilhada.
 *   prioridade_minima: true para o módulo rodar em SCHED_IDLE.
 * Retorno: nenhum.
 * Funcionamento: processo separado, lendo a amostra por um mapeamento somente
 * leitura e acordando por um semáforo que o núcleo só incrementa. Em SCHED_IDLE,
 * o módulo só roda quando o núcleo dorme, como o memorando propõe.
 */
static void latencia_memoria(double *latencias, bool prioridade_minima)
{
    int fd;
    struct leitora l = {cria_area_selada(&fd), compartilhada(sizeof(struct controle)), latencias};

    sem_init(&l.controle->aviso, 1, 0);
    pid_t pid = fork();
    if (pid == 0) {
        struct sched_param prioridade = {0};

        if (prioridade_minima && sched_setscheduler(0, SCHED_IDLE, &prioridade) != 0)
            _exit(1);
        l.amostra = mapeia_somente_leitura(l.amostra, fd);
        le_com_aviso(&l);
        _exit(0);
    }
    escreve_com_aviso(l.amostra, l.controle);
    waitpid(pid, NULL, 0);
}

/*
 * latencia_pipe: mede a comunicação clássica entre processos.
 *
 * Parâmetros:
 *   latencias: vetor de resultado, em memória compartilhada.
 * Retorno: nenhum.
 * Funcionamento: a amostra é copiada por write e read em um pipe.
 */
static void latencia_pipe(double *latencias)
{
    int canal[2];
    struct timespec pausa = {0, INTERVALO_MENSAGEM_NS};
    double gerada_em;

    if (pipe(canal) != 0)
        exit(1);
    pid_t pid = fork();
    if (pid == 0) {
        for (int i = 0; i < MENSAGENS; i++) {
            if (read(canal[0], &gerada_em, sizeof gerada_em) != sizeof gerada_em)
                _exit(1);
            latencias[i] = agora() - gerada_em;
        }
        _exit(0);
    }
    for (int i = 0; i < MENSAGENS; i++) {
        gerada_em = agora();
        if (write(canal[1], &gerada_em, sizeof gerada_em) != sizeof gerada_em)
            exit(1);
        nanosleep(&pausa, NULL);
    }
    waitpid(pid, NULL, 0);
}

/*
 * mede_latencias: executa os quatro arranjos.
 *
 * Parâmetros: nenhum.
 * Retorno: nenhum.
 * Funcionamento: imprime uma linha por arranjo, em microssegundos.
 */
static void mede_latencias(void)
{
    double *latencias = compartilhada(MENSAGENS * sizeof *latencias);

    printf("  mediana       p99    máximo   arranjo (microssegundos)\n");
    latencia_thread(latencias);
    imprime_latencias("thread, memória direta", latencias);
    latencia_memoria(latencias, false);
    imprime_latencias("processo, memória só de leitura", latencias);
    latencia_memoria(latencias, true);
    imprime_latencias("processo, memória só de leitura, SCHED_IDLE", latencias);
    latencia_pipe(latencias);
    imprime_latencias("processo, pipe", latencias);
}

/*
 * injeta_falhas: executa as três falhas nos dois modos.
 *
 * Parâmetros: nenhum.
 * Retorno: nenhum.
 * Funcionamento: cada cenário dura 3 s de laço de 100 Hz, com a falha em 1 s.
 */
static void injeta_falhas(void)
{
    static const struct {
        const char *nome;
        enum falha falha;
    } casos[] = {
        {"acesso indevido", ACESSO_INVALIDO},
        {"escreve na amostra", CORROMPE_AMOSTRA},
        {"segura a trava", TRAVA_NA_REGIAO},
    };

    printf("%-9s %8s %8s %7s   %s\n", "modo", "motor", "no prazo", "falsas", "falha: como terminou");
    for (size_t i = 0; i < sizeof casos / sizeof casos[0]; i++) {
        roda_cenario(casos[i].nome, THREAD, casos[i].falha);
        roda_cenario(casos[i].nome, PROCESSO, casos[i].falha);
    }
}

/*
 * main: escolhe o experimento pela linha de comando.
 *
 * Parâmetros:
 *   argc, argv: "latencia" ou "falhas".
 * Retorno: 0, ou 1 se o argumento estiver errado.
 * Funcionamento: desvia para o experimento pedido.
 */
int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "latencia") == 0) {
        mede_latencias();
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "falhas") == 0) {
        injeta_falhas();
        return 0;
    }
    fprintf(stderr, "uso: %s latencia | falhas\n", argv[0]);
    return 1;
}
