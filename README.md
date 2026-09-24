# Montador

Prepara a montagem de vídeos narrados a partir de um roteiro dividido em cenas.
Você escreve o roteiro num arquivo `.md`, arrasta sobre o `montar.bat` e recebe:

- a narração de cada cena (`audio/cena_01.mp3`, `cena_02.mp3`...);
- a narração completa, com pausa entre as cenas (`narracao_completa.mp3`);
- as legendas sincronizadas (`legendas.srt`);
- a linha do tempo com início, fim, duração, termo de busca da imagem e texto de tela
  (`linha_do_tempo.csv`, que abre no Excel, e `checklist.md`);
- as pastas vazias `imagens/` e `export/` para você completar a edição.

Funciona no Windows 10/11, sem placa de vídeo, e aceita pastas com espaços e acentos.

---

## Passo a passo (primeira vez)

### 1. Baixar o montador

Na página do repositório no GitHub, clique em **Code → Download ZIP**.
Extraia o ZIP numa pasta fácil de achar, por exemplo `Documentos\Montador`.

### 2. Instalar o Python

1. Acesse <https://www.python.org/downloads/> e clique em **Download Python**.
2. Abra o instalador. **Na primeira tela, marque "Add python.exe to PATH"** (importante!).
3. Clique em **Install Now** e aguarde.

> Se esquecer este passo, o `instalar.bat` avisa e abre a página de download.

### 3. Instalar o ffmpeg (para gerar a narração completa)

Sem o ffmpeg o montador funciona, mas gera só os áudios das cenas (ele avisa).

**Jeito mais fácil (Windows 10/11 com winget):**

1. Clique no menu Iniciar, digite `cmd` e abra o **Prompt de Comando**.
2. Digite e tecle Enter:
   ```
   winget install Gyan.FFmpeg
   ```
3. Feche o Prompt de Comando quando terminar.

**Jeito manual (se o winget não existir):**

1. Acesse <https://www.gyan.dev/ffmpeg/builds/> e baixe `ffmpeg-release-essentials.zip`.
2. Extraia o ZIP. Dentro dele há uma pasta com uma subpasta `bin`.
3. Copie a pasta extraída para dentro da pasta do montador e renomeie para `ffmpeg`,
   de modo que exista `Montador\ffmpeg\bin\ffmpeg.exe`. Pronto: o montador acha sozinho.
   (Outra opção: `C:\ffmpeg\bin\ffmpeg.exe`, ou adicionar a pasta `bin` ao PATH do Windows.)

### 4. Instalar o montador

Dê dois cliques no **`instalar.bat`**. Ele confere o Python, cria o ambiente virtual
(pasta `.venv`), instala as dependências e procura o ffmpeg. Precisa de internet.

> Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**.

---

## Uso no dia a dia

1. Escreva o roteiro (veja o formato abaixo) e salve como `.md` — pode ser no Bloco de Notas.
2. **Arraste o arquivo `.md` e solte em cima do `montar.bat`.**
3. O montador primeiro **valida** o texto e mostra, cena por cena, o que a voz pode ler errado.
   Se houver avisos, ele pergunta se quer continuar (Enter = sim; `n` = parar para corrigir).
4. Depois gera os arquivos em:
   ```
   episodios\<canal>\<AAAA-MM-DD>_<episodio>\
   ```

Para testar agora, arraste `exemplos\exemplo-paper-trail.md` sobre o `montar.bat`.
(Esse exemplo tem avisos de propósito: números, "Dr.", "FBI" e uma frase longa.)

### Formato do roteiro

```
CANAL: paper-trail
EPISODIO: nome-do-episodio

=== CENA 1 ===
NARRACAO: texto da narração
IMAGEM: termo de busca da imagem
TELA: texto na tela (ou -)

=== CENA 2 ===
NARRACAO: ...
IMAGEM: ...
TELA: -
```

- `CANAL` precisa existir no `canais.yaml`.
- A narração pode continuar em várias linhas.
- `TELA: -` significa "sem texto na tela".
- Acentos (`NARRAÇÃO`, `EPISÓDIO`) e maiúsculas/minúsculas são aceitos nos nomes dos campos.

### O que a validação aponta

Ela **só avisa, nunca altera o texto**. Aponta por cena:

