import pygame
import math
import random
from abc import ABC, abstractmethod
from util import EventHandler, load_sprite, scale_value, muzzle_position
from bullet import StraightBullet
import arena


class Enemy:
    # Inimigo "normal" (pistola). Também é a classe base das variações
    # (ShotgunEnemy, MachineGunEnemy), que reaproveitam os estados de
    # movimento (Approach/Orbit/Dead) e só trocam o sprite, o tiro e o drop.

    SPEED = 110          # pixels / segundo, velocidade de aproximação
    ORBIT_SPEED = 90     # pixels / segundo, velocidade ao rodear o jogador
    SHOOT_RANGE = 260    # distância a partir da qual ele já não precisa se aproximar mais
    MAX_HEALTH = 100

    SPRITE_PATH = "images/enemy/pistol.png"  # sprite usado nos estados Approach/Orbit
    HEAL_DROP_CHANCE = 1 / 6                 # chance de dropar cura, igual pra todos
    HIT_FLASH_DURATION = 0.2                 # duração do flash em segundos

    # distância (a partir do centro do inimigo) na direção que ele está mirando
    # onde a bala nasce -- mesma ideia do MUZZLE_OFFSET do player
    MUZZLE_OFFSET = scale_value(22)

    # dicionário com os sons de disparo (mesmo dict usado pelo player), setado
    # pela main.py logo na inicialização -- ver Enemy.shoot_sounds = shoot_sounds
    shoot_sounds = {}

    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.angle = 0
        self.radius = scale_value(18)  # raio de colisão
        self.health = self.MAX_HEALTH
        self.state = ApproachState(self)
        self.hit_time = 0  # tempo desde o último acerto

        # atira independente da distância/estado, por isso o cooldown fica no Enemy
        self.shoot_cooldown = random.uniform(2, 4)

    def update(self, dt, player):
        self.state.update(dt, player)
        self._update_shooting(dt, player)
        self.hit_time -= dt  # reduz o contador de tempo do flash

    def _update_shooting(self, dt, player):
        if not self.is_alive():
            return
        self.shoot_cooldown -= dt
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = random.uniform(2, 4)
            if arena.line_clear(self.pos, player.pos):
                self._fire(player)

    def _fire(self, player):
        # tiro padrão: uma bala reta simples (pistola)
        if "pistol" in self.shoot_sounds:
            self.shoot_sounds["pistol"].play()
        dmg = random.randint(15, 40)
        bullet = StraightBullet(muzzle_position(self.pos, self.angle, self.MUZZLE_OFFSET),
                                 self.angle, speed=320, radius=6,
                                 life_time=2.5, damage=dmg, owner="enemy")
        EventHandler().notify("SpawnObj", bullet)

    def get_drop(self):
        # inimigo normal: só pode dropar cura
        if random.random() < self.HEAL_DROP_CHANCE:
            return "heal"
        return None

    def draw(self, screen, offset):
        self.state.draw(screen, offset)

    def take_damage(self, dmg):
        if not self.is_alive():
            return
        self.register_hit()
        self.health -= dmg
        if self.health <= 0:
            self.health = 0
            self.change_state(DeadState)
            EventHandler().notify("EnemyDied", self)

    def register_hit(self):
        self.hit_time = self.HIT_FLASH_DURATION

    def get_hit_flash_alpha(self):
        """Retorna o alpha (0-255) para o flash de acerto"""
        if self.hit_time <= 0:
            return 0
        # fade out rápido: começa em 255 e vai para 0
        progress = 1.0 - (self.hit_time / self.HIT_FLASH_DURATION)
        return int(255 * (1.0 - progress))  # desvanece rapidamente

    def is_alive(self):
        return not isinstance(self.state, DeadState)

    def get_speed_multiplier(self, player):
        # aumenta velocidade se estiver a mais de 1500 pixels de distância
        dist = (self.pos - player.pos).length()
        if dist > 1500:
            return 2.0  # velocidade dobrada
        return 1.0

    def change_state(self, new_state):
        self.state.delete()
        self.state = new_state(self)


class ShotgunEnemy(Enemy):
    # Funciona como o player na escopeta: 3 balas em cone por disparo, só que
    # com dano mais baixo. É o único inimigo que pode dropar a escopeta.

    SPRITE_PATH = "images/enemy/shotgun.png"
    SPREAD_ANGLE = 14  # graus de abertura do cone entre cada bala

    SHOTGUN_DROP_CHANCE = 0.7

    def _fire(self, player):
        if "shotgun" in self.shoot_sounds:
            self.shoot_sounds["shotgun"].play()
        for spread in (-self.SPREAD_ANGLE, 0, self.SPREAD_ANGLE):
            dmg = random.randint(35, 60)
            bullet = StraightBullet(muzzle_position(self.pos, self.angle, self.MUZZLE_OFFSET),
                                     self.angle + spread, speed=520, radius=6,
                                     life_time=1, damage=dmg, owner="enemy")
            EventHandler().notify("SpawnObj", bullet)

    def get_drop(self):
        if random.random() < self.SHOTGUN_DROP_CHANCE:
            return "shotgun"
        if random.random() < self.HEAL_DROP_CHANCE:
            return "heal"
        return None


