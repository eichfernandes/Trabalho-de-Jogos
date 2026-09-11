import pygame
import math
import random

# ---- ZOOM GERAL DO JOGO ----
# Fator usado para aumentar proporcionalmente o tamanho de sprites e raios de
# colisão de todo o jogo (o "zoom"). Alterar só esse número já reescala tudo
# que usa scale_value/scale_size/load_sprite.
SCALE = 1.5


def scale_value(value):
    return int(round(value * SCALE))


def scale_size(size):
    return (scale_value(size[0]), scale_value(size[1]))


_sprite_cache = { }

def load_sprite(path, size):
    # Carrega (e cacheia) uma imagem já redimensionada com o SCALE do jogo.
    # "size" é o tamanho BASE (sem escala) desejado pro sprite.
    key = (path, size)
    if key not in _sprite_cache:
        img = pygame.image.load(path)
        _sprite_cache[key] = pygame.transform.scale(img, scale_size(size))
    return _sprite_cache[key]


def singleton(class_):
    instances = { } 
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)	# cria se ainda não existe
        return instances[class_] # armazena para mais tarde
    return getinstance # devolve a instância unica

@singleton
class EventHandler:
    def __init__(self):
        self.observers = { }  # passa a ser um dicionário onde chave é o tipo de evento

    def subscribe(self, type, callback): # passa o tipo de evento também
        if type not in self.observers: # caso não exista ainda
            self.observers[type] = [ ]  # cria um novo tipo de evento para notificar
        self.observers[type].append(callback) # inscreve a chamada ao evento

    def notify(self, type, data=None):
        if type in self.observers: # checa se tem eventos desse tipo
            for o in self.observers[type]: # para todos os inscritos nele
                o(data) # avise que o evento ocorreu


def colored_sprite(color, size=(32, 32), circle = True):
    sprite = pygame.Surface(size)
    if circle:
        sprite.set_colorkey((0,0,0))
        pygame.draw.circle(sprite, color, (size[0]//2, size[1]//2), size[0]//2)
    else:
        sprite.fill(color)
    return sprite


def circle_collistiion (p1, r1, p2, r2):
    euc_distance = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**(1/2)
    return  euc_distance <= r1 + r2

# alias com o nome escrito corretamente, caso prefiram usar
circle_collision = circle_collistiion


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def muzzle_position(pos, angle, distance):
    # devolve um ponto a "distance" pixels de "pos", na direção "angle" (graus) --
    # usado pra fazer a bala nascer perto da ponta da arma em vez do centro
    # exato de quem atira (player ou inimigo)
    return pygame.Vector2(pos) + pygame.Vector2(distance, 0).rotate(angle)


def random_point_around(center, min_r, max_r):
    # Sorteia um ponto a uma distância entre min_r e max_r de "center", em direção aleatória.
    # Usado para spawnar inimigos fora da tela, vindos de qualquer direção.
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(min_r, max_r)
    return pygame.Vector2(center.x + math.cos(angle) * r, center.y + math.sin(angle) * r)