| Aviso | Exemplo | Sugestão |
|---|---|---|
| algarismos | `1911`, `3,5` | escreva por extenso: "mil novecentos e onze" |
| abreviações | `art.`, `Dr.`, `nº` | escreva a palavra inteira: "artigo", "doutor", "número" |
| símbolos | `§`, `%`, `&` | "parágrafo", "por cento", "e" |
| siglas | `FBI`, `ONU` | confira se a voz soletra ou lê como palavra |
| frase longa | mais de 25 palavras | divida em frases menores |

Para só validar, sem gerar áudio, abra o Prompt de Comando na pasta do montador e rode:

```
.venv\Scripts\python -m montador validar "C:\caminho\do\roteiro.md"
```

---

## Vozes e canais (`canais.yaml`)

Cada canal tem sua voz. Abra o `canais.yaml` no Bloco de Notas:

```yaml
canais:
  paper-trail:
    motor: edge              # edge (gratuito), azure ou elevenlabs
    voz: en-US-AndrewNeural
    velocidade: "+0%"        # "+10%" mais rápido, "-10%" mais devagar
    tom: "+0Hz"              # "-5Hz" mais grave, "+5Hz" mais agudo
    pausa: 0.8               # segundos de silêncio entre as cenas
```

Já vêm configurados `paper-trail` (inglês) e `antes-do-capitulo-1` (português).
Para criar um canal novo, copie um bloco, troque o nome e ajuste.

### Listar as vozes

Dê dois cliques em **`listar_vozes.bat`**, escolha o motor e o idioma (ex.: `pt-BR`).
Ou pelo Prompt de Comando:

```
.venv\Scripts\python -m montador vozes edge --idioma pt-BR
.venv\Scripts\python -m montador vozes azure --idioma en-US
.venv\Scripts\python -m montador vozes elevenlabs
```

### Os três motores

| Motor | Custo | Chave | Legenda |
|---|---|---|---|
| `edge` (padrão) | gratuito | não precisa | sincronizada por palavra |
| `azure` | pago (tem cota gratuita) | `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` | distribuída por frase, proporcional ao tamanho |
| `elevenlabs` | pago (tem cota gratuita) | `ELEVENLABS_API_KEY` | sincronizada por palavra |

No ElevenLabs, `voz` é o **ID** da voz (aparece no `listar_vozes.bat`) e o `tom` é ignorado.

### Chaves (arquivo `.env`)

O `instalar.bat` cria o arquivo `.env` a partir do `.env.exemplo`. Abra-o no Bloco de Notas
e preencha só as chaves do motor que for usar:

```
AZURE_SPEECH_KEY=sua-chave
AZURE_SPEECH_REGION=brazilsouth
ELEVENLABS_API_KEY=sua-chave
```

**Nunca coloque chaves no `canais.yaml` nem em outro arquivo.** O `.env` está no
`.gitignore` e não vai para o repositório.

---

## Opções avançadas

```
.venv\Scripts\python -m montador montar roteiro.md [opções]

  --saida PASTA        pasta base (padrão: episodios\)
  --data AAAA-MM-DD    data usada no nome da pasta (padrão: hoje)
  --motor MOTOR        usa outro motor só desta vez (edge, azure, elevenlabs)
  --canais ARQUIVO     outro arquivo de canais
  --sim                não pergunta nada, continua mesmo com avisos
```

Rodar de novo o mesmo roteiro no mesmo dia sobrescreve os áudios, legendas e linha do tempo
(as pastas `imagens/` e `export/` não são apagadas).

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| "O montador ainda não foi instalado" | Rode o `instalar.bat`. |
| "ffmpeg não encontrado" | Veja o passo 3. Os áudios das cenas, legendas e linha do tempo são gerados mesmo assim. |
| "O canal 'x' não está no canais.yaml" | Corrija a linha `CANAL:` do roteiro ou cadastre o canal. |
| "Falha de conexão com o serviço de voz" | Confira a internet; o edge-tts precisa dela. |
| "O edge-tts não devolveu áudio" | O nome da voz está errado. Use o `listar_vozes.bat`. |
| "chave recusada" | Confira a chave e a região no `.env`. |

---

## Para desenvolvedores

```
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

Os testes não usam internet: o motor de voz é simulado (`tests/conftest.py`).

Estrutura:

```
montador/
  roteiro.py      leitura do .md
  validacao.py    avisos de texto para TTS
  config.py       canais.yaml e .env
  motores/        edge, azure, elevenlabs
  audio.py        duração de MP3 (sem ffmpeg) e concatenação com ffmpeg
  legendas.py     legendas .srt
  montagem.py     gera a pasta do episódio
  cli.py          comandos validar, montar e vozes
```
