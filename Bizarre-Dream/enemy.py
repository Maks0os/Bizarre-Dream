import pygame
import math
import heapq
from audio import get_audio_manager

DIRECTIONS = ['down', 'left', 'right', 'up']

class Enemy:
    SPRITE_SIZE = (32, 64)
    def __init__(self, x, y, player_ref, get_fov_polygon, tile_width, tile_height, obstacles,
                 sprite_path='img/animations/!Enemy_w.png', frame_coords={'down': (0, 0),'left': (0, 64),'right': (0, 128),'up': (0, 192)
}):
        self.x = x  # в пикселях
        self.y = y
        self.player_ref = player_ref  # ссылка на игрока (для слежения)
        self.get_fov_polygon = get_fov_polygon  # функция, возвращающая текущий FOV-полигон
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.speed = 2  # пикселя за кадр
        self.obstacles = obstacles
        # AI
        self.path = []
        self.target_tile = None
        self.last_player_tile = None
        # Направление движения
        self.direction = 'down'
        # Загрузка спрайтов по направлениям
        self.sprites = self.load_directional_sprites(sprite_path, frame_coords)
        # Ограничение частоты пересчёта пути
        self.repath_cooldown = 0  # в кадрах
        self.REPATH_DELAY = 12  # 12 кадров = 0.2 сек при 60 FPS
        
        # Audio manager
        self.audio_manager = get_audio_manager()
        
        # Звуки крика
        self.is_moving = False  # Флаг движения для звуков

    @staticmethod
    def load_directional_sprites(sprite_path, frame_coords):
        """
        Загружает спрайты врага для каждого направления.
        frame_coords: dict {'down': (x, y), ...} — координаты левого верхнего угла кадра для каждого направления
        """
        image = pygame.image.load(sprite_path).convert_alpha()
        sprites = {}
        for dir in DIRECTIONS:
            if frame_coords and dir in frame_coords:
                x, y = frame_coords[dir]
            else:
                x, y = 0, 0  # по умолчанию
            rect = pygame.Rect(x, y, 32, 64)
            sprites[dir] = image.subsurface(rect).copy()
        return sprites

    def get_hitbox(self):
        return pygame.Rect(self.x, self.y, self.tile_width, self.tile_height)

    def is_in_fov(self):
        player = getattr(self, 'player', None)
        if player and hasattr(player, 'lit_enemies'):
            return self in player.lit_enemies
        fov_poly = self.get_fov_polygon()
        if not fov_poly:
            return False
        hitbox = self.get_hitbox()
        for px in [hitbox.left, hitbox.right]:
            for py in [hitbox.top, hitbox.bottom]:
                if point_in_poly(px, py, fov_poly):
                    return True
        return False

    def is_colliding(self, px, py):
        left = int(px / self.tile_width)
        right = int((px + self.tile_width - 1) / self.tile_width)
        top = int(py / self.tile_height)
        bottom = int((py + self.tile_height - 1) / self.tile_height)
        for tx in range(left, right + 1):
            for ty in range(top, bottom + 1):
                if (tx, ty) in self.obstacles:
                    return True
        return False

    def get_tile(self):
        return (int(self.x // self.tile_width), int(self.y // self.tile_height))

    def get_player_tile(self):
        player_cx, player_cy = self.player_ref()
        return (int(player_cx // self.tile_width), int(player_cy // self.tile_height))

    def reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def astar(self, start, goal, occupied=None):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        closed = set()
        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                return self.reconstruct_path(came_from, current)
            closed.add(current)
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                neighbor = (current[0]+dx, current[1]+dy)
                if neighbor in self.obstacles or neighbor in closed:
                    continue
                if occupied and neighbor in occupied and neighbor != goal:
                    continue
                tentative_g = g_score[current] + 1
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return []

    def update(self, enemies=None):
        was_moving = self.is_moving  # Сохраняем предыдущее состояние движения
        self.is_moving = False  # Сбрасываем флаг движения
        
        if not self.is_in_fov():
            player_tile = self.get_player_tile()
            my_tile = self.get_tile()
            occupied = set()
            if enemies:
                for e in enemies:
                    if e is not self:
                        occupied.add(e.get_tile())
            # Пересчитываем путь только если cooldown == 0
            need_repath = (
                not self.path or self.target_tile != player_tile or (self.path and my_tile == self.path[0])
            )
            if need_repath and self.repath_cooldown == 0:
                path = self.astar(my_tile, player_tile, occupied)
                if path and len(path) > 1:
                    self.path = path[1:]
                    self.target_tile = player_tile
                else:
                    self.path = []
                self.repath_cooldown = self.REPATH_DELAY
            if self.repath_cooldown > 0:
                self.repath_cooldown -= 1
            if self.path:
                next_tile = self.path[0]
                if next_tile in occupied:
                    return  # ждём, не двигаемся
                next_x = next_tile[0] * self.tile_width
                next_y = next_tile[1] * self.tile_height
                dx = next_x - self.x
                dy = next_y - self.y
                dist = math.hypot(dx, dy)
                if abs(dx) > abs(dy):
                    self.direction = 'right' if dx > 0 else 'left'
                else:
                    self.direction = 'down' if dy > 0 else 'up'
                if dist < self.speed:
                    self.x = next_x
                    self.y = next_y
                    self.path.pop(0)
                else:
                    self.x += self.speed * dx / dist
                    self.y += self.speed * dy / dist
                    self.is_moving = True  # Враг движется
        else:
            # Если в луче — стоит на месте
            pass
            
        # Звуки крика (вынесено за пределы блока is_in_fov)
        if self.is_moving and not was_moving:  # Начало движения
            self.audio_manager.play_enemy_scream()
        elif self.is_moving and was_moving:  # Продолжение движения
            # Проверяем, не закончился ли звук, и если да - запускаем заново
            if not self.audio_manager.sounds['enemy_scream'].get_num_channels():
                self.audio_manager.play_enemy_scream()
        elif not self.is_moving and was_moving:  # Остановка движения
            self.audio_manager.stop_enemy_scream()  # Прерываем звук крика

    def draw(self, surface, cam_x, cam_y):
        px = self.x - cam_x
        py = self.y - cam_y
        frame = self.sprites[self.direction]
        # Центрируем по X, низ кадра = низ хитбокса
        offset_x = px - (self.SPRITE_SIZE[0] - self.tile_width) // 2
        offset_y = py - (self.SPRITE_SIZE[1] - self.tile_height)
        surface.blit(frame, (offset_x, offset_y))
        # DEBUG: рисуем хитбокс врага
       # hitbox_rect = pygame.Rect(px, py, self.tile_width, self.tile_height)
       # pygame.draw.rect(surface, (255, 0, 0), hitbox_rect, 2)

def point_in_poly(x, y, poly):
    # Проверка: точка в многоугольнике (алгоритм луча)
    num = len(poly)
    j = num - 1
    c = False
    for i in range(num):
        if ((poly[i][1] > y) != (poly[j][1] > y)) and \
           (x < (poly[j][0] - poly[i][0]) * (y - poly[i][1]) / (poly[j][1] - poly[i][1] + 1e-6) + poly[i][0]):
            c = not c
        j = i
    return c 