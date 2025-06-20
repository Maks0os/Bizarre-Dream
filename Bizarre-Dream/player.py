import pygame
import math
import controls
from audio import get_audio_manager

class Player:
    def __init__(self, x, y, tile_width, tile_height, obstacles):
        self.x = x
        self.y = y
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.obstacles = obstacles
        self.move_speed = 4
        self.fov_target_dx = 0
        self.fov_target_dy = 1
        self.fov_smooth_coef = 0.1
        self.flashlight_enabled = False
        self._flashlight_toggle_lock = False
        self.last_move_dir = 'down'
        self.is_moving = False
        self.fading = False
        self.fade_in = False
        self.fade_out = False
        self.fade_alpha = 0
        self.fade_speed = 15
        self.next_map_info = None
        self.menu_active = False
        self.last_fov_poly = None
        self.lit_enemies = set()
        # Для оптимизации FOV
        self._last_fov_params = None
        self._fov_recalc_cooldown = 0
        self._FOV_RECALC_DELAY = 2  # не чаще 1 раза в 2 кадра
        
        # Audio manager
        self.audio_manager = get_audio_manager()
        
        # Звуки шагов
        self.step_cooldown = 0
        self.step_delay = 15  # Задержка между звуками шагов (каждые 15 кадров)

    def get_position(self):
        return self.x, self.y

    def get_center(self):
        return self.x + self.tile_width // 2, self.y + self.tile_height // 2

    def get_hitbox(self):
        return pygame.Rect(self.x, self.y, self.tile_width, self.tile_height)

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

    def update(self, cam_x=0, cam_y=0):
        # Переключение фонарика
        if controls.is_button_pressed('f'):
            if not self._flashlight_toggle_lock:
                self.flashlight_enabled = not self.flashlight_enabled
                self.audio_manager.play_switch_sound()  # Звук переключателя
                self._flashlight_toggle_lock = True
        else:
            self._flashlight_toggle_lock = False

        # Плавное направление фонарика (FOV)
        mouse_pos = controls.get_mouse_pos()
        # Переводим координаты мыши в мировые координаты
        mouse_world_x = mouse_pos[0] + cam_x
        mouse_world_y = mouse_pos[1] + cam_y
        player_cx = self.x + self.tile_width // 2
        player_cy = self.y + self.tile_height // 2
        dx = mouse_world_x - player_cx
        dy = mouse_world_y - player_cy
        if dx == 0 and dy == 0:
            dx, dy = 0, 1
        self.fov_target_dx += (dx - self.fov_target_dx) * self.fov_smooth_coef
        self.fov_target_dy += (dy - self.fov_target_dy) * self.fov_smooth_coef

        # --- Движение игрока ---
        self.is_moving = False
        dx, dy = 0, 0
        move_dir = None
        if controls.is_button_pressed('up') or controls.is_button_pressed('w'):
            dy = -self.move_speed
            move_dir = 'up'
        elif controls.is_button_pressed('down') or controls.is_button_pressed('s'):
            dy = self.move_speed
            move_dir = 'down'
        elif controls.is_button_pressed('left') or controls.is_button_pressed('a'):
            dx = -self.move_speed
            move_dir = 'left'
        elif controls.is_button_pressed('right') or controls.is_button_pressed('d'):
            dx = self.move_speed
            move_dir = 'right'
        if dx != 0 or dy != 0:
            new_px = self.x + dx
            new_py = self.y + dy
            if not self.is_colliding(new_px, new_py):
                self.x = new_px
                self.y = new_py
                self.is_moving = True
                self.last_move_dir = move_dir
                
                # Звуки шагов
                if self.step_cooldown <= 0:
                    self.audio_manager.play_walk_sound()  # Случайный звук шагов
                    self.step_cooldown = self.step_delay
                else:
                    self.step_cooldown -= 1

    def _compute_fov_polygon(self, cam_x, cam_y, obstacles, tile_width, tile_height, angle=None, enemies=None):
        # Более агрессивная оптимизация: пересчёт только при существенном изменении
        player_pos = (int(self.x), int(self.y))
        dir_angle = math.degrees(math.atan2(self.fov_target_dy, self.fov_target_dx)) if (self.fov_target_dx or self.fov_target_dy) else 90
        last_params = self._last_fov_params
        # num_steps уменьшен
        num_steps = 40
        # Проверяем, изменилось ли положение игрока или направление больше чем на 5 градусов
        need_recalc = True
        if last_params is not None:
            last_pos, last_angle, last_cam, last_enemies = last_params
            angle_diff = abs((dir_angle - last_angle + 180) % 360 - 180)
            if player_pos == last_pos and angle_diff < 5 and cam_x == last_cam[0] and cam_y == last_cam[1] and last_enemies == (tuple(sorted((e.x, e.y) for e in enemies)) if enemies else None):
                if self._fov_recalc_cooldown > 0 and self.last_fov_poly is not None:
                    self._fov_recalc_cooldown -= 1
                    return self.last_fov_poly, self.lit_enemies
                need_recalc = False
        if not need_recalc:
            return self.last_fov_poly, self.lit_enemies
        # Пересчитываем FOV
        FOV_ANGLE = 100
        FOV_RADIUS = 400
        EXTRA_LIGHT_TILES = 1
        player_cx = int(self.x - cam_x + tile_width // 2)
        player_cy = int(self.y - cam_y + tile_height // 2)
        dx = self.fov_target_dx
        dy = self.fov_target_dy
        if angle is not None:
            dx = math.cos(angle)
            dy = math.sin(angle)
        if dx == 0 and dy == 0:
            dx, dy = 0, 1
        angle_rad = math.atan2(dy, dx)
        points = [(player_cx, player_cy)]
        lit_enemies = set()
        for i in range(num_steps + 1):
            a = angle_rad - math.radians(FOV_ANGLE) / 2 + i * math.radians(FOV_ANGLE) / num_steps
            hit = False
            enemy_hit = None
            for r in range(0, FOV_RADIUS, 4):
                x = player_cx + r * math.cos(a)
                y = player_cy + r * math.sin(a)
                tile_x = int((x + cam_x) // tile_width)
                tile_y = int((y + cam_y) // tile_height)
                if (tile_x, tile_y) in obstacles:
                    hit = True
                    break
                if enemies:
                    for enemy in enemies:
                        if enemy.get_hitbox().collidepoint(x + cam_x, y + cam_y):
                            hit = True
                            enemy_hit = enemy
                            break
                    if hit:
                        break
            if hit:
                r += tile_width * EXTRA_LIGHT_TILES
                if r > FOV_RADIUS:
                    r = FOV_RADIUS
                x = player_cx + r * math.cos(a)
                y = player_cy + r * math.sin(a)
                if enemy_hit:
                    lit_enemies.add(enemy_hit)
            else:
                r = FOV_RADIUS
                x = player_cx + r * math.cos(a)
                y = player_cy + r * math.sin(a)
            points.append((x, y))
        self._last_fov_params = (player_pos, dir_angle, (cam_x, cam_y), tuple(sorted((e.x, e.y) for e in enemies)) if enemies else None)
        self._fov_recalc_cooldown = self._FOV_RECALC_DELAY
        
        # Проверяем валидность точек перед сохранением
        if points and len(points) > 2:
            # Проверяем, что все точки - это пары чисел
            valid_points = []
            for point in points:
                if isinstance(point, (tuple, list)) and len(point) == 2:
                    x, y = point
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        valid_points.append((int(x), int(y)))
            
            if len(valid_points) > 2:
                self.last_fov_poly = valid_points
                self.lit_enemies = lit_enemies
                return valid_points, lit_enemies
        
        # Если точки невалидны, возвращаем None
        self.last_fov_poly = None
        self.lit_enemies = set()
        return None, set()

    def draw_light(self, surface, cam_x, cam_y, obstacles, tile_width, tile_height, darkness_enabled, enemies=None):
        # Отрисовка фонарика/FOV и затемнения
        import math
        INTERNAL_WIDTH = 1024
        INTERNAL_HEIGHT = 1024
        DARK_ALPHA = 160
        PLAYER_LIGHT_RADIUS = 50
        if not darkness_enabled:
            return
        if self.flashlight_enabled:
            # Фонарик: сектор обзора (raycasting)
            FOV_ALPHA = 128  # уровень прозрачности сектора (0-255)
            fov_mask = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            fov_mask.fill((0, 0, 0, FOV_ALPHA))
            points, lit_enemies = self._compute_fov_polygon(cam_x, cam_y, obstacles, tile_width, tile_height, enemies=enemies)
            
            # Проверяем валидность точек
            if points and len(points) > 2:
                # Проверяем, что все точки - это пары чисел
                valid_points = []
                for point in points:
                    if isinstance(point, (tuple, list)) and len(point) == 2:
                        x, y = point
                        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                            valid_points.append((int(x), int(y)))
                
                if len(valid_points) > 2:
                    self.last_fov_poly = valid_points
                    self.lit_enemies = lit_enemies
                    player_cx = int(self.x - cam_x + tile_width // 2)
                    player_cy = int(self.y - cam_y + tile_height // 2)
                    pygame.draw.polygon(fov_mask, (0, 0, 0, 0), valid_points)
                    # Также делаем светлый круг вокруг игрока
                    pygame.draw.circle(fov_mask, (0, 0, 0, 0), (player_cx, player_cy), PLAYER_LIGHT_RADIUS)
                    surface.blit(fov_mask, (0, 0))
                else:
                    # Если точки невалидны, сбрасываем кэш
                    self.last_fov_poly = None
                    self._last_fov_params = None
            else:
                # Если точек нет или их мало, сбрасываем кэш
                self.last_fov_poly = None
                self._last_fov_params = None
        else:
            # Просто светлый круг вокруг игрока
            darkness_mask = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            darkness_mask.fill((0, 0, 0, DARK_ALPHA))
            player_cx = int(self.x - cam_x + tile_width // 2)
            player_cy = int(self.y - cam_y + tile_height // 2)
            pygame.draw.circle(darkness_mask, (0, 0, 0, 0), (player_cx, player_cy), PLAYER_LIGHT_RADIUS)
            surface.blit(darkness_mask, (0, 0))
            self.last_fov_poly = None  # Нет сектора — нет полигона
            self.lit_enemies = set()

    def get_fov_polygon(self, cam_x, cam_y, angle=None, enemies=None):
        # Если явно передан angle — пересчитать, иначе вернуть кэш
        if angle is not None or self.last_fov_poly is None:
            # Для врагов всегда нужен актуальный obstacles/tile_width/tile_height, используем self
            poly, _ = self._compute_fov_polygon(cam_x, cam_y, self.obstacles, self.tile_width, self.tile_height, angle, enemies)
            return poly if poly is not None else []
        return self.last_fov_poly if self.last_fov_poly is not None else []

    def draw(self, surface, cam_x, cam_y, player_anim):
        # Нарисовать хитбокс игрока
        hitbox_rect = pygame.Rect(
            self.x - cam_x,
            self.y - cam_y,
            self.tile_width,
            self.tile_height
        )
       # pygame.draw.rect(surface, (255, 0, 0), hitbox_rect, 2)
        # Нарисовать анимацию игрока
        px = self.x - cam_x
        py = self.y - cam_y
        player_anim.draw(surface, px, py - 32)

