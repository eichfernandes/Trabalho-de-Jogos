import pygame
import random
import math
from abc import ABC, abstractmethod
from collision import Collider


pygame.init()

# ---------------- configurações gerais ----------------

LARGURA, ALTURA = 480, 620
FPS = 60
COR_FUNDO = (18, 18, 26)

VELOCIDADE_PLATAFORMA = 7
VELOCIDADE_BOLA = 6
RAIO_BOLA = 8
LARGURA_PLATAFORMA = 90
ALTURA_PLATAFORMA = 16
VELOCIDADE_UPGRADE = 3
VELOCIDADE_ESTRELA = 3

LINHAS = 5
COLUNAS = 8
LARGURA_CAIXA = 48
ALTURA_CAIXA = 20
ESPACO = 4
TOPO_GRADE = 60

# do azul (primeira fileira) ao vermelho (última), seguindo o arco-íris
CORES_LINHAS = [
    (40, 110, 255),   # azul
    (40, 200, 120),   # verde
    (240, 220, 40),   # amarelo
    (250, 140, 30),   # laranja
    (220, 40, 40),    # vermelho
]

# a partir da 2ª wave, cada wave é de uma cor só e ganha mais uma linha,
# seguindo o arco-íris até o azul; depois disso o tamanho trava e as
# waves seguintes são sempre brancas (ver criar_grade_caixinhas)
CORES_ONDAS = [
    (220, 40, 40),    # vermelho - wave 2
    (250, 140, 30),   # laranja - wave 3
    (240, 220, 40),   # amarelo - wave 4
    (40, 200, 120),   # verde - wave 5
    (40, 110, 255),   # azul - wave 6
]
COR_ONDA_FINAL = (235, 235, 235)  # branco - wave 7 em diante

LIMITE_BOLAS_PARA_DROP = 12  # com 12+ bolas em campo, upgrade azul para de dropar

# a chance de drop do upgrade azul vai caindo conforme a wave avança:
# wave 1 -> 1/4, wave 2 -> 1/5, wave 3 -> 1/6, wave 4 -> 1/7,
# wave 5 em diante -> trava em 1/8
def chance_drop_upgrade(onda):
    denominador = min(4 + (onda - 1), 8)
    return 1 / denominador

MUSICA_MENU = "audio/menu.mp3"
MUSICA_GAMEPLAY = "audio/theme.mp3"
VOLUME_INICIAL = 0.1
PASSO_VOLUME = 0.05  # 5% por toque em W/S ou seta cima/baixo

screen = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Breakout - colisão com máscara")
clock = pygame.time.Clock()
fonte = pygame.font.SysFont(None, 28)
fonte_titulo = pygame.font.SysFont(None, 76, bold=True)
fonte_especial = pygame.font.SysFont(None, 20)


# ---------------- fábricas de sprite ----------------
# Geramos os sprites por código (sem depender de imagens externas), o que
# deixa o jogo autocontido e facilita variar formas e cores.

def criar_sprite_circulo(raio, cor):
    diametro = raio * 2
    surf = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
    pygame.draw.circle(surf, cor, (raio, raio), raio)
    return surf


