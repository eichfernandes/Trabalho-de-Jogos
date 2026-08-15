# Inicialização
import pygame 
import random
pygame.init()
pygame.font.init()



font = font = pygame.font.Font(None, 50)
Nome = "Rafael Eich"
rect =  (260, 100, 200, 35)

x, y = 260,100

print(y)

# Cria a janela
WIDTH   =  800; HEIGHT =  600
screen = pygame.display.set_mode((WIDTH, HEIGHT))  

#loop
while True: 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        # Desenha
        screen.fill((30, 30, 30))
        pygame.draw.rect(screen, (255,255,255), rect)
        screen.blit(font.render(Nome, True, (0,0,0)), (x, y))
        pygame.display.flip()
