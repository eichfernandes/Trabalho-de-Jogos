import pygame
import math
import random
from util import clamp

# ---- ARENA ----
# A arena é dividida num grid de "salas" (quartos) ligadas por portas (vãos
# nas paredes). É baseada no rascunho enviado: 4 faixas de linhas -- a de
# cima e a de baixo com 2 salas largas cada, as duas do meio com 4 salas
# cada -- totalizando 12 salas, cada uma com 1 ponto de spawn (os quadrados
# amarelos do rascunho).

WALL_THICKNESS = 14   # espessura de cada segmento de parede
DOOR_WIDTH = 140      # largura do vão de cada porta (bem maior que qualquer raio de colisão)

ARENA_WIDTH = 2000
ARENA_HEIGHT = 1900

ROOMS = {
    "R1L":  pygame.Rect(0,    0,    1000, 500),
    "R1R":  pygame.Rect(1000, 0,    1000, 500),
    "R2C1": pygame.Rect(0,    500,  500,  450),
    "R2C2": pygame.Rect(500,  500,  500,  450),
    "R2C3": pygame.Rect(1000, 500,  500,  450),
    "R2C4": pygame.Rect(1500, 500,  500,  450),
    "R3C1": pygame.Rect(0,    950,  500,  450),
    "R3C2": pygame.Rect(500,  950,  500,  450),
    "R3C3": pygame.Rect(1000, 950,  500,  450),
    "R3C4": pygame.Rect(1500, 950,  500,  450),
    "R4L":  pygame.Rect(0,    1400, 1000, 500),
    "R4R":  pygame.Rect(1000, 1400, 1000, 500),
}

# cada porta liga duas salas e diz onde fica o vão (usado tanto pra abrir o
# buraco na parede quanto como "waypoint" de navegação dos inimigos)
DOORS = [
    ("R1L",  "R2C2", (750, 500)),
    ("R1R",  "R2C3", (1250, 500)),
    ("R2C1", "R3C1", (250, 950)),
    ("R2C2", "R3C2", (750, 950)),
    ("R2C3", "R3C3", (1250, 950)),
    ("R2C4", "R3C4", (1750, 950)),
    ("R3C1", "R4L",  (250, 1400)),
    ("R3C4", "R4R",  (1750, 1400)),
    ("R1L",  "R1R",  (1000, 250)),
    ("R2C1", "R2C2", (500, 725)),
    ("R2C3", "R2C4", (1500, 725)),
    ("R3C1", "R3C2", (500, 1175)),
    ("R3C3", "R3C4", (1500, 1175)),
    ("R4L",  "R4R",  (1000, 1650)),
]

# ponto de spawn de cada sala (equivalente aos quadrados amarelos do rascunho)
SPAWN_POINTS = [room.center for room in ROOMS.values()]

# sala onde o player nasce ao (re)começar a partida
PLAYER_START = ROOMS["R2C2"].center


def _make_rect(is_vertical, fixed, half, start, end):
    if is_vertical:
        return pygame.Rect(int(fixed - half), int(start), int(WALL_THICKNESS), int(end - start))
    return pygame.Rect(int(start), int(fixed - half), int(end - start), int(WALL_THICKNESS))


def _segment(is_vertical, fixed, start, end, gaps):
    # devolve os retângulos sólidos de uma parede (fixed = x se for vertical,
    # y se for horizontal), já "furada" nos pontos de "gaps" (portas)
    half = WALL_THICKNESS / 2
    cuts = sorted(g for g in gaps if start < g < end)
    rects = []
    pos = start
    for g in cuts:
        gap_start = max(start, g - DOOR_WIDTH / 2)
        gap_end = min(end, g + DOOR_WIDTH / 2)
        if gap_start > pos:
            rects.append(_make_rect(is_vertical, fixed, half, pos, gap_start))
        pos = gap_end
    if pos < end:
        rects.append(_make_rect(is_vertical, fixed, half, pos, end))
    return rects


