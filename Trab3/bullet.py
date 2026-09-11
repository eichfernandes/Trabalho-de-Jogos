import pygame
from abc import ABC, abstractmethod
from util import colored_sprite, EventHandler, scale_value
import arena

import math

def rotate(pos, angle, axis = (0,0)):
    angle = math.radians(angle)
    x, y = pos
    ax, ay = axis

    # Translate so axis is the origin
    x -= ax
    y -= ay

    # Rotate
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    rx = x * cos_a - y * sin_a
    ry = x * sin_a + y * cos_a

    # Translate back
    return rx + ax, ry + ay

class Bullet (ABC):

    def __init__(self, pos, angle=0, speed=400, radius=6, life_time=2,
                 damage=0, color=(255, 255, 0), owner=None):
        self.pos = pygame.Vector2(pos)
        self.origin = pygame.Vector2(pos)
        self.life_time = life_time
        self.angle = angle          # graus
        self.speed = speed          # pixels / segundo
        self.elapsed = 0
        self.traveled = 0
        self.radius = scale_value(radius)
        self.damage = damage        # dano já sorteado (range definido em quem cria a bala)
        self.owner = owner          # "player" ou "enemy", usado na checagem de colisão
        self.alive = True

        # ---- SPRITE: bolinha amarela representando o projétil ----
        # TODO: trocar por sprite -> pygame.image.load("images/bullets/bullet.png").convert_alpha()
        self.sprite = colored_sprite(color, (self.radius*2, self.radius*2))

    def update(self, dt):
        self.elapsed += dt
        if self.life_time and self.elapsed >= self.life_time:
            self.destroy()
            return

        old_pos = pygame.Vector2(self.pos)
        self.traveled += self.speed * dt
        self.pos = pygame.Vector2(rotate(self.move(), self.angle)) + self.origin

        if not arena.line_clear(old_pos, self.pos):
            self.destroy()  # bateu numa parede (portas são só um vão, então passam livre)

    def draw(self, screen, offset=pygame.Vector2(0, 0)):
        screen.blit(self.sprite, self.pos - offset - pygame.Vector2(self.radius, self.radius))

    @abstractmethod
    def move(self):
        pass

    def destroy(self): # pede para deletar
        if self.alive:
            self.alive = False
            EventHandler().notify("DestroyObj", self) # avisa o mundo que saiu da tela


class StraightBullet(Bullet):
    # bala reta simples: anda em linha reta na direção "angle" a partir da origem.
    # usada tanto pelo jogador (pistola/metralhadora/escopeta) quanto pelos inimigos.

    def move(self):
        return pygame.Vector2(self.traveled, 0)