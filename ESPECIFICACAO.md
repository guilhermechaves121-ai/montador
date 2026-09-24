Crie neste repositório o "montador": um programa em Python que prepara a montagem de vídeos narrados a partir de um roteiro dividido em cenas. Ele vai rodar no Windows 10/11, num PC modesto e sem depender de GPU, usado por um iniciante: tudo precisa funcionar com dois cliques, com mensagens em português, e aceitar caminhos com espaços e acentos.

ENTRADA
Arquivo .md neste formato:

CANAL: paper-trail
EPISODIO: nome-do-episodio

=== CENA 1 ===
NARRACAO: texto da narração
IMAGEM: termo de busca da imagem
TELA: texto na tela (ou -)

SAÍDA, em episodios/<canal>/<AAAA-MM-DD>_<episodio>/
- audio/cena_01.mp3, cena_02.mp3...: narração de cada cena
- narracao_completa.mp3: cenas concatenadas com pausa configurável (via ffmpeg; sem ffmpeg, avisar e gerar só as cenas)
- legendas.srt: legenda única, sincronizada com a narração completa; se o motor não der tempos por palavra, distribuir por frase proporcionalmente ao tamanho
- linha_do_tempo.csv e checklist.md: cena, início, fim, duração, termo de busca e texto de tela
- pastas vazias imagens/ e export/

VOZ
- canais.yaml com motor, voz, velocidade, tom e pausa entre cenas, já com entradas para paper-trail (inglês) e antes-do-capitulo-1 (português)
- Três motores intercambiáveis: edge-tts (padrão), Azure Speech e ElevenLabs. Chaves só no .env, que fica no .gitignore; nunca gravar chave no repositório
- Comando para listar as vozes de cada motor

VALIDAÇÃO
Comando "validar", que roda antes de gerar áudio e aponta por cena o que o TTS costuma ler errado: algarismos, abreviações (art., Dr., nº), símbolos (§, %, &), siglas em maiúsculas e frases com mais de 25 palavras. Só avisa, não altera o texto.

USO
- instalar.bat: confere o Python (e orienta a instalar se faltar), cria o ambiente virtual e instala as dependências
- montar.bat: arrastar o .md sobre ele roda validação e montagem
- README.md em português, passo a passo para iniciante, incluindo instalar o ffmpeg no Windows

TESTES
pytest sem depender de internet: simule o motor de voz, porque este ambiente de nuvem bloqueia o serviço de voz. Inclua um roteiro de exemplo em exemplos/.

Mantenha as dependências mínimas, não versione episodios/ e abra um pull request com o resumo do que foi feito e como testar no Windows.
