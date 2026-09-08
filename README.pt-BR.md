# pixelbench

**Um benchmark de FPS em pixel art para o Raspberry Pi**, com telemetria térmica
e de throttling embutida no resultado.

Ele desenha um pôr do sol synthwave animado — um mar construído com física de
ondas de verdade, uma ilha com um náufrago cumprindo sua rotina, pássaros e uma
trilha sintetizada em numpy — e reporta FPS, frametime, 1% low, temperatura do
chip e `vcgencmd get_throttled`, tudo num bloco só.

[English](README.md)

```
=== pixelbench - pixel art FPS benchmark =========================
 preset...........: medium  (480x270 internal, 90 sprites)
 output...........: 1920x1080 x4 (fullscreen)
 scaler...........: sdl2 (accelerated) @ x11  vsync OFF
 soundtrack.......: synthesised ambient, volume 0.55
 duration.........: 33.4 s, 3262 frames
------------------------------------------------------------------
 average FPS......:     97.5
 FPS min / max....:     43.5 / 129.7
 1% low (p99 ms)..:     79.4  (12.59 ms)
 mean frametime...:    10.25 ms  (median 10.16 ms)
 stability........: stdev 0.64 ms
------------------------------------------------------------------
 temperature......: 51.2 C -> 53.5 C  (peak 54.0 C)
 throttled........: 0x0 -> 0x0
==================================================================
```

## Por que existe, e por que é específico para Raspberry Pi

Um triângulo girando a 4000 FPS diz muito pouco sobre um computador de placa
única. Este benchmark foi escrito para o Raspberry Pi e faz quatro escolhas por
causa disso.

**Ele reporta se a placa estava com throttling.** Um FPS medido enquanto o SoC
estava limitado descreve a refrigeração, não a máquina. O `vcgencmd get_throttled`
é amostrado numa thread própria durante toda a rodada e fica retido, então um
evento de um segundo ainda aparece no bloco final. Sem essa linha, um número de
benchmark vindo de um Pi não é um resultado.

**As resoluções são divisores exatos de 1920x1080.** 240x135, 480x270, 640x360 e
960x540 sobem exatamente x8, x4, x3 e x2 num monitor 1080p. A escala é inteira e
nearest-neighbour: nada é reamostrado, nada fica com tarja, e a carga que você
mede é a que você pediu.

**Ele separa o upscale da cena.** Num Pi 5, escalar para 1080p *na CPU* custa
cerca de 10 ms por quadro e vira o gargalo — todos os presets ficam presos em
~45 FPS, independentemente do custo real. Passando o upscale para o renderer do
SDL, o FPS praticamente dobra e volta a acompanhar a cena. O `--cpu` roda o
caminho de software de propósito, para você medir a diferença na sua placa.

**A carga é uma cena de verdade.** Mar, camadas em paralaxe, blits de sprite,
busca em paleta e trabalho de array em numpy — a mistura que um jogo 2D pequeno
realmente produz, não um laço sintético. E é determinística (semente fixa, fase
da água quantizada), então duas rodadas medem a mesma imagem.

Tudo que é específico do Pi degrada com elegância: em hardware sem `vcgencmd` a
telemetria mostra `n/a` e o benchmark roda do mesmo jeito.

## Instalação

Precisa de Python 3.9+, SDL2 e um `pygame` com `pygame._sdl2` (qualquer wheel do
PyPI serve; no Raspberry Pi OS, `sudo apt install python3-pygame python3-numpy`
também funciona).

```bash
pip install git+https://github.com/RenantDev/pixelbench-pi
```

## Uso

```bash
pixelbench                     # preset medium, tela cheia, roda até apertar ESC
pixelbench -c heavy            # preset mais pesado
pixelbench -c extreme -t 60    # stress test, para sozinho em 60 s
pixelbench --cpu               # escala por software, para comparar com a GPU
pixelbench --headless          # sem janela: só o custo de CPU do render
pixelbench --json result.json  # também grava o resumo legível por máquina
```

| Flag | Padrão | O que faz |
|---|---|---|
| `-c, --load` | `medium` | preset: `light`, `medium`, `heavy`, `extreme` |
| `-t, --time` | `0` | duração em segundos (`0` = roda até o ESC) |
| `-n, --sprites` | do preset | número de pássaros |
| `-r, --resolution` | do preset | resolução interna, ex.: `640x360` |
| `-w, --windowed` | off | roda em janela em vez de tela cheia |
| `-j, --window` | `1280x720` | tamanho da janela com `-w` |
| `--cpu` | off | escala por software em vez do renderer do SDL |
| `--vsync` | off | trava o FPS na taxa do monitor |
| `--headless` | off | sem janela; mede só o custo de CPU |
| `--no-sound` | off | roda em silêncio |
| `--volume` | `0.55` | volume da trilha |
| `--no-hud` | off | começa com o HUD escondido |
| `--json ARQ` | — | grava o resumo em JSON |

Teclas: `ESC`/`Q` sai, `SPACE` pausa, `F` janela/tela cheia, `M` muda a trilha,
`H` esconde o HUD, `+`/`-` mudam o número de sprites.

## Resultados de referência

Raspberry Pi 5 (8 GB), Debian 13, X11, tela cheia 1920x1080, vsync desligado,
sem overclock, refrigeração ativa. `throttled=0x0` do início ao fim.

| Rodada | FPS médio |
|---|---|
| `light` | ~108 |
| `medium` | ~92 |
| `heavy` | ~78 |
| `extreme` | ~35 |
| `medium --cpu` | ~48 |
| `medium --vsync` | 60,0 (limite do monitor — esperado, não é falha) |

A trilha não custa quadros: 99,9 FPS com som contra 99,6 sem, no mesmo preset.
Se você vir queda, não culpe o áudio.

## Como ler o resultado

**O FPS médio é o número menos útil do bloco.** Olhe estes:

- **1% low** — o FPS do 1% pior dos quadros. Uma média de 90 FPS feita de 95
  estáveis com travadas ocasionais de 20 ms é muito pior que 85 constantes, e só
  esta linha mostra a diferença.
- **Mediana do frametime vs. média** — se a mediana está bem abaixo da média,
  alguns quadros lentos estão inflando a conta.
- **`throttled`** — qualquer coisa diferente de `0x0` invalida a rodada.
- **Temperatura** — subir alguns graus é normal; chegando perto de 80 °C, a
  curva da ventoinha vira aquilo que você está medindo.

## Como funciona

- [Física de ondas](docs/wave-physics.md)
- [Regras de pixel art](docs/pixel-art-rules.md)
- [Síntese de áudio](docs/audio-synthesis.md)
- [Metodologia do benchmark](docs/benchmarking.md)

*(A documentação técnica está em inglês.)*

## Licença

MIT — veja [LICENSE](LICENSE).
