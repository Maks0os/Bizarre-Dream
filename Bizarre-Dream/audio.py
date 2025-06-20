import pygame
import os
import random

class AudioManager:
    def __init__(self):
        """Инициализация менеджера звуков"""
        pygame.mixer.init()
        
        # Настройки звука
        self.sound_volume = 0.7

        # Словари для хранения звуков
        self.sounds = {}
        # Загрузка звуков
        self.load_sounds()
        
    def load_sounds(self):
        """Загрузка всех звуковых файлов"""
        sound_dir = "sound"
        
        # Звуки шагов по разным поверхностям
        self.sounds['walk_tile1'] = self.load_sound(os.path.join(sound_dir, "WalkSteps_Tile1.ogg"))
        self.sounds['walk_tile2'] = self.load_sound(os.path.join(sound_dir, "WalkSteps_Tile2.ogg"))
        self.sounds['walk_tile3'] = self.load_sound(os.path.join(sound_dir, "WalkSteps_Tile3.ogg"))
        self.sounds['walk_tile4'] = self.load_sound(os.path.join(sound_dir, "WalkSteps_Tile4.ogg"))
        
        # Звуки взаимодействий
        self.sounds['switch'] = self.load_sound(os.path.join(sound_dir, "Switch1.ogg"))
        self.sounds['door_open'] = self.load_sound(os.path.join(sound_dir, "DoorOpenNormal.ogg"))
        self.sounds['door_cant_open'] = self.load_sound(os.path.join(sound_dir, "Door_CantOpen.ogg"))
        self.sounds['cursor_confirm'] = self.load_sound(os.path.join(sound_dir, "Cursor_Confirm.ogg"))
        
        # Звуки врагов
        self.sounds['enemy_scream'] = self.load_sound(os.path.join(sound_dir, "enemy_scream.wav"))
        
        # Звук концовки игры
        self.sounds['game_over'] = self.load_sound(os.path.join(sound_dir, "game_over.wav"))
        
        # Звук хорошей концовки
        self.sounds['angelic'] = self.load_sound(os.path.join(sound_dir, "Angelic.ogg"))
        
        # Звук телефона
        self.sounds['domphone'] = self.load_sound(os.path.join(sound_dir, "domphone.wav"))
        
        # Звук лифта
        self.sounds['elevator_door'] = self.load_sound(os.path.join(sound_dir, "Elevator door.wav"))
        
    def load_sound(self, filepath):
        """Загрузка отдельного звукового файла"""
        try:
            sound = pygame.mixer.Sound(filepath)
            sound.set_volume(self.sound_volume)
            return sound
        except Exception as e:
            print(f"Ошибка загрузки звука {filepath}: {e}")
            return None
            
    def play_sound(self, sound_name):
        """Воспроизведение звука по имени"""
        if sound_name in self.sounds and self.sounds[sound_name]:
            self.sounds[sound_name].play()
            
    def play_walk_sound(self, tile_type=None):
        """Воспроизведение звука шагов с выбором типа поверхности"""
        if tile_type and f'walk_tile{tile_type}' in self.sounds:
            self.play_sound(f'walk_tile{tile_type}')
        else:
            # Случайный звук шагов, если тип не указан
            walk_sounds = ['walk_tile1', 'walk_tile2', 'walk_tile3', 'walk_tile4']
            random_sound = random.choice(walk_sounds)
            self.play_sound(random_sound)
            
    def play_door_sound(self, can_open=True):
        """Воспроизведение звука двери"""
        if can_open:
            self.play_sound('door_open')
        else:
            self.play_sound('door_cant_open')
            
    def play_switch_sound(self):
        """Воспроизведение звука переключателя"""
        self.play_sound('switch')
        
    def play_cursor_sound(self):
        """Воспроизведение звука подтверждения курсора"""
        self.play_sound('cursor_confirm')
        
    def play_enemy_scream(self):
        """Воспроизведение звука крика врага"""
        self.play_sound('enemy_scream')
        
    def play_game_over_sound(self):
        """Воспроизведение звука концовки игры"""
        self.play_sound('game_over')
        
    def play_angelic_sound(self):
        """Воспроизведение звука хорошей концовки"""
        self.play_sound('angelic')
        
    def play_domphone_sound(self):
        """Воспроизведение звука телефона"""
        self.play_sound('domphone')
        
    def play_elevator_door_sound(self):
        """Воспроизведение звука лифта"""
        self.play_sound('elevator_door')
        
    def stop_sound(self, sound_name):
        """Остановка конкретного звука"""
        if sound_name in self.sounds and self.sounds[sound_name]:
            self.sounds[sound_name].stop()
            
    def stop_enemy_scream(self):
        """Остановка звука крика врага"""
        self.stop_sound('enemy_scream')
        
    def set_sound_volume(self, volume):
        """Установка громкости звуков (0.0 - 1.0)"""
        self.sound_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            if sound:
                sound.set_volume(self.sound_volume)

    def cleanup(self):
        """Очистка ресурсов"""
        pygame.mixer.quit()


# Глобальный экземпляр менеджера звуков
_audio_manager = None

def get_audio_manager():
    """Получение глобального экземпляра менеджера звуков"""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioManager()
    return _audio_manager
