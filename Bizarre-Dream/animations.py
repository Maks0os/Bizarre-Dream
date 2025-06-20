import pygame

class BitmapFont:
    def __init__(self, image_path, char_map, char_width=40, char_height=24):
        self.image = pygame.image.load(image_path).convert_alpha()
        self.char_map = char_map
        self.char_width = char_width
        self.char_height = char_height
        self.chars_per_row = 16  # 16 символов в строке
        
    def get_char_rect(self, char):
        """Получить прямоугольник символа в изображении"""
        if char not in self.char_map:
            char = '?'  # Заменяем неизвестные символы на ?
        
        char_index = self.char_map.index(char)
        row = char_index // self.chars_per_row
        col = char_index % self.chars_per_row
        
        x = col * self.char_width
        y = row * self.char_height
        
        return pygame.Rect(x, y, self.char_width, self.char_height)
    
    def render_text(self, text, color=(255, 255, 255)):
        """Отрисовать текст с помощью шрифта-изображения"""
        if not text:
            return pygame.Surface((0, 0), pygame.SRCALPHA)
        
        # Создаем поверхность для текста
        text_width = len(text) * self.char_width
        text_height = self.char_height
        text_surface = pygame.Surface((text_width, text_height), pygame.SRCALPHA)
        
        # Отрисовываем каждый символ
        for i, char in enumerate(text):
            char_rect = self.get_char_rect(char)
            x = i * self.char_width
            text_surface.blit(self.image, (x, 0), char_rect)
        
        # размер текста
        scale_factor = 0.5
        scaled_width = int(text_width * scale_factor)
        scaled_height = int(text_height * scale_factor)
        scaled_surface = pygame.transform.scale(text_surface, (scaled_width, scaled_height))
        
        return scaled_surface

class Animation:
    FRAME_WIDTH = 64
    FRAME_HEIGHT = 64

    def __init__(self, image, num_frames, frame_duration, frame_start=(0, 0)):
        self.image = image
        self.num_frames = num_frames
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.counter = 0
        self.frame_start = frame_start  # (x, y) tuple

    def update(self):
        self.counter += 1
        if self.counter >= self.frame_duration:
            self.current_frame = (self.current_frame + 1) % self.num_frames
            self.counter = 0

    def get_frame_rect(self, frame_index):
        x0, y0 = self.frame_start
        return pygame.Rect(
            x0,
            y0 + frame_index * self.FRAME_HEIGHT,
            self.FRAME_WIDTH,
            self.FRAME_HEIGHT
        )

    def draw(self, surface, x, y):
        frame_rect = self.get_frame_rect(self.current_frame)
        surface.blit(self.image, (x, y), frame_rect)

class DoorAnimation(Animation):
    def __init__(self, image):
        # 3 frames vertically, starting at frame_start
        super().__init__(image, num_frames=3, frame_duration=10, frame_start=(0, 0))

class SpecialDoorAnimation(Animation):
    def __init__(self, image):
        # 3 frames vertically, starting at (256, 0)
        super().__init__(image, num_frames=3, frame_duration=10, frame_start=(256, 0))
class LiftDoorAnimation(Animation):
    def __init__(self, image):
        # 3 frames vertically, starting at (256, 0)
        super().__init__(image, num_frames=3, frame_duration=10, frame_start=(128, 0))
class LiftDoorBotAnimation(Animation):
    def __init__(self, image):
        # 3 frames vertically, starting at (256, 0)
        super().__init__(image, num_frames=3, frame_duration=10, frame_start=(320, 0))
class CloseDoorAnimation(Animation):
    def __init__(self, image):
        # 3 frames vertically, starting at (256, 0)
        super().__init__(image, num_frames=3, frame_duration=10, frame_start=(400, 64))
class PlayerAnimation(Animation):
    FRAME_WIDTH = 32
    def __init__(self, image, frame_coords, frame_duration=8):
        # frame_coords: dict with keys ('down', 'left', 'right', 'up'), each value is a list of 3 (x, y) tuples
        super().__init__(image, num_frames=3, frame_duration=frame_duration)
        self.frame_coords = frame_coords  # e.g. {'down': [(x0,y0), (x1,y1), (x2,y2)], ...}
        self.direction = 'down'  # 'down', 'left', 'right', 'up'
        self.anim_index = 0  # 0: standing, 1: left leg, 2: right leg

    def set_direction(self, direction):
        if direction in self.frame_coords:
            self.direction = direction

    def set_anim_index(self, index):
        self.anim_index = index % 3

    def update(self):
        self.counter += 1
        if self.counter >= self.frame_duration:
            self.anim_index = (self.anim_index + 1) % 3
            self.counter = 0

    def draw(self, surface, x, y):
        frame_pos = self.frame_coords[self.direction][self.anim_index]
        frame_rect = pygame.Rect(frame_pos[0], frame_pos[1], self.FRAME_WIDTH, self.FRAME_HEIGHT)
        surface.blit(self.image, (x, y), frame_rect)

