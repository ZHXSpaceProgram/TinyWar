from const import *
import pygame
import math

class Unit:
    def __init__(self, x, y, type, player_id):
        self.x = x
        self.y = y
        self.type = type
        self.player_id = player_id
        self.moved = False
        self.attacked = False # 如果移动后无法攻击，直接设置为True，表示无法选中

        if type in self.PROPERTIES:
            self.movement = self.PROPERTIES[type]['movement']
            self.attack_range = self.PROPERTIES[type]['attack_range']
            self.health = self.max_health = self.PROPERTIES[type]['health']
            self.attack = self.PROPERTIES[type]['attack']
            self.weapon_type = self.PROPERTIES[type]['weapon_type']
            self.armor_type = self.PROPERTIES[type]['armor_type']
            self.move_type = self.PROPERTIES[type]['move_type']
            if 'anti_air' in self.PROPERTIES[type]:
                self.anti_air = self.PROPERTIES[type]['anti_air']

    """
    movement:
    integer

    attack_range:
    (min, max)

    weapon_type / armor_type:
    0: light
    1: median
    2: heavy
    
    move_type:
    (as class MoveType)

    anti_air:
    [Optional]

    description: 
    should be no more than 65 characters
    """
    PROPERTIES = {
        "commando": {
            'movement' : 4,
            'attack_range' : (1, 1),
            'health' : 50,
            'attack' : 22,
            'weapon_type' : 0,
            'armor_type' : 0,
            'move_type' : MoveType.Feet,
            'price' : 10,
            'description' : '123456789|123456789|123456789|123456789|123456789|123456789|12345',
        },
        "tank": {
            'movement' : 6,
            'attack_range' : (1, 1),
            'health' : 70,
            'attack' : 35,
            'weapon_type' : 1,
            'armor_type' : 1,
            'move_type' : MoveType.Track,
            'price' : 35,
            'description' : '123456789|123456789|123456789|123456789|123456789|123456789|'
        },
        "mortar": {
            'movement' : 4,
            'attack_range' : (2, 3),
            'health' : 50,
            'attack' : 40,
            'weapon_type' : 1,
            'armor_type' : 0,
            'move_type' : MoveType.Wheel,
            'price' : 40,
            'description' : 'mortar'
        },
        "fighter": {
            'movement' : 8,
            'attack_range' : (1, 1),
            'health' : 90,
            'attack' : 45,
            'weapon_type' : 1,
            'armor_type' : 1,
            'move_type' : MoveType.Air,
            'anti_air' : True,
            'price' : 65,
            'description' :'fighter'
        },
        "bomber": {
           'movement' : 4,
            'attack_range' : (1, 1),
            'health' : 110,
            'attack' : 50,
            'weapon_type' : 2,
            'armor_type' : 0,
            'move_type' : MoveType.Air,
            'price' : 85,
            'description' :'bomber'
        }
    }


    def draw(self, screen, map_x, map_y):
        x = self.x - map_x
        y = self.y - map_y
        rect = pygame.Rect(
            SCREEN_MARGIN + x * TILE_SIZE,
            SCREEN_MARGIN + y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        if x>=0 and y>=0 and x<MAP_VIEW_SIZE and y<MAP_VIEW_SIZE:
            # 绘制单位
            try:
                # unit_img = pygame.image.load(f"assets/unit/{self.type}_{self.player_id}.png")
                unit_img = preload_unit_imgs[f"{self.type}_{self.player_id}.png"]
                screen.blit(unit_img, rect)
            except:
                # TODO:
                # print(f"Error loading image for unit type {self.type} and player {self.player}.")
                pass
            
            # DEBUG
            if self.type == "factory":
                pygame.draw.rect(screen, (255, 0, 0), rect, 4)

            if not (isinstance(self, Build) and self.build_stacked):
                # 绘制血条
                health_percentage = self.health / self.max_health
                if self.health < self.max_health:
                    health_color = GREEN if health_percentage > 0.5 else YELLOW if health_percentage > 0.25 else RED 
                    health_width = int(TILE_SIZE * health_percentage)
                    health_rect = pygame.Rect(rect.left, rect.top, health_width, 3)
                    pygame.draw.rect(screen, health_color, health_rect)  
                # 行动过的显示半透明遮罩
                if self.attacked:
                    overlay = pygame.Surface((TILE_SIZE, TILE_SIZE))
                    overlay.fill((0, 0, 0))
                    overlay.set_alpha(96) 
                    screen.blit(overlay, rect)
                # 右上角显示血量
                health_percentage = math.ceil(health_percentage*10)
                if health_percentage < 10:
                    font = pygame.font.SysFont('Calibri', 12, True)
                    text = font.render(str(health_percentage), True, WHITE)
                    screen.blit(text, (rect.right - 7, rect.top))
    

class Build(Unit):
    def __init__(self, x, y, type, player_id):
        self.x = x
        self.y = y
        self.type = type
        self.player_id = player_id
        self.moved = False
        self.attacked = False
        self.movement = 0 # 禁用移动
        self.attack_range = (0, 0) # 禁用攻击
        self.health = self.max_health = 100
        self.armor_type = 1
        self.build_stacked = False

        if type in self.PROPERTIES:
            self.shop_type = self.PROPERTIES[type]['shop_type']
            self.stackable = self.PROPERTIES[type]['stackable']
            

    PROPERTIES = {
        "factory": {
            'shop_type' : SHOP_TYPE.GROUND,
            'stackable' : True,
            
        },
        "airport": {
        },
        "shipyard": {
        },
        "city": {
            'income': 5
        },
    }

    def draw(self, screen, map_x, map_y):
        super().draw(screen, map_x, map_y)