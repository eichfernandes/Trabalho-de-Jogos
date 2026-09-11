import pygame
import random
from player import Player
from bullet import StraightBullet
from enemy import Enemy, random_enemy
from item import Item
from util import EventHandler, circle_collistiion
import arena

#inicialização

pygame.init()
WIDTH, HEIGHT = 1200, 700  # janela maior, pra acompanhar o zoom nos sprites
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hotline Survivors")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 26)
big_font = pygame.font.SysFont(None, 52)

# ---- volumes (ajuste manual aqui, valores de 0.0 a 1.0) ----
MUSIC_VOLUME = 1      # volume da música de fundo
SHOT_VOLUME = 0.6       # volume dos efeitos sonoros de tiro (player e inimigos)
CHANGE_GUN_VOLUME = 1 # volume do som de troca de arma (ao pegar item do chão)

# ---- sistema de música ----
pygame.mixer.init()
music_playlist = []
current_music_index = 0

def init_music_playlist():
    global music_playlist, current_music_index
    music_files = [
        "audios/musics/music01.mp3",
        "audios/musics/music02.mp3",
        "audios/musics/music03.mp3"
    ]
    music_playlist = music_files.copy()
    random.shuffle(music_playlist)
    current_music_index = 0
    # toca a primeira música da playlist
    pygame.mixer.music.load(music_playlist[current_music_index])
    pygame.mixer.music.set_volume(MUSIC_VOLUME)
    pygame.mixer.music.play()

# ---- carregamento de efeitos sonoros ----
shoot_sounds = {
    "pistol": pygame.mixer.Sound("audios/effects/pistol.mp3"),
    "machinegun": pygame.mixer.Sound("audios/effects/machinegun.mp3"),
    "shotgun": pygame.mixer.Sound("audios/effects/shotgun.mp3"),
    "change_gun": pygame.mixer.Sound("audios/effects/change_gun.mp3")
}
for _sound in shoot_sounds.values():
    _sound.set_volume(SHOT_VOLUME)
shoot_sounds["change_gun"].set_volume(CHANGE_GUN_VOLUME)

# inimigos usam o mesmo dicionário de sons de tiro que o player (ver enemy.py)
Enemy.shoot_sounds = shoot_sounds

# ---- estado geral do jogo ----
game_state = "menu"   # "menu" | "playing" | "gameover"
score = 0
best_score = 0         # melhor score da sessão aberta (não salva em arquivo)

player = None
objects = [ ]   # tudo que precisa ser desenhado (balas, inimigos, itens)
enemies = [ ]   # referência rápida só pros inimigos, pra contar quantos estão vivos

spawn_timer = 0
next_spawn = random.uniform(3, 5)

SPAWN_MIN_TIME = 3.0    # tempo mínimo entre spawns
SPAWN_MAX_TIME = 5.0    # tempo máximo entre spawns
MAX_ALIVE_ENEMIES = 6
INITIAL_ENEMIES = 3    # quantos já nascem assim que a partida começa


# funções auxiliares

def spawn_enemy_off_screen():
    # sorteia um ponto de spawn que esteja garantidamente fora da tela visível
    visible_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
    visible_rect.center = player.pos
    
    # calcula distância do jogador para cada spawn point
    spawn_with_dist = [(p, (p - player.pos).length()) for p in arena.SPAWN_POINTS]
    
    # filtra apenas os que estão fora da tela visível
    off_screen_spawns = [(p, d) for p, d in spawn_with_dist if not visible_rect.collidepoint(p)]
    
    # se não houver spawn points off-screen, algo está errado - usa qualquer um fora da tela
    if not off_screen_spawns:
        off_screen_spawns = spawn_with_dist
    
    # ordena por distância e pega os 3 mais próximos (entre os off-screen)
    off_screen_spawns.sort(key=lambda x: x[1])
    closest_3 = [p for p, _ in off_screen_spawns[:3]]
    
    # sorteia um dos candidates para spawn
    pos = pygame.Vector2(random.choice(closest_3))
    
    # adiciona pequena variação aleatória pra evitar inimigos stacados
    offset = pygame.Vector2(random.uniform(-80, 80), random.uniform(-80, 80))
    pos += offset
    
    EventHandler().notify("SpawnObj", random_enemy(pos))


def reset_game():
    global player, objects, enemies, score, spawn_timer, next_spawn, game_state, SPAWN_MIN_TIME, SPAWN_MAX_TIME
    player = Player(arena.PLAYER_START, shoot_sounds)
    objects = [ ]
    enemies = [ ]
    score = 0
    spawn_timer = 0
    SPAWN_MIN_TIME = 3.0
    SPAWN_MAX_TIME = 5.0
    game_state = "playing"
    
    # inicia a playlist de música
    init_music_playlist()

    # já nasce com alguns inimigos na partida, em vez de esperar o primeiro spawn
    for _ in range(INITIAL_ENEMIES):
        spawn_enemy_off_screen()


