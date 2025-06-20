import pygame
import sys
from controls import update_button_states, is_button_pressed, get_mouse_pos, handle_event
from tmx_loader import load_tmx_map, draw_tmx_map, get_collision_rects, get_trigger_infos, get_enemy_infos
from animations import get_door_animation, get_special_door_animation, get_lift_door_animation, \
get_liftbot_door_animation, get_player_animation, get_close_door_animation, get_text_message_image, get_bitmap_font
from view import Camera
from interface import ElevatorMenu, TextMessageManager
from audio import get_audio_manager
import re
import os
from enemy import Enemy
from player import Player

# Create constant screen system
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 1024
FPS = 60
HITBOX_COLOR = (255, 0, 0)  # Красный цвет для хитбокса игрока
COLLISION_COLOR = (0, 0, 255, 0)  # Полупрозрачный синий для объектов-коллизий

# Constant internal resolution - never changes
INTERNAL_WIDTH = 1024
INTERNAL_HEIGHT = 1024

DARK_MAPS = ['map1']  # список карт с затемнением (без .tmx)
DARK_ALPHA = 160  # уровень прозрачности затемнения (0-255)
PLAYER_LIGHT_RADIUS = 50  # радиус светлого круга вокруг игрока

class GameState:
    def __init__(self, map_file, player_pos):
        self.map_file = map_file
        self.player_pos = player_pos 
        self.direction = None
        self.key_held = False
        self.animating_trigger = None
        self.door_anim_frame = 0
        self.door_anim_counter = 0
        self.door_anim_total_frames = 3
        self.door_anim_frame_duration = 5
        self.door_anim_done = False
        self.pending_trigger = None
        
        # Game ending state
        self.game_ending = False
        self.ending_type = None  # 'death', 'victory', etc.
        self.ending_image = None
        self.ending_fade_alpha = 0
        self.ending_fade_speed = 5
        self.ending_image_alpha = 0
        self.ending_image_fade_speed = 3
        
        # Sofa dialog state
        self.sofa_dialog_active = False
        self.sofa_dialog_choice = None  # None, 'yes', 'no'
        
        # Phone sound repeat state
        self.phone_sound_active = False
        self.phone_sound_timer = 0
        self.phone_sound_interval = 300  # 5 секунд при 60 FPS
        
        # Elevator system
        self.selected_floor = None
        self.current_floor = None  # Current floor we're on
        # Floor to map mapping - only numeric floors
        self.floor_to_map = {
            10: "map0",
            1: "map1",
            2: "map2",
            3: "map3",
            4: "map4",
            5: "map5",
            6: "map6",
            7: "map7",
            8: "map8",
            9: "map9"
        }
        # Reverse mapping for looking up floor by map
        self.map_to_floor = {v: k for k, v in self.floor_to_map.items()}
        # Elevator menu (save menu)
        self.elevator_menu = ElevatorMenu('img/elevator_menu/elevator_menu-export-export.png', (INTERNAL_WIDTH, INTERNAL_HEIGHT))
        self.elevator_menu.set_floor_callback(self.select_floor)  # Use our method
        self.menu_active = False

        # Text message manager
        self.text_message_manager = TextMessageManager(INTERNAL_WIDTH, INTERNAL_HEIGHT)

        # Audio manager
        self.audio_manager = get_audio_manager()

        # Configure menu zones - only for available floors
        menu_zones = {
            1: (57, 357),
            2: (57, 282),
            3: (57, 207),
            4: (57, 132),
            5: (57, 57),
            10: (207, 357),
            6: (207, 282),
            7: (207, 207),
            8: (207, 132),
            9: (207, 57),
        }

        for zone_id, (x, y) in menu_zones.items():
            self.elevator_menu.add_zone(zone_id, x, y)

        self.load_map()
        
        # New smooth camera with pixel-based dead zone
        self.camera = Camera(
            INTERNAL_WIDTH, INTERNAL_HEIGHT,
            self.tile_width, self.tile_height,
            zone_tiles=10, smoothing=0.15
        )
        # Fade state
        self.fading = False
        self.fade_in = False
        self.fade_out = False
        self.fade_alpha = 0
        self.fade_speed = 7  # Higher is faster (0-255 per frame)
        self.next_map_info = None  # (dest_map_file, pos)
        # --- Player Animation ---
        frame_coords = {
            'down': [(32, 0), (0, 0), (64, 0)],
            'left': [(32, 64), (0, 64), (64, 64)],
            'right': [(32, 128), (0, 128), (64, 128)],
            'up': [(32, 192), (0, 192), (64, 192)]
        }
        self.anim_speed = 12
        self.player_anim = get_player_animation(frame_coords, frame_duration=self.anim_speed)
        # Игрок
          # будет создан в load_map
        map_name = os.path.basename(self.map_file).replace('.tmx', '')
        self.darkness_enabled = map_name in DARK_MAPS
        self._rightm_lock = False  # Для предотвращения спама сообщения
        # Elevator sound lock
        self._elevator_lock = False  # Для предотвращения спама звука лифта

    def load_map(self):
        self.tmx_data = load_tmx_map(self.map_file)
        self.collision_rects = get_collision_rects(self.tmx_data)
        self.trigger_infos = get_trigger_infos(self.tmx_data)
        self.tile_width = self.tmx_data.tilewidth
        self.tile_height = self.tmx_data.tileheight
        self.grid_width = self.tmx_data.width
        self.grid_height = self.tmx_data.height
        self.map_pixel_width = self.grid_width * self.tile_width
        self.map_pixel_height = self.grid_height * self.tile_height
        self.obstacles = self.build_obstacle_set(self.collision_rects, self.tile_width, self.tile_height)
        # Игрок
        self.player = Player(
            x=self.player_pos[0] * self.tile_width,
            y=self.player_pos[1] * self.tile_height,
            tile_width=self.tile_width,
            tile_height=self.tile_height,
            obstacles=self.obstacles
        )
        # Загрузка врагов
        self.enemies = []
        enemy_infos = get_enemy_infos(self.tmx_data)
        for einfo in enemy_infos:
            def player_center():
                return self.player.get_center()
            def get_fov_poly():
                return self.player.get_fov_polygon(self.camera.offset_x, self.camera.offset_y)
            enemy = Enemy(einfo['x'], einfo['y'], player_center, get_fov_poly, self.tile_width, self.tile_height, self.obstacles)
            enemy.player = self.player  # <--- добавлено для корректной работы is_in_fov
            self.enemies.append(enemy)
        # Determine current floor from map filename
        map_name = os.path.basename(self.map_file).replace('.tmx', '')
        if map_name in self.map_to_floor:
            self.current_floor = self.map_to_floor[map_name]
            
        # Воспроизводим звук телефона только на карте maph
        if map_name == 'maph':
            self.phone_sound_active = True
            self.phone_sound_timer = 0
            self.audio_manager.play_domphone_sound()

    def build_obstacle_set(self, collision_rects, tile_width, tile_height):
        obstacles = set()
        for rect in collision_rects:
            left = rect.left // tile_width
            right = (rect.right - 1) // tile_width
            top = rect.top // tile_height
            bottom = (rect.bottom - 1) // tile_height
            for tx in range(left, right + 1):
                for ty in range(top, bottom + 1):
                    obstacles.add((tx, ty))
        return obstacles

    def is_colliding(self, px, py):
        # Check all tiles covered by the player's rectangle
        left = int(px / self.tile_width)
        right = int((px + self.tile_width - 1) / self.tile_width)
        top = int(py / self.tile_height)
        bottom = int((py + self.tile_height - 1) / self.tile_height)
        for tx in range(left, right + 1):
            for ty in range(top, bottom + 1):
                if (tx, ty) in self.obstacles:
                    return True
        return False

    def is_on_trigger(self, x, y):
        player_rect = pygame.Rect(x * self.tile_width, y * self.tile_height, self.tile_width, self.tile_height)
        for trig in self.trigger_infos:
            if player_rect.colliderect(trig["rect"]):
                # Новая логика: если триггер содержит '_rightm', дверь закрыта
                if 'clos' in trig["dest_map"]:
                    if not self._rightm_lock:
                        self.text_message_manager.show_message("ДВЕРЬ ЗАКРЫТА!")
                        self.audio_manager.play_door_sound(False)  # Звук закрытой двери
                        self._rightm_lock = True
                    return None
                # Обработка триггера дивана
                elif trig["dest_map"] == "sofa":
                    if not self.sofa_dialog_active:
                        self.sofa_dialog_active = True
                        self.sofa_dialog_choice = None
                    return None
                # Звук лифта для триггеров лифта
                elif '_liftom' in trig["dest_map"] or '_lift00' in trig["dest_map"]:
                    if not self._elevator_lock:
                        self.audio_manager.play_elevator_door_sound()  # Звук лифта
                        self._elevator_lock = True
                return trig
        return None

    def handle_event(self, event):
        update_button_states(event)
        
        # Обработка событий во время концовки
        if self.game_ending:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.exit_game()
                elif event.key == pygame.K_RETURN:
                    # Останавливаем звук концовки в зависимости от типа
                    if self.ending_type == 'sleep':
                        self.audio_manager.stop_sound('angelic')
                    else:
                        self.audio_manager.stop_sound('game_over')
                    return self.restart_game()
            return None
            
        # Обработка событий в диалоге дивана
        if self.sofa_dialog_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Нет - продолжаем игру
                    self.sofa_dialog_active = False
                    self.sofa_dialog_choice = 'no'
                elif event.key == pygame.K_RETURN:
                    # Да - запускаем концовку
                    self.sofa_dialog_active = False
                    self.sofa_dialog_choice = 'yes'
                    self.start_ending('sleep', 'img/endings/sleep_ending.png')
            return None
            
        if self.menu_active:
            self.elevator_menu.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.menu_active = False
            return None
        # Сброс блокировки для rightm
        if event.type == pygame.KEYUP and event.key == pygame.K_e:
            self._rightm_lock = False
            self._elevator_lock = False  # Сброс блокировки звука лифта
        return None

    def handle_menu_event(self, event):
        """
        Handles menu-related events. Returns updated menu_active state.
        """
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
        self.elevator_menu.handle_event(event)
        return self.menu_active

    def handle_trigger_event(self, event):
        """
        Handles trigger-related events. Returns updated state variables.
        """
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            tile_x = int(self.player.x // self.tile_width)
            tile_y = int(self.player.y // self.tile_height)
            trig = self.is_on_trigger(tile_x, tile_y)
            if trig and not self.animating_trigger:
                if trig["dest_map"] == "save":
                    self.menu_active = True
                    self.elevator_menu.show()
                    return None
                elif trig["dest_map"] == "sofa":
                    # Диалог дивана обрабатывается в is_on_trigger
                    return None
                self.animating_trigger = trig
                self.door_anim_frame = 0
                self.door_anim_counter = 0
                self.door_anim_done = False
                self.pending_trigger = trig
                return None
        return None

    def update(self):
        # Обработка концовки
        if self.game_ending:
            # Затемнение экрана
            if self.ending_fade_alpha < 255:
                self.ending_fade_alpha += self.ending_fade_speed
                if self.ending_fade_alpha > 255:
                    self.ending_fade_alpha = 255
            
            # Показ изображения концовки
            if self.ending_fade_alpha >= 255 and self.ending_image_alpha < 255:
                self.ending_image_alpha += self.ending_image_fade_speed
                if self.ending_image_alpha > 255:
                    self.ending_image_alpha = 255
            return None
            
        # Обработка диалога дивана
        if self.sofa_dialog_active:
            return None
            
        # Обработка повтора звука телефона
        if self.phone_sound_active:
            self.phone_sound_timer += 1
            if self.phone_sound_timer >= self.phone_sound_interval:
                self.audio_manager.play_domphone_sound()
                self.phone_sound_timer = 0
            
        if self.menu_active:
            return None
        # Smooth camera update
        self.camera.update(self.player.x, self.player.y)

        # Handle fade logic
        if self.fading:
            if self.fade_out:
                self.fade_alpha += self.fade_speed
                if self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    self.fade_out = False
                    # Change map now
                    if self.next_map_info:
                        dest_map_file, pos = self.next_map_info
                        self.__init__(dest_map_file, pos)
                        self.fading = True
                        self.fade_in = True
                        self.fade_alpha = 255
                        self.next_map_info = None
                    else:
                        self.fading = False
            elif self.fade_in:
                self.fade_alpha -= self.fade_speed
                if self.fade_alpha <= 0:
                    self.fade_alpha = 0
                    self.fade_in = False
                    self.fading = False
            return None

        # Handle trigger events
        if is_button_pressed('e'):
            tile_x = int(self.player.x // self.tile_width)
            tile_y = int(self.player.y // self.tile_height)
            trig = self.is_on_trigger(tile_x, tile_y)
            if trig and not self.animating_trigger:
                if trig["dest_map"] == "save":
                    self.menu_active = True
                    self.elevator_menu.show()
                    return None
                elif trig["dest_map"] == "sofa":
                    # Диалог дивана обрабатывается в is_on_trigger
                    return None
                self.animating_trigger = trig
                self.door_anim_frame = 0
                self.door_anim_counter = 0
                self.door_anim_done = False
                self.pending_trigger = trig
                return None

        # Обновление игрока
        self.player.update(cam_x=self.camera.offset_x, cam_y=self.camera.offset_y)
        # Обновление врагов
        for enemy in getattr(self, 'enemies', []):
            enemy.update(self.enemies)
            
        # Проверка столкновения игрока с врагом
        if not self.game_ending:
            player_rect = pygame.Rect(self.player.x, self.player.y, self.tile_width, self.tile_height)
            for enemy in self.enemies:
                enemy_rect = pygame.Rect(enemy.x, enemy.y, self.tile_width, self.tile_height)
                if player_rect.colliderect(enemy_rect):
                    self.start_ending('death')  # Запускаем концовку
                    break
                    
        # Обновление анимации игрока
        self.player_anim.set_direction(self.player.last_move_dir)
        if self.player.is_moving:
            self.player_anim.update()
        else:
            self.player_anim.set_anim_index(0)  # standing

        # Обновление текстовых сообщений
        self.text_message_manager.update()

        # If animating a door, progress animation
        if self.animating_trigger:
            self.door_anim_counter += 1
            if self.door_anim_counter >= self.door_anim_frame_duration:
                self.door_anim_frame += 1
                self.door_anim_counter = 0
                if self.door_anim_frame >= self.door_anim_total_frames:
                    self.door_anim_done = True
            # When animation is done, do the map transition
            if self.door_anim_done and self.pending_trigger:
                trig = self.pending_trigger
                self.animating_trigger = None
                self.pending_trigger = None
                self.door_anim_done = False
                return self.on_trigger(trig)
            return None
        return None

    def draw(self, screen, world_surface):
        world_surface.fill((0, 0, 0))
        cam_x = int(self.camera.offset_x)
        cam_y = int(self.camera.offset_y)

        # Draw map at (0, 0) minus camera offset
        draw_tmx_map(world_surface, self.tmx_data, -cam_x, -cam_y)

        # Draw collision objects
        collision_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        for rect in self.collision_rects:
            offset_rect = rect.copy()
            offset_rect.x -= cam_x
            offset_rect.y -= cam_y
            pygame.draw.rect(collision_surface, COLLISION_COLOR, offset_rect)
        world_surface.blit(collision_surface, (0, 0))

        # Draw doors and other objects...
        for trig in self.trigger_infos:
            if trig["dest_map"] == "save":
                continue  # Do not draw a door for save triggers
            if trig["dest_map"] == "sofa":
                continue  # Do not draw a door for sofa triggers
            if self.animating_trigger and trig == self.animating_trigger:
                continue
            label = trig["dest_map"][-7:]
            tile_x = trig["rect"].x // self.tile_width
            tile_y = trig["rect"].y // self.tile_height
            tile_px = tile_x * self.tile_width - cam_x
            tile_py = tile_y * self.tile_height - cam_y
            if label and label.startswith('_bottom'):
                anim = get_special_door_animation()
                anim.current_frame = 0
                x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                y = tile_py + self.tile_height - anim.FRAME_HEIGHT + (self.tile_height * 2)
            elif label and label.startswith('_lift00'):
                anim = get_lift_door_animation()
                anim.current_frame = 0
                x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                y = tile_py + self.tile_height - anim.FRAME_HEIGHT - self.tile_height
            elif label and label.startswith('_liftom'):
                anim = get_liftbot_door_animation()
                anim.current_frame = 0
                x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                y = tile_py + self.tile_height - anim.FRAME_HEIGHT + (self.tile_height * 2)
            elif label and label.startswith('_rightm'):
                anim = get_close_door_animation()
                anim.current_frame = 0
                x = tile_px + (self.tile_width - anim.FRAME_WIDTH) + (self.tile_height * 2)
                y = tile_py + self.tile_height - anim.FRAME_HEIGHT
            else:
                anim = get_door_animation()
                anim.current_frame = 0
                x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                y = tile_py + self.tile_height - anim.FRAME_HEIGHT - self.tile_height
            anim.draw(world_surface, x, y)
        if self.animating_trigger:
            if self.animating_trigger["dest_map"] != "save":
                label = self.animating_trigger["dest_map"][-7:]

                tile_x = self.animating_trigger["rect"].x // self.tile_width
                tile_y = self.animating_trigger["rect"].y // self.tile_height
                tile_px = tile_x * self.tile_width - cam_x
                tile_py = tile_y * self.tile_height - cam_y
                frame = min(self.door_anim_frame, 2)
                if label and label.startswith('_bottom'):
                    anim = get_special_door_animation()
                    anim.current_frame = frame
                    x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                    y = tile_py + self.tile_height - anim.FRAME_HEIGHT + (self.tile_height * 2)
                elif label and label.startswith('_lift00'):
                    anim = get_lift_door_animation()
                    anim.current_frame = frame
                    x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                    y = tile_py + self.tile_height - anim.FRAME_HEIGHT - self.tile_height
                elif label and label.startswith('_liftom'):
                    anim = get_liftbot_door_animation()
                    anim.current_frame = frame
                    x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                    y = tile_py + self.tile_height - anim.FRAME_HEIGHT + (self.tile_height * 2)
                else:
                    anim = get_door_animation()
                    anim.current_frame = frame
                    x = tile_px + (self.tile_width - anim.FRAME_WIDTH) // 2
                    y = tile_py + self.tile_height - anim.FRAME_HEIGHT - self.tile_height
                anim.draw(world_surface, x, y)
        # Draw player hitbox
        hitbox_rect = pygame.Rect(
            self.player.x - cam_x,
            self.player.y - cam_y,
            self.tile_width,
            self.tile_height
        )
       # pygame.draw.rect(world_surface, HITBOX_COLOR, hitbox_rect, 2)

        # Draw animated player
        px = self.player.x - cam_x
        py = self.player.y - cam_y
        self.player_anim.draw(world_surface, px, py - 32)
        debug_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        # for rect in self.trigger_infos:
        #     offset_rect = rect["rect"].move(-cam_x, -cam_y)
        #     pygame.draw.rect(debug_surface, (255, 0, 0, 100), offset_rect)
        # world_surface.blit(debug_surface, (0, 0))
        # Draw the camera's dead zone for debugging


        # Draw fade overlay if fading
        if self.fading and self.fade_alpha > 0:
            fade_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill((0, 0, 0))
            world_surface.blit(fade_surface, (0, 0))

        # Draw elevator menu if active
        if self.menu_active:
            self.elevator_menu.draw(world_surface)

        # Рисуем игрока
        self.player.draw(world_surface, cam_x, cam_y, self.player_anim)
        # Рисуем врагов
        for enemy in getattr(self, 'enemies', []):
            enemy.draw(world_surface, cam_x, cam_y)

        # --- Логика затемнения и фонарика ---
        if self.darkness_enabled:
            self.player.draw_light(world_surface, cam_x, cam_y, self.obstacles, self.tile_width, self.tile_height, self.darkness_enabled, self.enemies)

        # --- Всегда рисуем пользовательский курсор мыши ---
        mouse_pos = get_mouse_pos()
        pygame.draw.circle(world_surface, (255, 255, 255), mouse_pos, 5)
        pygame.draw.circle(world_surface, (0, 0, 0), mouse_pos, 5, 2)

        # --- Отрисовка текстовых сообщений ---
        self.text_message_manager.draw(world_surface)

        # Отрисовка диалога дивана
        if self.sofa_dialog_active:
            # Затемнение фона
            overlay_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            overlay_surface.fill((0, 0, 0, 128))
            world_surface.blit(overlay_surface, (0, 0))
            
            # Используем существующий фон для текстовых сообщений
            bg_image = get_text_message_image()
            font = get_bitmap_font()
            
            # Создаем поверхность для диалога
            dialog_width = 800
            dialog_height = 200
            dialog_surface = pygame.Surface((dialog_width, dialog_height), pygame.SRCALPHA)
            
            # Масштабируем фон под размер диалога
            scaled_bg = pygame.transform.scale(bg_image, (dialog_width, dialog_height))
            dialog_surface.blit(scaled_bg, (0, 0))
            
            # Рендерим основной текст
            main_text = "ЛУЧШЕ ЛЕЧЬ СПАТЬ И НИКУДА НЕ ИДТИ"
            main_surface = font.render_text(main_text, (255, 255, 255))
            main_rect = main_surface.get_rect(center=(dialog_width // 2, 80))
            dialog_surface.blit(main_surface, main_rect)
            
            # Рендерим инструкции
            instruction_text = "ESC/ENTER"
            instruction_surface = font.render_text(instruction_text, (255, 255, 255))
            instruction_rect = instruction_surface.get_rect(center=(dialog_width // 2, 120))
            dialog_surface.blit(instruction_surface, instruction_rect)
            
            # Размещаем диалог по центру экрана
            dialog_x = (INTERNAL_WIDTH - dialog_width) // 2
            dialog_y = (INTERNAL_HEIGHT - dialog_height) // 2
            world_surface.blit(dialog_surface, (dialog_x, dialog_y))

        # Отрисовка концовки
        if self.game_ending:
            # Затемнение экрана
            if self.ending_fade_alpha > 0:
                fade_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
                fade_surface.set_alpha(self.ending_fade_alpha)
                fade_surface.fill((0, 0, 0))
                world_surface.blit(fade_surface, (0, 0))
            
            # Показ изображения концовки
            if self.ending_image and self.ending_image_alpha > 0:
                # Масштабируем изображение под размер экрана
                scaled_image = pygame.transform.scale(self.ending_image, (INTERNAL_WIDTH, INTERNAL_HEIGHT))
                scaled_image.set_alpha(self.ending_image_alpha)
                world_surface.blit(scaled_image, (0, 0))

    def parse_trigger_name(self, name):
        """
        Пример: maph_bottom_12_23 -> ('maph', 12, 23)
                map1_12_23 -> ('map1', 12, 23)
        """
        # Сначала ищем _bottom с координатами
        match = re.match(r'(.+?)_bottom_(\d+)_(\d+)$', name)
        if match:
            dest_map = match.group(1)
            dest_x = int(match.group(2))
            dest_y = int(match.group(3))
            return dest_map, dest_x, dest_y
        
        # Обычный случай с координатами
        match = re.match(r'(.+?)_(\d+)_(\d+)$', name)
        if match:
            dest_map = match.group(1)
            dest_x = int(match.group(2))
            dest_y = int(match.group(3))
            return dest_map, dest_x, dest_y
        
        # Fallback: если нет координатов, извлекаем базовое имя карты
        # Убираем суффиксы типа _bottom, _liftom, _lift00
        base_name = re.sub(r'_(bottom|liftom|lift00)$', '', name)
        return base_name, None, None

    def on_trigger(self, trig):
        dest_map = trig["dest_map"]
        
        # Handle elevator exit with floor selection check
        if "_lift00" in dest_map:
            if self.selected_floor is None:
                self.text_message_manager.show_message("НАЖМИ КНОПКИ ЭТАЖА!")
                return None
            else:
                # Extract floor from trigger name and check if it matches selected floor
                floor = self.extract_floor_from_trigger(dest_map)
                if floor == self.selected_floor:
                    # Transition to selected floor
                    dest_map_name = self.floor_to_map[floor]
                    print(dest_map_name)
                    exit_pos = self.find_elevator_exit(dest_map_name)
                    print(exit_pos)
                    if exit_pos:
                        self.audio_manager.stop_enemy_scream()  # Останавливаем звук врага
                        self.phone_sound_active = False  # Останавливаем звук телефона
                        # Звук лифта уже воспроизведен в is_on_trigger
                        self.fading = True
                        self.fade_out = True
                        self.fade_in = False
                        self.fade_alpha = 0
                        self.next_map_info = (f"maps/{dest_map_name}.tmx", exit_pos)
                        print(f"Переход на этаж {floor} ({dest_map_name})")
                        self.selected_floor = None  # Reset selection
                    else:
                        print(f"Не найден выход лифта на этаже {floor}")
                else:
                    print(f"Выбран этаж {self.selected_floor}, но триггер для этажа {floor}")
                return None
        

            
        # Новая логика: парсим имя триггера
        dest_map_name, dest_x, dest_y = self.parse_trigger_name(dest_map)
        if dest_x is not None and dest_y is not None:
            pos = (dest_x, dest_y)
        else:
            pos = get_first_trigger_tile(f"maps/{dest_map_name}.tmx")
        self.audio_manager.stop_enemy_scream()  # Останавливаем звук врага
        self.phone_sound_active = False  # Останавливаем звук телефона
        
        # Звук двери только для обычных дверей, не для лифтов
        if '_liftom' not in dest_map:
            self.audio_manager.play_door_sound(True)  # Звук открытия двери
            
        self.fading = True
        self.fade_out = True
        self.fade_in = False
        self.fade_alpha = 0
        self.next_map_info = (f"maps/{dest_map_name}.tmx", pos)
        print(f"Переход на {dest_map_name} ({pos})")
        return None

    def extract_floor_from_trigger(self, trigger_name):
        """
        Extract floor number from trigger name like "map3_lift00" -> 3
        Also handles "map?_lift00" -> current floor
        """
        # Handle placeholder pattern
        if trigger_name == "map?_lift00":
            return self.selected_floor
        
        # Handle regular pattern
        match = re.match(r'map(\d+)_lift00', trigger_name)
        if match:
            return int(match.group(1))
            
        return None

    def find_elevator_exit(self, dest_map):
        """
        Find elevator exit position on destination map
        """
        try:
            tmx_data = load_tmx_map(f"maps/{dest_map}.tmx")
            trigger_infos = get_trigger_infos(tmx_data)
            for trig in trigger_infos:
                if "_liftom" in trig["dest_map"]:
                    rect = trig["rect"]
                    tile_x = rect.x // tmx_data.tilewidth
                    tile_y = rect.y // tmx_data.tileheight
                    return (tile_x, tile_y)
        except Exception as e:
            print(f"Ошибка при поиске выхода лифта на {dest_map}: {e}")
        return None

    def select_floor(self, floor):
        """
        Handle floor selection in elevator menu - activate switch
        """
        # Проверяем, является ли выбранный этаж разрешенным (1 или 3)
        if floor not in [1, 3]:
            self.text_message_manager.show_message("ТЕБЕ СРОЧНО НУЖЕН 1 ЭТАЖ!")

            self.menu_active = False
            return
        
        self.audio_manager.play_switch_sound()  # Звук переключателя
        
        self.selected_floor = floor
        self.text_message_manager.show_message(f"ВЫБРАН ЭТАЖ {floor}")
        self.menu_active = False
        # Switch activated - no transition yet

    def start_ending(self, ending_type, image_path=None):
        """Начать концовку игры"""
        self.game_ending = True
        self.ending_type = ending_type
        self.ending_fade_alpha = 0
        self.ending_image_alpha = 0
        
        # Останавливаем звук врага
        self.audio_manager.stop_enemy_scream()
        
        # Останавливаем звук телефона
        self.phone_sound_active = False
        
        # Воспроизводим звук концовки в зависимости от типа
        if ending_type == 'sleep':
            self.audio_manager.play_angelic_sound()  # Звук хорошей концовки
        else:
            self.audio_manager.play_game_over_sound()  # Звук плохой концовки
        
        # Загружаем изображение концовки
        if image_path:
            try:
                self.ending_image = pygame.image.load(image_path).convert_alpha()
            except:
                # Fallback на стандартное изображение
                try:
                    self.ending_image = pygame.image.load('img/endings/game_over.png').convert_alpha()
                except:
                    self.ending_image = None
        else:
            try:
                self.ending_image = pygame.image.load('img/endings/game_over.png').convert_alpha()
            except:
                self.ending_image = None

    def restart_game(self):
        """Перезапустить игру"""
        return GameState('maps/maph.tmx', (14, 15))
        
    def exit_game(self):
        """Выйти из игры"""
        pygame.quit()
        sys.exit()


def get_first_trigger_tile(map_file):
    tmx_data = load_tmx_map(map_file)
    trigger_infos = get_trigger_infos(tmx_data)
    if trigger_infos:
        rect = trigger_infos[0]["rect"]
        tile_x = rect.x // tmx_data.tilewidth
        tile_y = rect.y // tmx_data.tileheight
        return (tile_x, tile_y)
    return (0, 0)  # fallback if no trigger


def main():
    pygame.init()
    # Create window with resizable flag but maintain internal resolution
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption('Bizarre Dream')
    clock = pygame.time.Clock()
    
    # Create constant internal surface - never changes size
    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
    
    running = True
    # Start player at (5, 5) (5 tiles right and down from top-left)
    current_state = GameState('maps/maph.tmx', (14, 15))
    
    while running:
        for event in pygame.event.get():

            handle_event(event)
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.VIDEORESIZE:
                # Resize window but keep internal resolution constant
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            new_state = current_state.handle_event(event)
            if new_state:
                current_state = new_state
        new_state = current_state.update()
        if new_state:
            current_state = new_state
        
        # Draw everything to internal surface first
        current_state.draw(internal_surface, internal_surface)
        
        # Scale internal surface to fit window
        sw, sh = screen.get_size()
        scale = min(sw / INTERNAL_WIDTH, sh / INTERNAL_HEIGHT)
        scaled_w = int(INTERNAL_WIDTH * scale)
        scaled_h = int(INTERNAL_HEIGHT * scale)
        offset_x = (sw - scaled_w) // 2
        offset_y = (sh - scaled_h) // 2
        
        # Clear screen and draw scaled internal surface
        screen.fill((0, 0, 0))
        scaled_surface = pygame.transform.smoothscale(internal_surface, (scaled_w, scaled_h))
        screen.blit(scaled_surface, (offset_x, offset_y))

        pygame.display.flip()
        clock.tick(FPS)
       # print(clock)
    
    # Очистка ресурсов
    current_state.audio_manager.cleanup()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
