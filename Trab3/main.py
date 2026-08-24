import pygame
from player import Player

#inicialização

pygame.init()
WIDTH   =  800; HEIGHT =  600

screen = pygame.display.set_mode((WIDTH, HEIGHT))  
player = Player((50, 50))

objects = []
objects.append(player)

# funções auxiliares

def handle_input(player):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.action_1()
            if event.key == pygame.K_TAB:
                player.action_2()


# loop principal

running = True
while running:

    handle_input(player)

    for obj in objects:
        obj.update(1)

    screen.fill((30,30,30))

    for obj in objects:
        obj.draw(screen)
    
    pygame.display.flip()
    