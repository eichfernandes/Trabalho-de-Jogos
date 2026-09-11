import pygame
import math
import random
from abc import ABC, abstractmethod
from util import EventHandler, circle_collistiion, load_sprite, scale_value, muzzle_position
import arena
from bullet import StraightBullet


class Player:

    SPEED = 220  # pixels / segundo, velocidade de andar pelo mapa
    HIT_FLASH_DURATION = 0.2  # duração do flash de dano em segundos

    def __init__(self, pos, shoot_sounds=None):
        self.pos = pygame.Vector2(pos)
        self.angle = 0            # graus, direção que o boneco está olhando (mouse)
        self.radius = scale_value(16)  # raio de colisão
        self.max_health = 100
        self.health = self.max_health
        self.shoot_sounds = shoot_sounds or {}  # dicionário com sons de disparo
        self.state = PistolState(self)
        self.hit_time = 0  # tempo desde o último dano
        self.heal_time = 0  # tempo desde a última cura
        self.mouse_pressed_last_frame = False  # rastreia estado do mouse para click-to-fire

    def update(self, dt, mouse_world_pos, move_dir, mouse_pressed=False):
        # aponta pro mouse
        direction = mouse_world_pos - self.pos
        if direction.length_squared() > 0:
            self.angle = math.degrees(math.atan2(direction.y, direction.x))

        # anda pelo mapa (WASD / setas), respeitando as paredes da arena
        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()
            self.pos += move_dir * self.SPEED * dt
            self.pos = arena.resolve_wall_collision(self.pos, self.radius)

        self.state.update(dt)
        self.hit_time -= dt  # reduz o contador de tempo do flash de dano
        self.heal_time -= dt  # reduz o contador de tempo do flash de cura
        self.mouse_pressed_last_frame = mouse_pressed  # rastreia estado do mouse para próximo frame

    def draw(self, screen, offset):
        self.state.draw(screen, offset)

    def shoot(self):
        self.state.shoot()

    def pickup(self, items):
        # procura por um item próximo o suficiente e coleta o primeiro encontrado
        for item in items:
            if circle_collistiion(self.pos, self.radius + 8, item.pos, item.radius):
                item.apply(self)
                break

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)
        self.register_heal()

    def take_damage(self, dmg):
        self.register_hit()
        self.health -= dmg
        if self.health <= 0:
            self.health = 0
            EventHandler().notify("PlayerDied", self)

    def register_hit(self):
        self.hit_time = self.HIT_FLASH_DURATION

    def register_heal(self):
        self.heal_time = self.HIT_FLASH_DURATION

    def get_hit_flash_alpha(self):
        """Retorna o alpha (0-255) para o flash de dano"""
        if self.hit_time <= 0:
            return 0
        # fade out rápido: começa em 255 e vai para 0
        progress = 1.0 - (self.hit_time / self.HIT_FLASH_DURATION)
        return int(255 * (1.0 - progress))  # desvanece rapidamente

    def get_heal_flash_alpha(self):
        """Retorna o alpha (0-255) para o flash de cura"""
        if self.heal_time <= 0:
            return 0
        # fade out rápido: começa em 255 e vai para 0
        progress = 1.0 - (self.heal_time / self.HIT_FLASH_DURATION)
        return int(255 * (1.0 - progress))  # desvanece rapidamente

    def change_state(self, new_state):
        self.state.delete()
        self.state = new_state(self)


