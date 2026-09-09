import os
import sys

# Keeps startup quiet on systems without audio hardware; real devices still get SFX.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import Game
from runtime_paths import resource_path
from settings import HEIGHT, TITLE, WIDTH


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    icon_path = resource_path("packaging", "app-icon.png")
    if icon_path.exists():
        try:
            pygame.display.set_icon(pygame.image.load(icon_path.as_posix()))
        except pygame.error:
            pass
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)
    try:
        Game(screen).run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    if len(sys.argv)==3 and sys.argv[1]=="--verify-bundle":
        from bundle_check import verify
        verify(sys.argv[2])
    else:
        main()
