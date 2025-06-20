import pygame


button_states = {
    'up': False,
    'down': False,
    'left': False,
    'right': False,
    'e': False,
    'escape': False,
    'w': False,
    'a': False,
    's': False,
    'd': False,
    'f': False
}


mouse_pos = (0, 0)
mouse_buttons = [False, False, False]
hover_zone = None

def update_button_states(event):
    """
    Updates the button states dictionary based on pygame events.
    Call this for each event in the game loop.
    """
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_UP:
            button_states['up'] = True
        elif event.key == pygame.K_DOWN:
            button_states['down'] = True
        elif event.key == pygame.K_LEFT:
            button_states['left'] = True
        elif event.key == pygame.K_RIGHT:
            button_states['right'] = True
        elif event.key == pygame.K_e:
            button_states['e'] = True
        elif event.key == pygame.K_ESCAPE:
            button_states['escape'] = True
        elif event.key == pygame.K_w:
            button_states['w'] = True
        elif event.key == pygame.K_a:
            button_states['a'] = True
        elif event.key == pygame.K_s:
            button_states['s'] = True
        elif event.key == pygame.K_d:
            button_states['d'] = True
        elif event.key == pygame.K_f:
            button_states['f'] = True
    elif event.type == pygame.KEYUP:
        if event.key == pygame.K_UP:
            button_states['up'] = False
        elif event.key == pygame.K_DOWN:
            button_states['down'] = False
        elif event.key == pygame.K_LEFT:
            button_states['left'] = False
        elif event.key == pygame.K_RIGHT:
            button_states['right'] = False
        elif event.key == pygame.K_e:
            button_states['e'] = False
        elif event.key == pygame.K_ESCAPE:
            button_states['escape'] = False
        elif event.key == pygame.K_w:
            button_states['w'] = False
        elif event.key == pygame.K_a:
            button_states['a'] = False
        elif event.key == pygame.K_s:
            button_states['s'] = False
        elif event.key == pygame.K_d:
            button_states['d'] = False
        elif event.key == pygame.K_f:
            button_states['f'] = False

def get_button_states():
    """
    Returns the current button states dictionary.
    """
    return button_states

def is_button_pressed(button_name):
    """
    Returns True if the specified button is currently pressed.
    """
    return button_states.get(button_name, False)

def reset_button_states():
    """
    Resets all button states to False.
    """
    for button in button_states:
        button_states[button] = False

def handle_event(event, zones=None):
    """
    Universal event handler for keyboard and mouse.
    Updates button states, mouse position, mouse button states, and hover/click zones if zones are provided.
    """
    global mouse_pos, mouse_buttons, hover_zone
    update_button_states(event)
    if event.type == pygame.MOUSEMOTION:
        mouse_pos = event.pos
        hover_zone = None
        if zones:
            for zone_id, zone_rect in zones.items():
                if zone_rect.collidepoint(mouse_pos):
                    hover_zone = zone_id
                    break
    elif event.type == pygame.MOUSEBUTTONDOWN:
        if event.button in (1, 2, 3):
            mouse_buttons[event.button - 1] = True
            if zones:
                for zone_id, zone_rect in zones.items():
                    if zone_rect.collidepoint(event.pos):
                        hover_zone = zone_id
                        break
    elif event.type == pygame.MOUSEBUTTONUP:
        if event.button in (1, 2, 3):
            mouse_buttons[event.button - 1] = False

def get_mouse_pos():
    return mouse_pos

def get_mouse_buttons():
    return mouse_buttons

def get_hover_zone():
    return hover_zone