class MachineGunEnemy(Enemy):
    # Funciona como o player na metralhadora, mas em rajadas: atira uma
    # sequência rápida de balas e depois pausa por um tempo (igual o
    # shoot_cooldown normal) antes de soltar a próxima rajada.
    # É o único inimigo que pode dropar a metralhadora.

    SPRITE_PATH = "images/enemy/machinegun.png"

    BURST_SIZE = 6            # balas por rajada
    BURST_FIRE_RATE = 0.08    # segundos entre balas dentro da rajada

    MACHINEGUN_DROP_CHANCE = 0.7

    def __init__(self, pos):
        super().__init__(pos)
        self.burst_remaining = 0
        self.burst_cooldown = 0

    def _update_shooting(self, dt, player):
        if not self.is_alive():
            return

        if self.burst_remaining > 0:
            # já está no meio de uma rajada: só cuida do intervalo entre balas
            self.burst_cooldown -= dt
            if self.burst_cooldown <= 0:
                self.burst_cooldown = self.BURST_FIRE_RATE
                self.burst_remaining -= 1
                if arena.line_clear(self.pos, player.pos):
                    if "machinegun" in self.shoot_sounds:
                        self.shoot_sounds["machinegun"].play()
                    dmg = random.randint(10, 35)
                    bullet = StraightBullet(muzzle_position(self.pos, self.angle, self.MUZZLE_OFFSET),
                                             self.angle, speed=600, radius=4,
                                             life_time=1.2, damage=dmg, owner="enemy")
                    EventHandler().notify("SpawnObj", bullet)
            return

        # fora de rajada: espera o cooldown normal (a "pausa") antes de iniciar outra
        self.shoot_cooldown -= dt
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = random.uniform(2, 4)
            self.burst_remaining = self.BURST_SIZE
            self.burst_cooldown = 0

    def get_drop(self):
        if random.random() < self.MACHINEGUN_DROP_CHANCE:
            return "machinegun"
        if random.random() < self.HEAL_DROP_CHANCE:
            return "heal"
        return None


def random_enemy(pos):
    # Sorteia o tipo de inimigo a ser criado: 4/6 normal, 1/6 escopeta, 1/6 metralhadora.
    roll = random.random()
    if roll < 1 / 6:
        return ShotgunEnemy(pos)
    elif roll < 2 / 6:
        return MachineGunEnemy(pos)
    else:
        return Enemy(pos)


class EnemyState(ABC):

    def __init__(self, enemy):
        self.E = enemy

    def _sprite(self):
        # cada tipo de inimigo (Enemy.SPRITE_PATH) tem seu próprio sprite,
        # carregado e cacheado sob demanda por load_sprite
        return load_sprite(self.E.SPRITE_PATH, (80, 80))

    def draw(self, screen, offset):
        # desenhar contorno branco de flash por baixo do sprite
        alpha = self.E.get_hit_flash_alpha()
        if alpha > 0:
            flash_surf = pygame.Surface((self.E.radius * 2 + 6, self.E.radius * 2 + 6))
            flash_surf.set_colorkey((0, 0, 0))
            flash_surf.fill((0, 0, 0))
            pygame.draw.circle(flash_surf, (255, 255, 255), (self.E.radius + 3, self.E.radius + 3), self.E.radius + 3, 3)
            flash_surf.set_alpha(alpha)
            screen_pos = self.E.pos - offset - pygame.Vector2(self.E.radius + 3, self.E.radius + 3)
            screen.blit(flash_surf, screen_pos)
        
        # desenhar sprite do inimigo por cima
        rotated = pygame.transform.rotate(self._sprite(), -self.E.angle)
        rect = rotated.get_rect(center=self.E.pos - offset)
        screen.blit(rotated, rect)

    def delete(self):
        pass  # se precisar apagar algo na mudança de estados

    def _face_point(self, point):
        direction = pygame.Vector2(point) - self.E.pos
        if direction.length_squared() > 0:
            self.E.angle = math.degrees(math.atan2(direction.y, direction.x))
        return direction

    def _navigate_target(self, player):
        # Devolve (ponto_alvo, linha_de_visão_livre): o próprio jogador, se
        # o inimigo já enxerga ele (mesmo atravessando uma porta aberta), ou
        # a próxima porta no caminho até ele -- assim o inimigo entende como
        # atravessar a arena sala por sala até alcançar o jogador.
        if arena.line_clear(self.E.pos, player.pos):
            return player.pos, True
        return arena.next_waypoint(self.E.pos, player.pos), False

    @abstractmethod
    def update(self, dt, player):
        pass