def _build_walls():
    walls = []

    # bordas externas: fecham a arena por completo, sem portas
    walls += _segment(False, 0, 0, ARENA_WIDTH, [])              # topo
    walls += _segment(False, ARENA_HEIGHT, 0, ARENA_WIDTH, [])   # base
    walls += _segment(True, 0, 0, ARENA_HEIGHT, [])              # esquerda
    walls += _segment(True, ARENA_WIDTH, 0, ARENA_HEIGHT, [])    # direita

    # divisórias horizontais entre as 4 faixas de salas
    walls += _segment(False, 500, 0, ARENA_WIDTH, [750, 1250])
    walls += _segment(False, 950, 0, ARENA_WIDTH, [250, 750, 1250, 1750])
    walls += _segment(False, 1400, 0, ARENA_WIDTH, [250, 1750])

    # divisória vertical central das faixas largas (topo e base)
    walls += _segment(True, 1000, 0, 500, [250])
    walls += _segment(True, 1000, 1400, 1900, [1650])

    # divisórias verticais das duas faixas do meio (4 colunas cada).
    # a coluna central (x=1000) fica sólida, sem porta, como "espinha" do mapa
    walls += _segment(True, 500, 500, 950, [725])
    walls += _segment(True, 1000, 500, 950, [])
    walls += _segment(True, 1500, 500, 950, [725])

    walls += _segment(True, 500, 950, 1400, [1175])
    walls += _segment(True, 1000, 950, 1400, [])
    walls += _segment(True, 1500, 950, 1400, [1175])

    return walls


WALLS = _build_walls()


def _build_adjacency():
    adj = {name: [] for name in ROOMS}
    for a, b, point in DOORS:
        adj[a].append((b, pygame.Vector2(point)))
        adj[b].append((a, pygame.Vector2(point)))
    return adj


ADJACENCY = _build_adjacency()


def draw(screen, offset):
    # desenha as paredes como simples linhas (retângulos finos) brancas
    for wall in WALLS:
        screen_rect = wall.move(-offset.x, -offset.y)
        pygame.draw.rect(screen, (255, 255, 255), screen_rect)


def line_clear(p1, p2):
    # True se nenhuma parede corta o segmento p1->p2 (usado tanto pra mirar
    # quanto pra travar balas -- como as portas são só um vão na parede, o
    # segmento passa livre por elas naturalmente)
    for wall in WALLS:
        if wall.clipline(p1, p2):
            return False
    return True


def room_at(pos):
    for name, rect in ROOMS.items():
        if rect.collidepoint(pos):
            return name
    # fallback de segurança (ex.: posição em cima de uma parede): sala mais próxima
    return min(ROOMS, key=lambda n: (pygame.Vector2(ROOMS[n].center) - pygame.Vector2(pos)).length_squared())


def _bfs_path(start_room, goal_room):
    if start_room == goal_room:
        return [start_room]
    visited = {start_room}
    queue = [[start_room]]
    while queue:
        path = queue.pop(0)
        node = path[-1]
        for neighbor, _ in ADJACENCY[node]:
            if neighbor in visited:
                continue
            new_path = path + [neighbor]
            if neighbor == goal_room:
                return new_path
            visited.add(neighbor)
            queue.append(new_path)
    return None


def next_waypoint(from_pos, to_pos):
    # devolve o próximo ponto que um inimigo deve perseguir pra chegar em
    # "to_pos": o próprio alvo se já tiver linha de visão livre (mesmo que
    # atravessando uma porta), ou o centro da próxima porta no caminho até lá
    start_room = room_at(from_pos)
    goal_room = room_at(to_pos)
    path = _bfs_path(start_room, goal_room)
    if not path or len(path) < 2:
        return pygame.Vector2(to_pos)

    next_room = path[1]
    for neighbor, door_point in ADJACENCY[start_room]:
        if neighbor == next_room:
            return pygame.Vector2(door_point)
    return pygame.Vector2(to_pos)


def resolve_wall_collision(pos, radius):
    # empurra um círculo (pos, radius) pra fora de qualquer parede que esteja atravessando
    pos = pygame.Vector2(pos)
    for wall in WALLS:
        closest_x = clamp(pos.x, wall.left, wall.right)
        closest_y = clamp(pos.y, wall.top, wall.bottom)
        dx = pos.x - closest_x
        dy = pos.y - closest_y
        dist_sq = dx * dx + dy * dy
        if dist_sq < radius * radius:
            dist = math.sqrt(dist_sq)
            if dist < 1e-6:
                pos.y -= radius  # centro em cima da parede (raro); empurra pra cima
            else:
                overlap = radius - dist
                pos.x += dx / dist * overlap
                pos.y += dy / dist * overlap
    return pos


def random_spawn_point(visible_rect, margin=80):
    # sorteia um ponto de spawn (ver SPAWN_POINTS) que esteja fora da área
    # visível do jogador, com uma margem extra de segurança
    check_rect = visible_rect.inflate(margin * 2, margin * 2)
    candidates = [p for p in SPAWN_POINTS if not check_rect.collidepoint(p)]
    if not candidates:
        candidates = SPAWN_POINTS  # fallback: nenhum ponto fora da tela, usa qualquer um
    return pygame.Vector2(random.choice(candidates))