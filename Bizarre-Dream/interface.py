import pygame
import os
import controls
from animations import get_text_message_animation
from audio import get_audio_manager


class TextMessageManager:
    def __init__(self, screen_width, screen_height):
        self.text_animation = get_text_message_animation(screen_width, screen_height)
        
    def show_message(self, message):
        """Показать текстовое сообщение"""
        self.text_animation.show_message(message)
        
    def update(self):
        """Обновить анимацию сообщения"""
        self.text_animation.update()
        
    def draw(self, surface):
        """Отрисовать сообщение"""
        self.text_animation.draw(surface)


class ElevatorMenu:
    def __init__(self, base_image_path, screen_size):
        # Загрузить основное изображение меню
        self.base_image = pygame.image.load(os.path.join('img', 'elevator_menu', 'elevator_menu-export-export.png')).convert_alpha()
        self.screen_size = screen_size
        self.visible = False

        # Центрировать меню и сдвинуть влево на 200 пикселей
        self.rect = self.base_image.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2))
        self.rect.x -= 300

        # Загрузить все изображения для наведения
        self.hover_images = {}
        for i in range(0, 11):  # 1 to 11
            path = os.path.join('img', 'elevator_menu', f'elevator_menu-export-export{i}.png')
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                self.hover_images[i] = img

        # Инициализировать зоны (36x36 пикселей каждая)
        self.zones = {}  # Will be populated with {zone_id: pygame.Rect}
        self.current_hover = None

        # Пользовательский курсор
        pygame.mouse.set_visible(False)  # Always hide system cursor, пользовательский рисуем сами
        self.on_floor_selected = None  # Callback for floor selection
        
        # Audio manager
        self.audio_manager = get_audio_manager()

    def add_zone(self, zone_id, x, y):
        """Add a clickable/hoverable zone. Coordinates are relative to menu position."""
        # Размер зоны (оригинальный)
        zone_size = 36  # Original size
        rect = pygame.Rect(self.rect.x + x, self.rect.y + y, zone_size, zone_size)
        self.zones[zone_id] = rect

    def show(self):
        self.visible = True
        # не трогаем системный курсор

    def hide(self):
        self.visible = False
        # не трогаем системный курсор

    def set_floor_callback(self, callback):
        """Set the callback function for floor selection"""
        self.on_floor_selected = callback

    def handle_event(self, event):
        if not self.visible:
            return

        controls.handle_event(event, self.zones)
        self.current_hover = controls.get_hover_zone()
        mouse_buttons = controls.get_mouse_buttons()
        if mouse_buttons[0] and self.current_hover is not None:
            self.audio_manager.play_cursor_sound()  # Звук подтверждения курсора
            if self.on_floor_selected:
                self.on_floor_selected(self.current_hover)

    def draw(self, surface):
        if not self.visible:
            return

        # Нарисовать основное меню или состояние наведения
        if self.current_hover and self.current_hover in self.hover_images:
            surface.blit(self.hover_images[self.current_hover], self.rect)
        else:
            surface.blit(self.base_image, self.rect)

        # Нарисовать зоны (простые прямоугольники)
       # for zone_rect in self.zones.values():
           # pygame.draw.rect(surface, (255, 0, 0, 128), zone_rect, 1)

    def get_zone_count(self):
        """Return the number of configured zones"""
        return len(self.zones)