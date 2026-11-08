import pygame


_fullscreen = False


def create_display(size):
    flags = 0
    if _fullscreen:
        flags = pygame.SCALED | pygame.FULLSCREEN
    return pygame.display.set_mode(size, flags)


def toggle_fullscreen(size):
    global _fullscreen
    previous = _fullscreen
    _fullscreen = not previous
    try:
        return create_display(size)
    except pygame.error:
        _fullscreen = previous
        raise


def is_fullscreen():
    return _fullscreen