class ApproachState(EnemyState):
    # Inimigo se aproximando do jogador até chegar numa distância que já dá pra atirar bem.
    # (o tiro em si acontece sempre, independente do estado - ver Enemy._update_shooting)

    def update(self, dt, player):
        E = self.E
        target, los_clear = self._navigate_target(player)
        direction = self._face_point(target)

        # só passa a rodear o jogador se realmente enxergar ele e já estiver perto;
        # do contrário, segue perseguindo o alvo atual (jogador ou porta no caminho)
        if los_clear and (player.pos - E.pos).length() <= E.SHOOT_RANGE:
            E.change_state(OrbitState)
            return

        if direction.length_squared() > 0:
            direction = direction.normalize()
        speed_mult = E.get_speed_multiplier(player)
        E.pos += direction * E.SPEED * speed_mult * dt
        E.pos = arena.resolve_wall_collision(E.pos, E.radius)


class OrbitState(EnemyState):
    # Já está numa distância boa: não precisa mais se aproximar, fica rodeando o jogador
    # (nunca parado) enquanto continua atirando. O movimento tem variações aleatórias
    # (velocidade, leve zigue-zague e trocas ocasionais de sentido) pra não parecer um
    # círculo perfeito e mecânico.

    def __init__(self, enemy):
        super().__init__(enemy)
        self.orbit_dir = random.choice((-1, 1))  # sentido horário ou anti-horário
        self.time = 0
        self.wobble_freq = random.uniform(0.6, 1.6)   # velocidade da "respiração" do movimento
        self.wobble_phase = random.uniform(0, 2 * math.pi)
        self.dir_change_timer = random.uniform(2, 5)  # de vez em quando troca o sentido do giro

    def update(self, dt, player):
        E = self.E
        self.time += dt

        # se a linha de visão pro jogador foi bloqueada (ele saiu por uma porta,
        # por exemplo), volta a persegui-lo navegando pela arena
        if not arena.line_clear(E.pos, player.pos):
            E.change_state(ApproachState)
            return

        direction = self._face_point(player.pos)
        dist = direction.length()

        # se o jogador se afastar demais, volta a perseguir
        if dist > E.SHOOT_RANGE * 1.3:
            E.change_state(ApproachState)
            return

        if dist > 0:
            direction = direction.normalize()

        # a cada alguns segundos existe a chance de inverter o sentido do giro,
        # quebrando o padrão de "só girar pra um lado"
        self.dir_change_timer -= dt
        if self.dir_change_timer <= 0:
            self.dir_change_timer = random.uniform(3, 6)
            if random.random() < 0.5:
                self.orbit_dir *= -1

        # velocidade tangencial varia suavemente com o tempo (em vez de ser constante)
        wobble = 0.55 + 0.45 * math.sin(self.time * self.wobble_freq + self.wobble_phase)
        tangent = pygame.Vector2(-direction.y, direction.x) * self.orbit_dir
        speed_mult = E.get_speed_multiplier(player)
        E.pos += tangent * E.ORBIT_SPEED * wobble * speed_mult * dt

        # um pouco de ruído aleatório pra tirar a "perfeição" do círculo
        jitter = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        E.pos += jitter * (E.ORBIT_SPEED * 0.2) * dt

        # pequena correção pra não se afastar nem colar demais no jogador
        if dist > E.SHOOT_RANGE:
            E.pos += direction * E.SPEED * 0.4 * dt
        elif dist < E.SHOOT_RANGE * 0.6:
            E.pos -= direction * E.SPEED * 0.4 * dt

        E.pos = arena.resolve_wall_collision(E.pos, E.radius)


class DeadState(EnemyState):
    # Inimigo morto: fica cinza parado, depois de 15s começa a sumir em fade-out
    # (o sprite de "morto" é o mesmo pra todos os tipos de inimigo)

    FADE_DELAY = 15     # segundos parado antes de começar a sumir
    FADE_DURATION = 2   # duração do fade-out

    def __init__(self, enemy):
        super().__init__(enemy)
        self.timer = 0
        self.alpha = 255

    def _sprite(self):
        return load_sprite("images/enemy/dead.png", (40, 40))

    def update(self, dt, player):
        self.timer += dt
        if self.timer > self.FADE_DELAY:
            fade_t = self.timer - self.FADE_DELAY
            self.alpha = max(0, 255 - int(255 * (fade_t / self.FADE_DURATION)))
            if self.alpha <= 0:
                EventHandler().notify("DestroyObj", self.E)

    def draw(self, screen, offset):
        sprite = self._sprite().copy()
        sprite.set_alpha(self.alpha)
        rotated = pygame.transform.rotate(sprite, -self.E.angle)
        rect = rotated.get_rect(center=self.E.pos - offset)
        screen.blit(rotated, rect)