def criar_sprite_hexagono(largura, altura, cor):
    # formato não-retangular exigido pelo enunciado: um hexágono, com os
    # cantos "cortados" ficando de fato fora da máscara de colisão.
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    chanfro = altura // 2
    pontos = [
        (chanfro, 0), (largura - chanfro, 0),
        (largura, altura // 2),
        (largura - chanfro, altura), (chanfro, altura),
        (0, altura // 2),
    ]
    pygame.draw.polygon(surf, cor, pontos)
    borda = tuple(max(c - 50, 0) for c in cor)
    pygame.draw.polygon(surf, borda, pontos, width=2)
    return surf


def criar_sprite_upgrade(diametro):
    surf = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
    centro = diametro // 2
    pygame.draw.circle(surf, (30, 144, 255), (centro, centro), centro)
    pygame.draw.line(surf, (255, 255, 255), (centro, 3), (centro, diametro - 3), 2)
    pygame.draw.line(surf, (255, 255, 255), (3, centro), (diametro - 3, centro), 2)
    return surf


def criar_sprite_estrela(raio_externo, cor):
    raio_interno = raio_externo * 0.45
    diametro = raio_externo * 2
    surf = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
    pontos = []
    for i in range(10):
        raio = raio_externo if i % 2 == 0 else raio_interno
        angulo = math.pi / 2 + i * math.pi / 5
        x = raio_externo + raio * math.cos(angulo)
        y = raio_externo - raio * math.sin(angulo)
        pontos.append((x, y))
    pygame.draw.polygon(surf, cor, pontos)
    return surf


def checar_colisao(a, b):
    offset = (b.coord[0] - a.coord[0], b.coord[1] - a.coord[1])
    return a.mask.overlap(b.mask, offset) is not None


def checar_colisao_retangular(a, b):
    # colisão por bounding box: usada só para "pegar" itens de coleta
    # (upgrade e estrela), onde precisão pixel a pixel deixaria a captura
    # frustrante — formas com bastante vão vazio (como a estrela) fazem a
    # máscara falhar mesmo quando visualmente encostou na plataforma
    rect_a = a.sprite.get_rect(topleft=a.coord)
    rect_b = b.sprite.get_rect(topleft=b.coord)
    return rect_a.colliderect(rect_b)


# ---------------- classes do jogo ----------------

class obj(ABC):
    def __init__(self, sprite, coord):
        self.sprite = sprite
        self.mask = pygame.mask.from_surface(sprite)
        self.coord = list(coord)  # lista pra poder alterar x/y in-place

    def draw(self, screen):
        screen.blit(self.sprite, self.coord)

    @abstractmethod
    def lidar_colisao(self, outro):
        pass


class Bola(obj):
    def __init__(self, coord, cor=(235, 235, 235)):
        super().__init__(criar_sprite_circulo(RAIO_BOLA, cor), coord)
        angulo = random.uniform(-0.6, 0.6)
        self.vel = [VELOCIDADE_BOLA * math.sin(angulo), -VELOCIDADE_BOLA * math.cos(angulo)]

    def mover(self):
        self.coord[0] += self.vel[0]
        self.coord[1] += self.vel[1]

        # paredes não são "objetos" do jogo, então tratamos aqui mesmo,
        # sem passar pelo Collider
        largura_sprite = self.sprite.get_width()
        if self.coord[0] <= 0 or self.coord[0] + largura_sprite >= LARGURA:
            self.vel[0] *= -1
            self.coord[0] = max(0, min(self.coord[0], LARGURA - largura_sprite))
        if self.coord[1] <= 0:
            self.vel[1] *= -1
            self.coord[1] = 0

    def lidar_colisao(self, outro):
        Collider().colidir(self, outro)


class Plataforma(obj):
    def __init__(self, coord):
        sprite = pygame.Surface((LARGURA_PLATAFORMA, ALTURA_PLATAFORMA), pygame.SRCALPHA)
        pygame.draw.rect(sprite, (235, 235, 235), sprite.get_rect(), border_radius=6)
        super().__init__(sprite, coord)

    def mover(self, teclas):
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            self.coord[0] -= VELOCIDADE_PLATAFORMA
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            self.coord[0] += VELOCIDADE_PLATAFORMA
        self.coord[0] = max(0, min(self.coord[0], LARGURA - self.sprite.get_width()))

    def lidar_colisao(self, outro):
        # quem bate na plataforma é sempre outro objeto (bola ou upgrade),
        # então repassamos ao Collider com a ordem (outro, self)
        Collider().colidir(outro, self)


class Caixinha(obj):
    def __init__(self, coord, cor):
        super().__init__(criar_sprite_hexagono(LARGURA_CAIXA, ALTURA_CAIXA, cor), coord)
        self.quebrada = False

    def quebrar(self):
        self.quebrada = True

    def lidar_colisao(self, outro):
        pass  # a caixinha é passiva: só reage quando a bola bate nela


class Upgrade(obj):
    def __init__(self, coord):
        super().__init__(criar_sprite_upgrade(16), coord)
        self.coletado = False

    def cair(self):
        self.coord[1] += VELOCIDADE_UPGRADE  # cai reto para baixo

    def lidar_colisao(self, outro):
        Collider().colidir(self, outro)


class EstrelaEspecial(obj):
    def __init__(self, coord):
        super().__init__(criar_sprite_estrela(12, (70, 230, 110)), coord)
        self.coletada = False

    def cair(self):
        self.coord[1] += VELOCIDADE_ESTRELA  # cai reto para baixo, igual ao upgrade normal

    def lidar_colisao(self, outro):
        Collider().colidir(self, outro)


# ---------------- estado do jogo ----------------

def criar_grade_caixinhas(onda):
    # wave 1: a grade original, multicolorida
    # waves 2 a 6: cor sólida seguindo o arco-íris, com +1 linha por wave
    # waves 7+: tamanho travado no da wave 6, sempre brancas
    if onda <= 1:
        linhas = LINHAS
        cor_por_linha = lambda linha: CORES_LINHAS[linha]
    elif onda - 2 < len(CORES_ONDAS):
        linhas = LINHAS + (onda - 1)
        cor_da_onda = CORES_ONDAS[onda - 2]
        cor_por_linha = lambda linha: cor_da_onda
    else:
        linhas = LINHAS + len(CORES_ONDAS)
        cor_por_linha = lambda linha: COR_ONDA_FINAL

    caixinhas = []
    largura_total = COLUNAS * (LARGURA_CAIXA + ESPACO) - ESPACO
    margem = (LARGURA - largura_total) // 2
    for linha in range(linhas):
        for coluna in range(COLUNAS):
            x = margem + coluna * (LARGURA_CAIXA + ESPACO)
            y = TOPO_GRADE + linha * (ALTURA_CAIXA + ESPACO)
            caixinhas.append(Caixinha([x, y], cor_por_linha(linha)))
    return caixinhas


def criar_bola_extra(plataforma_ref):
    # chamado pelo Collider quando o upgrade é pego na plataforma
    global bolas_extras_coletadas
    x = plataforma_ref.coord[0] + plataforma_ref.sprite.get_width() / 2 - RAIO_BOLA
    y = plataforma_ref.coord[1] - RAIO_BOLA * 2
    bolas.append(Bola([x, y]))
    bolas_extras_coletadas += 1


def coletar_especial():
    # chamado pelo Collider quando a estrela é pega na plataforma; só
    # deixa o jogador com o especial "no bolso" até ele usar (espaço)
    global especial_pronto
    especial_pronto = True


def ativar_especial():
    # cada bola em campo vira 3: a própria (mantém a direção) mais duas
    # novas, cada uma girada +-120° em torno da direção atual dela
    global especiais_usados
    novas = []
    for bola in bolas:
        angulo_atual = math.atan2(bola.vel[1], bola.vel[0])
        velocidade = math.hypot(bola.vel[0], bola.vel[1])
        for delta_graus in (120, -120):
            angulo = angulo_atual + math.radians(delta_graus)
            nova = Bola(list(bola.coord))
            nova.vel = [velocidade * math.cos(angulo), velocidade * math.sin(angulo)]
            novas.append(nova)
    bolas.extend(novas)
    especiais_usados += 1


def tocar_musica(caminho):
    # troca a faixa e já deixa tocando em loop infinito (-1); só deve ser
    # chamada nas transições de estado, nunca a cada quadro, senão a
    # música reinicia sem parar
    pygame.mixer.music.load(caminho)
    pygame.mixer.music.play(-1)


def ajustar_volume(delta):
    # o volume é uma propriedade do "canal" de música do pygame, não do
    # arquivo — continua valendo mesmo depois de trocar a faixa com
    # tocar_musica, então não precisa ser reaplicado a cada troca
    global volume
    volume = max(0.0, min(1.0, volume + delta))
    pygame.mixer.music.set_volume(volume)


def reiniciar_jogo():
    global plataforma, bolas, caixinhas, upgrades, score
    global bolas_extras_coletadas, tempo_inicio
    global estrela, especial_pronto, especiais_usados
    global onda
    plataforma = Plataforma([LARGURA / 2 - LARGURA_PLATAFORMA / 2, ALTURA - 40])
    bolas = [Bola([LARGURA / 2 - RAIO_BOLA, ALTURA - 70])]
    onda = 1
    caixinhas = criar_grade_caixinhas(onda)
    upgrades = []
    score = 0
    bolas_extras_coletadas = 0
    tempo_inicio = pygame.time.get_ticks()
    estrela = None
    especial_pronto = False
    especiais_usados = 0


# ---------------- telas de início e fim ----------------

def desenhar_tela_inicio():
    centro_titulo = (LARGURA / 2, ALTURA / 2 - 40)
    # contorno escuro atrás do texto pra dar mais destaque/contraste ao
    # título, já que a fonte ficou maior e em negrito
    sombra_titulo = fonte_titulo.render("BREAKOUT", True, (50, 35, 0))
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
        screen.blit(sombra_titulo, sombra_titulo.get_rect(
            center=(centro_titulo[0] + dx, centro_titulo[1] + dy)))
    titulo = fonte_titulo.render("BREAKOUT", True, (255, 215, 0))
    instrucao = fonte.render("Pressione qualquer tecla para começar", True, (190, 190, 190))
    controles = fonte_especial.render(
        "Setas ou A/D para mover — Espaço usa o especial — R encerra a partida", True, (170, 170, 170)
    )
    volume_info = fonte_especial.render(
        f"W/S ou ↑/↓ ajusta o volume — Volume: {round(volume * 100)}%", True, (170, 170, 170)
    )
    screen.blit(titulo, titulo.get_rect(center=centro_titulo))
    screen.blit(instrucao, instrucao.get_rect(center=(LARGURA / 2, ALTURA / 2 + 30)))
    screen.blit(controles, controles.get_rect(center=(LARGURA / 2, ALTURA / 2 + 65)))
    screen.blit(volume_info, volume_info.get_rect(center=(LARGURA / 2, ALTURA / 2 + 90)))


def formatar_tempo(segundos):
    if segundos < 60:
        return f"{segundos:.1f}s"
    minutos = int(segundos // 60)
    resto = segundos - minutos * 60
    return f"{minutos}m {resto:04.1f}s"


def desenhar_tela_fim():
    titulo = fonte_titulo.render("FIM DE JOGO", True, (220, 70, 70))
    linhas = [
        f"Pontos: {score}",
        f"Waves completas: {onda - 1}",
        f"Bolas extras coletadas: {bolas_extras_coletadas}",
        f"Especiais usados: {especiais_usados}",
        f"Tempo de jogo: {formatar_tempo(tempo_final)}",
        "",
        "Pressione qualquer tecla para voltar ao início",
    ]
    screen.blit(titulo, titulo.get_rect(center=(LARGURA / 2, ALTURA / 2 - 110)))
    for i, linha in enumerate(linhas):
        if (i==0): 
            cor = (230, 230, 0);
        elif (i==1):
                    cor = (230, 0, 50);
        elif (i==2):
            cor = (30, 144, 255);
        elif (i==3):
                    cor = (0, 230, 0);
        else:
            cor = (190, 190, 190);
        texto = fonte.render(linha, True, cor)
        screen.blit(texto, texto.get_rect(center=(LARGURA / 2, ALTURA / 2 - 30 + i * 32)))


# ---------------- loop principal ----------------
# estados possíveis: "inicio" (tela de título), "jogando", "fim" (game over)

estado = "inicio"
tempo_final = 0
bolas_extras_coletadas = 0
score = 0
estrela = None
especial_pronto = False
especiais_usados = 0
onda = 1

running = True
volume = VOLUME_INICIAL
pygame.mixer.music.set_volume(volume)
tocar_musica(MUSICA_MENU)  # tela inicial começa com a música do menu
while running:
    ## input
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP):
                ajustar_volume(PASSO_VOLUME)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                ajustar_volume(-PASSO_VOLUME)
            elif estado == "inicio":
                reiniciar_jogo()
                estado = "jogando"
                tocar_musica(MUSICA_GAMEPLAY)
            elif estado == "jogando" and event.key == pygame.K_r:
                # R agora força o game over em vez de reiniciar, assim o
                # jogador não perde o progresso (score, wave etc.) — o
                # estado fica igual ao de quando as bolas somem sozinhas.
                tempo_final = (pygame.time.get_ticks() - tempo_inicio) / 1000
                estado = "fim"
            elif estado == "fim":
                estado = "inicio"
                tocar_musica(MUSICA_MENU)
            elif estado == "jogando" and event.key == pygame.K_SPACE and especial_pronto:
                ativar_especial()
                especial_pronto = False

    if not running:
        break  # sai antes de tocar na tela: evita "display Surface quit"

    ## atualização (só roda de fato durante a partida)
    if estado == "jogando":
        teclas = pygame.key.get_pressed()
        plataforma.mover(teclas)

        for bola in bolas:
            bola.mover()

            if checar_colisao(bola, plataforma):
                bola.lidar_colisao(plataforma)

            for caixinha in caixinhas:
                if not caixinha.quebrada and checar_colisao(bola, caixinha):
                    bola.lidar_colisao(caixinha)
                    break  # uma caixinha por bola já basta em cada quadro

        # bolinha que passou da plataforma sai de jogo; o game over só
        # acontece quando não sobra nenhuma (upgrade dá bolas extras)
        bolas = [bola for bola in bolas if bola.coord[1] <= ALTURA]

        # caixinhas quebradas nesse quadro: somam pontos e podem soltar upgrade
        for caixinha in caixinhas[:]:
            if caixinha.quebrada:
                caixinhas.remove(caixinha)
                score += 10
                # com muita bola em campo, o drop do upgrade azul trava
                # (senão o jogo enche de bolinhas); a estrela não é afetada
                if len(bolas) < LIMITE_BOLAS_PARA_DROP and random.random() < chance_drop_upgrade(onda):
                    upgrades.append(Upgrade(list(caixinha.coord)))

        for upgrade in upgrades[:]:
            upgrade.cair()
            if checar_colisao_retangular(upgrade, plataforma):
                upgrade.lidar_colisao(plataforma)
            if upgrade.coletado or upgrade.coord[1] > ALTURA:
                upgrades.remove(upgrade)

        # todas as caixinhas quebradas: avança pra próxima wave
        if not caixinhas:
            onda += 1
            caixinhas = criar_grade_caixinhas(onda)
            # só solta uma estrela nova se não houver outra caindo, não
            # houver uma já coletada esperando pra ser usada, e o campo
            # não estiver cheio de bolas (mesma trava do upgrade azul;
            # um especial já coletado continua podendo ser acionado normalmente)
            if estrela is None and not especial_pronto and len(bolas) < LIMITE_BOLAS_PARA_DROP:
                estrela = EstrelaEspecial([LARGURA / 2 - 12, TOPO_GRADE])

        if estrela is not None:
            estrela.cair()
            if checar_colisao_retangular(estrela, plataforma):
                estrela.lidar_colisao(plataforma)
            if estrela.coletada or estrela.coord[1] > ALTURA:
                estrela = None

        if not bolas:
            tempo_final = (pygame.time.get_ticks() - tempo_inicio) / 1000
            estado = "fim"

    ## desenho

    screen.fill(COR_FUNDO)

    if estado == "inicio":
        desenhar_tela_inicio()
    elif estado == "jogando":
        plataforma.draw(screen)
        for caixinha in caixinhas:
            caixinha.draw(screen)
        for upgrade in upgrades:
            upgrade.draw(screen)
        if estrela is not None:
            estrela.draw(screen)
        for bola in bolas:
            bola.draw(screen)

        texto = fonte.render(f"Pontos: {score}   Wave: {onda}", True, (240, 240, 240))
        screen.blit(texto, (10, 10))

        vol_texto = fonte_especial.render(f"Volume: {round(volume * 100)}%", True, (170, 170, 170))
        screen.blit(vol_texto, vol_texto.get_rect(topright=(LARGURA - 10, 12)))

        if especial_pronto:
            aviso = fonte_especial.render("aperte espaço para usar o especial", True, (70, 230, 110))
            screen.blit(aviso, (10, 34))
    elif estado == "fim":
        desenhar_tela_fim()

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()