def on_destroy(obj):
    # variavel global é feio, mas serve como um exemplo
    if obj in objects:
        objects.remove(obj)
    if obj in enemies:
        enemies.remove(obj)


def on_spawn(obj):
    objects.append(obj)
    if isinstance(obj, Enemy):
        enemies.append(obj)


def on_enemy_died(enemy):
    global score, best_score, MAX_ALIVE_ENEMIES, SPAWN_MIN_TIME, SPAWN_MAX_TIME
    score += 1
    best_score = max(best_score, score)

    # aumenta o máximo de inimigos a cada 15 mortos, até o máximo de 12
    if score % 15 == 0 and MAX_ALIVE_ENEMIES < 12:
        MAX_ALIVE_ENEMIES += 1

    # diminui o tempo de spawn a cada 10 inimigos mortos
    if score % 10 == 0:
        if score >= 30:
            SPAWN_MIN_TIME = 0.5
            SPAWN_MAX_TIME = 2.5
        else:
            SPAWN_MIN_TIME = max(0.5, SPAWN_MIN_TIME - 0.5)
            SPAWN_MAX_TIME = max(2.5, SPAWN_MAX_TIME - 0.5)

    # cada tipo de inimigo decide seu próprio drop (ver Enemy.get_drop em enemy.py)
    kind = enemy.get_drop()
    if kind:
        EventHandler().notify("SpawnObj", Item(enemy.pos, kind))


def on_player_died(_player):
    global game_state
    game_state = "gameover"


#inscreve os métodos pros eventos do jogo
EventHandler().subscribe("DestroyObj", on_destroy)
EventHandler().subscribe("SpawnObj", on_spawn)
EventHandler().subscribe("EnemyDied", on_enemy_died)
EventHandler().subscribe("PlayerDied", on_player_died)


def spawn_enemies_if_needed(dt):
    global spawn_timer, next_spawn, SPAWN_MIN_TIME, SPAWN_MAX_TIME
    spawn_timer += dt
    alive_count = sum(1 for e in enemies if e.is_alive())

    if alive_count < MAX_ALIVE_ENEMIES and spawn_timer >= next_spawn:
        spawn_timer = 0
        next_spawn = random.uniform(SPAWN_MIN_TIME, SPAWN_MAX_TIME)
        spawn_enemy_off_screen()


def handle_collisions():
    bullets = [o for o in objects if isinstance(o, StraightBullet)]

    for b in bullets:
        if not b.alive:
            continue

        if b.owner == "player":
            for e in enemies:
                if e.is_alive() and circle_collistiion(b.pos, b.radius, e.pos, e.radius):
                    e.take_damage(b.damage)
                    b.destroy()
                    break

        elif b.owner == "enemy":
            if circle_collistiion(b.pos, b.radius, player.pos, player.radius):
                player.take_damage(b.damage)
                b.destroy()


def draw_button(rect, text):
    pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=10)
    pygame.draw.rect(screen, (220, 220, 220), rect, 2, border_radius=10)
    label = big_font.render(text, True, (255, 255, 255))
    screen.blit(label, label.get_rect(center=rect.center))


def draw_grid(offset):
    # só um chão simples pra dar noção de movimento no mapa "infinito"
    spacing = 100
    color = (45, 45, 55)
    start_x = -int(offset.x) % spacing
    start_y = -int(offset.y) % spacing
    for x in range(start_x, WIDTH, spacing):
        pygame.draw.line(screen, color, (x, 0), (x, HEIGHT))
    for y in range(start_y, HEIGHT, spacing):
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))


def draw_crosshair(pos):
    # mirinha verde que substitui o cursor do sistema durante o gameplay
    color = (0, 255, 0)
    size = 7
    gap = 3
    x, y = int(pos.x), int(pos.y)
    pygame.draw.line(screen, color, (x - size - gap, y), (x - gap, y), 3)
    pygame.draw.line(screen, color, (x + gap, y), (x + size + gap, y), 3)
    pygame.draw.line(screen, color, (x, y - size - gap), (x, y - gap), 3)
    pygame.draw.line(screen, color, (x, y + gap), (x, y + size + gap), 3)


