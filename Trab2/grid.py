# Classe base abstrata (Abstract Base Class)
from abc import ABC, abstractmethod
import random
import pygame


# fonte usada para os números das células, criada só quando for usada
# (pygame.font precisa estar inicializado antes de criar a fonte)
_fonte_numeros = None

def _obter_fonte():
    global _fonte_numeros
    if _fonte_numeros is None:
        _fonte_numeros = pygame.font.SysFont(None, 28)
    return _fonte_numeros

_bomba = None

def _obter_bomba(size):
    global _bomba

    if _bomba is None:
        _bomba = pygame.image.load("images/bomb/bomb.png").convert_alpha()
    _bomba = pygame.transform.scale(_bomba, (size, size))
    return _bomba

# objeto herda de classe abstrata
## nunca pode ser criada, só as filhas
class obj (ABC):

    def __init__(self, x, y, sprites):
        self.x = x
        self.y = y
        #lista
        self.sprites = sprites


    def draw(self, screen):
        for s in self.sprites:
            screen.blit(self.sprites, (self.x, self.y))

    # avisa que o método é abstato e precisa ser feito pelos filhos
    @abstractmethod
    def update(self, dt):
        pass

class Grid (obj):

    # só avisa a construtora da mãe o que fazer
    # pode, e deve ser extendido para outras caracteristicas nescessárias
    def __init__(self, x, y, sprites, grid_size, cell_size, num_minas):
        # bom lugar para criar uma matriz de celulas
        super().__init__(x, y, sprites)

        self.rows, self.cols = grid_size
        self.cell_size = cell_size
        self.num_minas = num_minas

        self.game_over = False
        self.vitoria = False
        self.celulas_reveladas = 0

        # matriz de células
        self.cells = []
        self._montar_matriz()
        self._sortear_minas()
        self._calcular_numeros()

    def _montar_matriz(self):
        for row in range(self.rows):
            linha = []
            for col in range(self.cols):
                cx = self.x + col * self.cell_size
                cy = self.y + row * self.cell_size
                linha.append(Cell(cx, cy, [], self.cell_size, row, col))
            self.cells.append(linha)

    def _sortear_minas(self):
        posicoes = []
        # Cria todas as posições possiveis
        for r in range(self.rows):
            for c in range(self.cols):
                posicoes.append((r, c))
        random.shuffle(posicoes)
        for r, c in posicoes[:self.num_minas]:
            self.cells[r][c].is_mine = True

    def _vizinhos(self, row, col):
        vizinhos = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    vizinhos.append((nr, nc))
        return vizinhos

    def _calcular_numeros(self):
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.cells[row][col]
                if cell.is_mine:
                    continue
                cell.adjacent = sum(
                    1 for nr, nc in self._vizinhos(row, col) if self.cells[nr][nc].is_mine
                )

    def celula_no_ponto(self, pos):
        mx, my = pos
        col = (mx - self.x) // self.cell_size
        row = (my - self.y) // self.cell_size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return int(row), int(col)
        return None

    def revelar(self, row, col):
        if self.game_over or self.vitoria:
            return

        cell = self.cells[row][col]
        if cell.revealed or cell.flagged:
            return

        cell.revelar()
        self.celulas_reveladas += 1

        if cell.is_mine:
            self.game_over = True
            self._revelar_tudo()
            return

        # abre em cascata quando não há minas ao redor
        if cell.adjacent == 0:
            for nr, nc in self._vizinhos(row, col):
                if not self.cells[nr][nc].revealed:
                    self.revelar(nr, nc)

        self._checar_vitoria()

    def alternar_bandeira(self, row, col):
        if self.game_over or self.vitoria:
            return

        cell = self.cells[row][col]
        if not cell.revealed and self.minas_restantes() > 0:
            cell.alternar_bandeira()

    def _revelar_tudo(self):
        for linha in self.cells:
            for cell in linha:
                if cell.is_mine:
                    cell.revelar()

    def _checar_vitoria(self):
        total_seguras = self.rows * self.cols - self.num_minas
        if self.celulas_reveladas >= total_seguras:
            self.vitoria = True

    def minas_restantes(self):
        bandeiras = 0
        for linha in self.cells:
            for cell in linha:
                if cell.flagged:
                    bandeiras += 1
        return self.num_minas - bandeiras

    def reiniciar(self):
        self.game_over = False
        self.vitoria = False
        self.celulas_reveladas = 0
        self.cells = []
        self._montar_matriz()
        self._sortear_minas()
        self._calcular_numeros()

    def draw(self, screen):

        # aqui a grade não tem sprite próprio, quem desenha são as células
        for linha in self.cells:
            for cell in linha:
                cell.draw(screen)

    def update(self, dt):
        for linha in self.cells:
            for cell in linha:
                cell.update(dt)


class Cell (obj):

    def __init__(self, x, y, sprites, grid_size, row, col):
        super().__init__(x, y, sprites)

        # aqui grid_size é usado como tamanho em pixels da célula
        self.size = grid_size
        self.row = row
        self.col = col

        self.is_mine = False
        self.adjacent = 0
        self.revealed = False
        self.flagged = False

        # animação simples de abertura (escala de 0 até 1)
        self.animando = False
        self.anim_escala = 1.0
        self.anim_tempo = 0
        self.anim_duracao = 0.15

    def revelar(self):
        self.revealed = True
        self.animando = True
        self.anim_tempo = 0
        self.anim_escala = 0

    def alternar_bandeira(self):
        self.flagged = not self.flagged

    def draw(self, screen):

        rect_base = pygame.Rect(self.x, self.y, self.size, self.size)

        if not self.revealed:
            cor = (30, 100, 30) if self.flagged else (90, 90, 90)
            pygame.draw.rect(screen, cor, rect_base)
        else:
            # escala anima a abertura da célula
            tamanho = max(2, int(self.size * self.anim_escala))
            offset = (self.size - tamanho) // 2
            rect_anim = pygame.Rect(self.x + offset, self.y + offset, tamanho, tamanho)
            pygame.draw.rect(screen, (200, 200, 200), rect_anim)

            if self.anim_escala >= 1.0:
                if self.is_mine:
                    pygame.draw.rect(screen, (100, 30, 30), rect_base)
                    # adicionando sprite da bomba
                    bomb_size = self.size * 0.6
                    bomb_offset = (self.size - bomb_size) // 2
                    bomb_pos = (int(self.x + bomb_offset), int(self.y + bomb_offset))
                    screen.blit(_obter_bomba(bomb_size), bomb_pos)
                elif self.adjacent > 0:
                    fonte = _obter_fonte()
                    cor_num = (100, 30, 30)
                    texto = fonte.render(str(self.adjacent), True, cor_num)
                    screen.blit(texto, texto.get_rect(center=rect_base.center))

        pygame.draw.rect(screen, (30, 30, 30), rect_base, 2)

    def update(self, dt):
        # para garantir animação de abertura ao revelar
        if self.animando:
            self.anim_tempo += dt
            self.anim_escala = min(1.0, self.anim_tempo / self.anim_duracao)
            if self.anim_escala >= 1.0:
                self.animando = False