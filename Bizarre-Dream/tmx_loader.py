import pytmx
import pygame

def load_tmx_map(filename):
    """
    Loads a Tiled TMX map file and returns the tmx_data object.
    Ensures Pygame display is initialized before loading.
    """
    if not pygame.display.get_init() or not pygame.display.get_surface():
        pygame.display.set_mode((1, 1))  # Минимальное окно для конвертации изображений
    return pytmx.util_pygame.load_pygame(filename)

def draw_tmx_map(screen, tmx_data, offset_x=0, offset_y=0):
    """
    Draws all visible tile layers of the TMX map to the given Pygame surface, with an optional offset.
    """
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(tile, (offset_x + x * tmx_data.tilewidth, offset_y + y * tmx_data.tileheight))

def get_collision_rects(tmx_data):
    """
    Returns a list of pygame.Rect for all objects in the first object layer (collision layer).
    """
    collision_rects = []
    for layer in tmx_data.layers:
        if isinstance(layer, pytmx.TiledObjectGroup):
            for obj in layer:
                rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                collision_rects.append(rect)
            break
    return collision_rects

def get_trigger_rects(tmx_data):
    """
    Returns a list of pygame.Rect for all objects in the first object layer named 'trigg'.
    """
    trigger_rects = []
    for layer in tmx_data.layers:
        if isinstance(layer, pytmx.TiledObjectGroup) and layer.name == 'trigg':
            for obj in layer:
                rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                trigger_rects.append(rect)
            break
    return trigger_rects

def get_trigger_infos(tmx_data):
    triggers = []
    for layer in tmx_data.layers:
        if isinstance(layer, pytmx.TiledObjectGroup) and layer.name == 'trigg':
            for obj in layer:
                info = {
                    "rect": pygame.Rect(obj.x, obj.y, obj.width, obj.height),
                    "dest_map": getattr(obj, "name", None),
                    "dest_x": getattr(obj, "dest_x", None),
                    "dest_y": getattr(obj, "dest_y", None)
                }
                triggers.append(info)

            break
    return triggers

def get_enemy_infos(tmx_data):
    """
    Возвращает список врагов из слоя 'enem'.
    Каждый враг — dict с ключами: name, x, y, width, height
    """
    enemies = []
    for layer in tmx_data.layers:
        if isinstance(layer, pytmx.TiledObjectGroup) and layer.name == 'enem':
            for obj in layer:
                info = {
                    'name': getattr(obj, 'name', None),
                    'x': obj.x,
                    'y': obj.y,
                    'width': obj.width,
                    'height': obj.height
                }
                enemies.append(info)
            break
    return enemies