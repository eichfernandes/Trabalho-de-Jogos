import pygame
from util import colored_sprite, EventHandler, load_sprite, scale_value
from player import ShotgunState, MachineGunState


class Item:
    # a chance de drop agora depende do tipo de inimigo que morreu (ver enemy.py)

    ITEM_SCALE = (40, 40)
    SPRITES = {
        "heal": load_sprite("images/itens/heal.png", ITEM_SCALE),
        "shotgun": load_sprite("images/itens/shotgun.png", ITEM_SCALE),
        "machinegun": load_sprite("images/itens/machinegun.png", ITEM_SCALE),
    }

    HEAL_AMOUNT = 40
    SIZE = 26

    def __init__(self, pos, kind):
        self.pos = pygame.Vector2(pos)
        self.kind = kind
        self.radius = scale_value(self.SIZE // 2)

        self.sprite = self.SPRITES[kind]

    def update(self, dt):
        pass  # item parado no chão, não precisa de lógica de update

    def draw(self, screen, offset):
        screen.blit(self.sprite, self.pos - offset - pygame.Vector2(self.radius, self.radius))

    def apply(self, player):
        if self.kind == "heal":
            player.heal(self.HEAL_AMOUNT)
        elif self.kind == "shotgun":
            player.change_state(ShotgunState)
            self._play_change_gun_sound(player)
        elif self.kind == "machinegun":
            player.change_state(MachineGunState)
            self._play_change_gun_sound(player)

        EventHandler().notify("DestroyObj", self)

    def _play_change_gun_sound(self, player):
        # toca o som de troca de arma (mesmo dict de sons usado pelo player pra atirar)
        if "change_gun" in player.shoot_sounds:
            player.shoot_sounds["change_gun"].play()