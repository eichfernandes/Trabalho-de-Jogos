def desenhar_tela_fim():
    titulo = fonte_titulo.render("FIM DE JOGO", True, (220, 70, 70))
    linhas = [
        f"Pontos: {score}",
        f"Waves completas: {onda - 1}",
        f"Bolas extras coletadas: {bolas_extras_coletadas}",
        f"Especiais usados: {especiais_usados}",
        f"Tempo de jogo: {tempo_final:.1f}s",
        "",
        "Pressione qualquer tecla para voltar ao início",
    ]
    screen.blit(titulo, titulo.get_rect(center=(LARGURA / 2, ALTURA / 2 - 110)))
    for i, linha in enumerate(linhas):
        if (i==0): 
            cor = (230, 230, 0);
        elif (i==1):
                    cor = (230, 0, 50);
        elif (i==2):
            cor = (30, 144, 255);
        elif (i==3):
                    cor = (0, 230, 0);
        else:
            cor = (190, 190, 190);
        texto = fonte.render(linha, True, cor)
        screen.blit(texto, texto.get_rect(center=(LARGURA / 2, ALTURA / 2 - 30 + i * 32)))
