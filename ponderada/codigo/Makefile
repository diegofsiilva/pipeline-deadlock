# Makefile
#
# Compila e roda as versões da questão A4 com um único comando:
#   make v1    versão 1, sem sincronização
#   make v2    versão 2, com semáforos
#   make v3    versão 3, ordem trocada
#
# make tsan1 e make tsan2 rodam as versões 1 e 2 no ThreadSanitizer.

CC = gcc
CFLAGS = -O2 -g -Wall -Wextra -pthread -ffile-prefix-map="$(CURDIR)"=.

.PHONY: v1 v2 v3 tsan1 tsan2 limpa

v1: versao1
	./versao1

v2: versao2
	./versao2

v3: versao3
	./versao3

tsan1: versao1_tsan
	-TSAN_OPTIONS=report_thread_leaks=0 ./versao1_tsan

tsan2: versao2_tsan
	-TSAN_OPTIONS=report_thread_leaks=0 ./versao2_tsan

versao%: versao%.c comum.h
	$(CC) $(CFLAGS) -o $@ $<

versao%_tsan: versao%.c comum.h
	$(CC) -O1 -g -Wall -Wextra -pthread -fsanitize=thread -ffile-prefix-map="$(CURDIR)"=. -o $@ $<

limpa:
	rm -f versao1 versao2 versao3 versao1_tsan versao2_tsan