button_rect = pygame.Rect(WIDTH // 2 - 110, HEIGHT // 2 - 30, 220, 64)

# loop principal

running = True
while running:
    dt = clock.tick(60) / 1000  # segundos desde o último frame
    mouse_screen_pos = pygame.Vector2(pygame.mouse.get_pos())

    # cursor do sistema escondido só durante o gameplay (a mirinha o substitui);
    # no menu/gameover o cursor normal volta pra dar pra clicar no botão
    pygame.mouse.set_visible(game_state != "playing")

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state in ("menu", "gameover") and button_rect.collidepoint(event.pos):
                reset_game()
        elif event.type == pygame.KEYDOWN:
            if game_state == "playing" and event.key == pygame.K_SPACE:
                items = [o for o in objects if isinstance(o, Item)]
                player.pickup(items)

    if game_state == "playing":
        # gerencia a playlist de música: passa para a próxima quando a atual termina
        if not pygame.mixer.music.get_busy():
            current_music_index = (current_music_index + 1) % len(music_playlist)
            pygame.mixer.music.load(music_playlist[current_music_index])
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play()
        
        offset = player.pos - pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        mouse_world_pos = mouse_screen_pos + offset

        keys = pygame.key.get_pressed()
        move_dir = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_dir.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_dir.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_dir.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_dir.x += 1

        mouse_pressed = pygame.mouse.get_pressed()[0]
        
        # lógica de shoot diferenciada ANTES de atualizar o player (para usar mouse_pressed_last_frame corretamente)
        if player.state.is_click_to_fire():
            # pistola/shotgun: só atira na transição (novo click)
            if mouse_pressed and not player.mouse_pressed_last_frame:
                player.shoot()
        else:
            # metralhadora: atira enquanto pressiona
            if mouse_pressed:
                player.shoot()
        
        player.update(dt, mouse_world_pos, move_dir, mouse_pressed)

        spawn_enemies_if_needed(dt)

        for e in enemies:
            e.update(dt, player)

        for o in objects:
            if isinstance(o, StraightBullet):
                o.update(dt)

        handle_collisions()

        # ---- desenho ----
        screen.fill((25, 25, 32))
        draw_grid(offset)
        arena.draw(screen, offset)

        # ordem de camadas: balas/itens no fundo, depois inimigos, e o player
        # sempre por cima de tudo -- por isso os objetos que NÃO são inimigos
        # (balas e itens) são desenhados primeiro
        for o in objects:
            if o not in enemies:
                o.draw(screen, offset)
        for e in enemies:
            e.draw(screen, offset)
        player.draw(screen, offset)

        # desenhar contorno vermelho da tela quando o jogador toma dano
        alpha = player.get_hit_flash_alpha()
        if alpha > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT))
            flash_surf.set_colorkey((0, 0, 0))
            flash_surf.fill((0, 0, 0))
            pygame.draw.rect(flash_surf, (255, 0, 0), (0, 0, WIDTH, HEIGHT), 20)
            flash_surf.set_alpha(alpha)
            screen.blit(flash_surf, (0, 0))

        # desenhar contorno verde da tela quando o jogador se cura
        alpha = player.get_heal_flash_alpha()
        if alpha > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT))
            flash_surf.set_colorkey((0, 0, 0))
            flash_surf.fill((0, 0, 0))
            pygame.draw.rect(flash_surf, (0, 255, 0), (0, 0, WIDTH, HEIGHT), 20)
            flash_surf.set_alpha(alpha)
            screen.blit(flash_surf, (0, 0))

        # HUD
        best_label = font.render(f"Melhor: {best_score}", True, (255, 255, 255))
        screen.blit(best_label, (10, 10))

        score_label = font.render(f"Score: {score}", True, (255, 255, 255))
        screen.blit(score_label, (WIDTH - score_label.get_width() - 10, 10))

        hp_label = font.render(f"HP: {player.health}", True, (255, 90, 90))
        screen.blit(hp_label, (10, HEIGHT - 30))

        weapon_name = type(player.state).__name__.replace("State", "")
        if player.state.ammo is None:
            ammo_text = ""
        else:
            max_ammo = getattr(player.state, 'max_ammo', player.state.ammo)
            ammo_text = f" {player.state.ammo}/{max_ammo}"
        weapon_label = font.render(weapon_name + ammo_text, True, (255, 255, 0))
        screen.blit(weapon_label, (WIDTH - weapon_label.get_width() - 10, HEIGHT - 30))

        draw_crosshair(mouse_screen_pos)

    elif game_state == "menu":
        screen.fill((20, 20, 26))
        title = big_font.render("Hotline Survivors", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 120)))

        subtitle = font.render("WASD/setas: mover | mouse: mirar | clique: atirar | espaço: pegar item",
                                True, (200, 200, 200))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 70)))

        draw_button(button_rect, "Iniciar")

    elif game_state == "gameover":
        screen.fill((20, 20, 26))
        over_label = big_font.render("Você morreu!", True, (255, 90, 90))
        screen.blit(over_label, over_label.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 110)))

        score_label = font.render(f"Score: {score}   Melhor: {best_score}", True, (255, 255, 255))
        screen.blit(score_label, score_label.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50)))

        draw_button(button_rect, "Reiniciar")

    pygame.display.flip()

pygame.quit()