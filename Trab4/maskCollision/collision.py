# Centraliza a lógica de colisão do jogo. Collider é singleton: uma única
# instância compartilhada por todos os objetos que colidem.

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


@singleton
class Collider():
    """Despacha cada par de objetos colidíveis para o handler correspondente."""

    def colidir(self, a, b):
        # NÃO usar "import main": o script roda como __main__, não como
        # "main", então isso re-executaria main.py inteiro (reabre janela,
        # reseta estado). sys.modules['__main__'] pega o módulo já em
        # execução independente de como foi invocado.
        import sys
        main = sys.modules['__main__']

        if isinstance(a, main.Bola) and isinstance(b, main.Plataforma):
            self.bola_plataforma(a, b)
        elif isinstance(a, main.Bola) and isinstance(b, main.Caixinha):
            self.bola_caixinha(a, b)
        elif isinstance(a, main.Upgrade) and isinstance(b, main.Plataforma):
            self.upgrade_plataforma(a, b)
        elif isinstance(a, main.EstrelaEspecial) and isinstance(b, main.Plataforma):
            self.estrela_plataforma(a, b)

    # ---- colisões que alteram trajetória ----

    def bola_plataforma(self, bola, plataforma):
        rect_bola = bola.sprite.get_rect(topleft=bola.coord)
        rect_plat = plataforma.sprite.get_rect(topleft=plataforma.coord)

        if bola.vel[1] > 0:  # só reage vindo de cima; de lado a bola atravessa
            largura_plat = rect_plat.width
            desvio = (rect_bola.centerx - rect_plat.centerx) / (largura_plat / 2)
            desvio = max(-1, min(1, desvio))

            velocidade = (bola.vel[0] ** 2 + bola.vel[1] ** 2) ** 0.5
            bola.vel[0] = desvio * velocidade
            bola.vel[1] = -abs(velocidade) * (1 - abs(desvio) * 0.4)

            bola.coord[1] = rect_plat.top - rect_bola.height  # evita afundar na plataforma

    def bola_caixinha(self, bola, caixinha):
        rect_bola = bola.sprite.get_rect(topleft=bola.coord)
        rect_caixa = caixinha.sprite.get_rect(topleft=caixinha.coord)

        sobreposicao_x = min(rect_bola.right, rect_caixa.right) - max(rect_bola.left, rect_caixa.left)
        sobreposicao_y = min(rect_bola.bottom, rect_caixa.bottom) - max(rect_bola.top, rect_caixa.top)

        # reflete pelo eixo de menor penetração (normal de colisão aproximada)
        if sobreposicao_x < sobreposicao_y:
            bola.vel[0] *= -1
        else:
            bola.vel[1] *= -1

        caixinha.quebrar()

    # ---- colisões que só aplicam efeito, sem alterar trajetória ----

    def upgrade_plataforma(self, upgrade, plataforma):
        import sys
        main = sys.modules['__main__']
        upgrade.coletado = True
        main.criar_bola_extra(plataforma)

    def estrela_plataforma(self, estrela, plataforma):
        import sys
        main = sys.modules['__main__']
        estrela.coletada = True
        main.coletar_especial()