class TextMessageAnimation(Animation):
    def __init__(self, image, screen_width, screen_height):
        # Анимация выдвижения снизу вверх
        super().__init__(image, num_frames=1, frame_duration=1)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.target_y = screen_height - 100  # Позиция, куда должен выдвинуться фон
        self.current_y = screen_height  # Начинаем снизу экрана
        self.animation_speed = 8  # Скорость выдвижения
        self.is_visible = False
        self.message = ""
        self.font = get_bitmap_font()  # Используем bitmap шрифт
        self.text_color = (255, 255, 255)  # Белый цвет текста
        self.show_duration = 80  # Длительность показа сообщения (3 секунды при 60 FPS)
        self.show_counter = 0
        self.is_sliding_out = False  # Флаг для анимации задвижения
        
    def show_message(self, message):
        """Показать сообщение с анимацией"""
        self.message = message
        self.is_visible = True
        self.is_sliding_out = False
        self.current_y = self.screen_height  # Начинаем снизу
        self.show_counter = 0
        
    def update(self):
        if not self.is_visible:
            return
            
        self.show_counter += 1
        
        # Анимация выдвижения
        if not self.is_sliding_out and self.current_y > self.target_y:
            self.current_y -= self.animation_speed
            if self.current_y < self.target_y:
                self.current_y = self.target_y
                
        # Автоматическое задвижение после показа
        if self.show_counter >= self.show_duration and not self.is_sliding_out:
            self.is_sliding_out = True
            
        # Анимация задвижения
        if self.is_sliding_out:
            self.current_y += self.animation_speed
            if self.current_y >= self.screen_height:
                self.is_visible = False
                self.is_sliding_out = False
                self.current_y = self.screen_height
            
    def draw(self, surface, x=None, y=None):
        if not self.is_visible:
            return
            
        # Рисуем фон
        bg_rect = self.image.get_rect()
        bg_rect.centerx = self.screen_width // 2
        bg_rect.bottom = self.current_y
        surface.blit(self.image, bg_rect)
        
        # Рисуем текст
        if self.message:
            text_surface = self.font.render_text(self.message, self.text_color)
            text_rect = text_surface.get_rect()
            text_rect.centerx = self.screen_width // 2
            text_rect.centery = self.current_y - bg_rect.height // 2
            surface.blit(text_surface, text_rect)


_door_anim_image = None
_door_anim = None
_special_door_anim = None
_lift_door_anim = None
_lift_doorbot_anim = None
_close_door_anim = None
_player_anim_image = None
_player_anim = None
_text_message_image = None
_text_message_anim = None
_bitmap_font = None

def get_door_anim_image():
    global _door_anim_image
    if _door_anim_image is None:
        _door_anim_image = pygame.image.load('img/animations/!Doors.png').convert_alpha()
    return _door_anim_image

def get_door_animation():
    global _door_anim
    if _door_anim is None:
        _door_anim = DoorAnimation(get_door_anim_image())
    return _door_anim

def get_special_door_animation():
    global _special_door_anim
    if _special_door_anim is None:
        _special_door_anim = SpecialDoorAnimation(get_door_anim_image())
    return _special_door_anim
def get_lift_door_animation():
    global _lift_door_anim
    if _lift_door_anim is None:
        _lift_door_anim = LiftDoorAnimation(get_door_anim_image())
    return _lift_door_anim
def get_liftbot_door_animation():
    global _lift_doorbot_anim
    if _lift_doorbot_anim is None:
        _lift_doorbot_anim = LiftDoorBotAnimation(get_door_anim_image())
    return _lift_doorbot_anim
def get_close_door_animation():
    global _close_door_anim
    if _close_door_anim is None:
        _close_door_anim = CloseDoorAnimation(get_door_anim_image())
    return _close_door_anim
def get_player_anim_image():
    global _player_anim_image
    if _player_anim_image is None:
        _player_anim_image = pygame.image.load('img/animations/!Player.png').convert_alpha()
    return _player_anim_image

def get_player_animation(frame_coords, frame_duration=8):
    global _player_anim
    if _player_anim is None:
        _player_anim = PlayerAnimation(get_player_anim_image(), frame_coords, frame_duration)
    return _player_anim
def get_text_message_image():
    global _text_message_image
    if _text_message_image is None:
        _text_message_image = pygame.image.load('img/animations/text_back.png').convert_alpha()
    return _text_message_image

def get_bitmap_font():
    global _bitmap_font
    if _bitmap_font is None:
        char_map = ("0123456789?!ABCD"
                    "EFGHIJKLMNOPQRST"
                    "UVWXYZАБВГДЕЗИКЛ"
                    "МНОПРСТШЩФЫЦЪЖЮУ"
                    "ХЧЬЭЯ><: "
                    ).replace('\n', '')
        _bitmap_font = BitmapFont('img/animations/font.png', char_map, 40, 24)
    return _bitmap_font

def get_text_message_animation(screen_width, screen_height):
    global _text_message_anim
    if _text_message_anim is None:
        _text_message_anim = TextMessageAnimation(get_text_message_image(), screen_width, screen_height)
    return _text_message_anim