class PlayerState(ABC):

    # Sprite é comum à classe estado (triângulo verde = pistola, cor muda por estado)
    sprite = load_sprite("images/player/pistol.png", (80, 80))
    ammo = None  # None = infinito (pistola). Metralhadora/escopeta sobrescrevem no __init__.

    # distância (a partir do centro do player) na direção que ele está mirando
    # onde a bala nasce -- pra sair perto do bico da arma em vez do meio do boneco
    MUZZLE_OFFSET = scale_value(28)

    def __init__(self, player):
        self.P = player
        self.cooldown = 0

    def update(self, dt):
        if self.cooldown > 0:
            self.cooldown -= dt

    def draw(self, screen, offset):
        rotated = pygame.transform.rotate(self.sprite, -self.P.angle)
        rect = rotated.get_rect(center=self.P.pos - offset)
        screen.blit(rotated, rect)

    def delete(self):
        pass  # se precisar apagar algo na mudança de estados

    def is_click_to_fire(self):
        # retorna True para armas que só atiram ao clicar (Pistol, Shotgun)
        # retorna False para armas que atiram enquanto pressionando (MachineGun)
        return False

    @abstractmethod
    def shoot(self):
        pass


class PistolState(PlayerState):
    # Pistola: arma inicial, munição infinita, tiro lento (mas não exagerado)

    sprite = load_sprite("images/player/pistol.png", (80, 80))

    fire_rate = 0.2  # segundos entre tiros

    def is_click_to_fire(self):
        return True

    def shoot(self):
        if self.cooldown <= 0:
            self.cooldown = self.fire_rate
            # toca som de disparo da pistola
            if "pistol" in self.P.shoot_sounds:
                self.P.shoot_sounds["pistol"].play()
            dmg = random.randint(20, 40)
            bullet = StraightBullet(muzzle_position(self.P.pos, self.P.angle, self.MUZZLE_OFFSET),
                                     self.P.angle, speed=520, radius=5,
                                     life_time=1.5, damage=dmg, owner="player")
            EventHandler().notify("SpawnObj", bullet)


class MachineGunState(PlayerState):
    # Metralhadora: 150 balas, cadência bem rápida (automática), dano variável

    sprite = load_sprite("images/player/machinegun.png", (80, 80))

    fire_rate = 0.09
    max_ammo = 150

    def __init__(self, player):
        super().__init__(player)
        self.ammo = 150

    def shoot(self):
        if self.cooldown <= 0 and self.ammo > 0:
            self.cooldown = self.fire_rate
            self.ammo -= 1
            # toca som de disparo da metralhadora a cada tiro
            if "machinegun" in self.P.shoot_sounds:
                self.P.shoot_sounds["machinegun"].play()
            dmg = random.randint(10, 60)
            bullet = StraightBullet(muzzle_position(self.P.pos, self.P.angle, self.MUZZLE_OFFSET),
                                     self.P.angle, speed=650, radius=4,
                                     life_time=1.2, damage=dmg, owner="player")
            EventHandler().notify("SpawnObj", bullet)
            if self.ammo <= 0:
                self.P.change_state(PistolState)  # acabou a munição, volta pra pistola


class ShotgunState(PlayerState):
    # Escopeta: 8 cartuchos, dispara 3 balas em cone, dano alto por bala

    sprite = load_sprite("images/player/shotgun.png", (80, 80))

    fire_rate = 1.7
    SPREAD_ANGLE = 14  # graus de abertura do cone entre cada bala
    max_ammo = 12

    def __init__(self, player):
        super().__init__(player)
        self.ammo = 12

    def is_click_to_fire(self):
        return True

    def shoot(self):
        if self.cooldown <= 0 and self.ammo > 0:
            self.cooldown = self.fire_rate
            self.ammo -= 1
            # toca som de disparo da shotgun uma vez por click
            if "shotgun" in self.P.shoot_sounds:
                self.P.shoot_sounds["shotgun"].play()
            for spread in (-self.SPREAD_ANGLE, 0, self.SPREAD_ANGLE):
                dmg = random.randint(80, 150)
                bullet = StraightBullet(muzzle_position(self.P.pos, self.P.angle, self.MUZZLE_OFFSET),
                                         self.P.angle + spread, speed=560, radius=6,
                                         life_time=0.5, damage=dmg, owner="player")
                EventHandler().notify("SpawnObj", bullet)
            if self.ammo <= 0:
                self.P.change_state(PistolState)  # acabou a munição, volta pra pistola