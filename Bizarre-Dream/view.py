import pygame

class Camera:
    def __init__(self, screen_width, screen_height, tile_width, tile_height, zone_tiles=5, smoothing=0.15):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.zone_width = zone_tiles * tile_width
        self.zone_height = zone_tiles * tile_height
        self.smoothing = smoothing
        # Смещение камеры (float для плавного движения)
        self.offset_x = 0.0
        self.offset_y = 0.0
        # Мёртвая зона всегда по центру экрана
        self.zone_rect = pygame.Rect(
            (screen_width - self.zone_width) // 2,
            (screen_height - self.zone_height) // 2,
            self.zone_width,
            self.zone_height
        )

    def update(self, player_px, player_py):
        # Вычисляет позицию игрока в экранных координатах
        player_screen_x = player_px - self.offset_x
        player_screen_y = player_py - self.offset_y
        target_offset_x = self.offset_x
        target_offset_y = self.offset_y
        # Если игрок вне мёртвой зоны, камера двигается так, чтобы игрок был на краю зоны
        if player_screen_x < self.zone_rect.left:
            target_offset_x = player_px - self.zone_rect.left
        elif player_screen_x > self.zone_rect.right:
            target_offset_x = player_px - self.zone_rect.right
        if player_screen_y < self.zone_rect.top:
            target_offset_y = player_py - self.zone_rect.top
        elif player_screen_y > self.zone_rect.bottom:
            target_offset_y = player_py - self.zone_rect.bottom
        # Плавно интерполируем смещение к целевому значению
        self.offset_x += (target_offset_x - self.offset_x) * self.smoothing
        self.offset_y += (target_offset_y - self.offset_y) * self.smoothing

    def apply(self, rect):
        # Применяем смещение камеры к rect
        return rect.move(-int(self.offset_x), -int(self.offset_y))
