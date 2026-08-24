import pygame
from grid import Grid, Cell


pygame.init()
pygame.font.init()

WIDTH   =  800; HEIGHT =  600
screen = pygame.display.set_mode((WIDTH, HEIGHT))  

# caso precise de usar fontes na main, descomente

font_size = 28
font = pygame.font.Font(None, font_size)

# caso precise carregar imagens na main, descomente

#idle = pygame.image.load("images/duck/duck.png").convert_alpha()
#step = pygame.image.load("images/duck/step.png").convert_alpha()
#etc


#numero de celulas
grid_size = (10, 10)

# tamanho de cada célula em pixels e quantidade de minas
cell_size = 40
num_minas = 15

#criar objetos, adicione eles a lista
objects = []

# centraliza a grade na tela
grid_x = (WIDTH - grid_size[1] * cell_size) // 2
grid_y = 80

grade = Grid(grid_x, grid_y, [], grid_size, cell_size, num_minas)
objects.append(grade)

# posição do cursor controlado pelo teclado (linha, coluna)
cursor_row = 0
cursor_col = 0

relogio = pygame.time.Clock()
tempo_decorrido = 0

while True: 
    dt = relogio.tick(60) / 1000

    if not grade.game_over and not grade.vitoria:
        tempo_decorrido += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()

        # uso do mouse é obrigatório
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if pygame.mouse.get_pressed()[0]: # 0 botão esquedo 2, direito
                alvo = grade.celula_no_ponto(event.pos)
                if alvo:
                    grade.revelar(*alvo)
            elif pygame.mouse.get_pressed()[2]:
                alvo = grade.celula_no_ponto(event.pos)
                if alvo:
                    grade.alternar_bandeira(*alvo)

        #caso queira usar levantar o mouse, descomente
        #elif event.type == pygame.MOUSEBUTTONUP:
        #                    exit()


        # uso do teclado para controle é obrigatório
        elif event.type == pygame.KEYDOWN:
            #inclua outras funcionalidades para outras téclas
            if event.key == pygame.K_ESCAPE:
                exit()

            # movimenta o cursor de seleção pela grade
            elif event.key == pygame.K_UP:
                cursor_row = max(0, cursor_row - 1)
            elif event.key == pygame.K_DOWN:
                cursor_row = min(grid_size[0] - 1, cursor_row + 1)
            elif event.key == pygame.K_LEFT:
                cursor_col = max(0, cursor_col - 1)
            elif event.key == pygame.K_RIGHT:
                cursor_col = min(grid_size[1] - 1, cursor_col + 1)

            # revela ou marca a célula selecionada
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                grade.revelar(cursor_row, cursor_col)
            elif event.key == pygame.K_f:
                grade.alternar_bandeira(cursor_row, cursor_col)

            # reinicia a partida
            elif event.key == pygame.K_r:
                grade.reiniciar()
                tempo_decorrido = 0

    #atualiza
    for obj in objects:
        obj.update(dt)

    # Desenha
    screen.fill((30, 30, 30))


    for obj in objects:
        obj.draw(screen)

    # destaque da célula selecionada pelo teclado
    destaque = pygame.Rect(
        grid_x + cursor_col * cell_size,
        grid_y + cursor_row * cell_size,
        cell_size, cell_size
    )
    pygame.draw.rect(screen, (255, 255, 255), destaque, 3)

    # HUD com minas restantes e tempo de jogo
    texto_minas = font.render(f"Minas: {grade.minas_restantes()}", True, (255, 255, 255))
    screen.blit(texto_minas, (20, 20))

    texto_tempo = font.render(f"Tempo: {int(tempo_decorrido)}s", True, (255, 255, 255))
    screen.blit(texto_tempo, (WIDTH - 160, 20))

    if grade.game_over:
        texto_status = font.render("Você perdeu! Pressione R para reiniciar", True, (220, 60, 60))
        screen.blit(texto_status, (20, HEIGHT - 40))
    elif grade.vitoria:
        texto_status = font.render("Você venceu! Pressione R para reiniciar", True, (60, 200, 60))
        screen.blit(texto_status, (20, HEIGHT - 40))

    pygame.display.flip()