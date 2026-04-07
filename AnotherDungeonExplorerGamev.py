#better camera and boss and ui

import pygame, sys
from pygame.math import Vector2 as vector
from pytmx.util_pygame import load_pygame
from os import walk
from os.path import join
from pygame.time import get_ticks
from random import choice

WINDOW_WIDTH, WINDOW_HEIGHT = 960, 640
scale = 4
tile_size = 16 * scale
ANIMATION_SPEED = 10

LEVEL_LAYERS ={
     'bg1': 0,
     'bg2':1,
     'bg3':2,
     'collisions':3,
     'main':4,
     'platforms':5,
     'fg':6,


}

def import_image(*path, alpha = True, format = 'png'):
	full_path = join(*path) + f'.{format}'
	return pygame.image.load(full_path).convert_alpha() if alpha else pygame.image.load(full_path).convert()

def import_folder(*path):
	frames = []
	for folder_path, subfolders, image_names in walk(join(*path)):
		for image_name in sorted(image_names, key = lambda name: int(name.split('.')[0])):
			full_path = join(folder_path, image_name)
			frames.append(pygame.image.load(full_path).convert_alpha())
	return frames 

def import_folder_dict(*path):
	frame_dict = {}
	for folder_path, _, image_names in walk(join(*path)):
		for image_name in image_names:
			full_path = join(folder_path, image_name)
			surface = pygame.image.load(full_path).convert_alpha()
			frame_dict[image_name.split('.')[0]] = surface
	return frame_dict

def import_sub_folders(*path):
	frame_dict = {}
	for _, sub_folders, __ in walk(join(*path)): 
		if sub_folders:
			for sub_folder in sub_folders:
				frame_dict[sub_folder] = import_folder(*path, sub_folder)
	return frame_dict

class Timer:
	def __init__(self, duration, func = None, repeat = False):
		self.duration = duration
		self.func = func
		self.start_time = 0
		self.active = False
		self.repeat = repeat


	def activate(self):
		self.active = True
		self.start_time = get_ticks()


	def deactivate(self):
		self.active = False
		self.start_time = 0
		if self.repeat:
			self.activate()


	def update(self):
		current_time = get_ticks()
		if current_time - self.start_time >= self.duration:
			if self.func and self.start_time != 0:
				self.func()
			self.deactivate()

class AllSprites(pygame.sprite.Group):
     def __init__(self):
            super().__init__()
            self.display_surface = pygame.display.get_surface()
            self.offset = vector()
            self.zoom = 2.2

     def draw(self, target_position):
        self.offset.x = -(target_position[0] - WINDOW_WIDTH / 2)
        self.offset.y = -(target_position[1] - WINDOW_HEIGHT / 1.75)
        temp_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        temp_surface.fill('black')
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.z):
            offset_pos = sprite.rect.topleft + self.offset
            temp_surface.blit(sprite.image, offset_pos)
        scaled = pygame.transform.scale( temp_surface, (int(WINDOW_WIDTH * self.zoom), int(WINDOW_HEIGHT * self.zoom)))
        rect = scaled.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.display_surface.blit(scaled, rect)

class Level:
    def __init__(self, tmx_map, level_frames):
        self.display_surface = pygame.display.get_surface()

        self.boss_defeated = False
        self.boss_death_timer = None

        self.all_sprites = AllSprites()
        self.collision_sprites = AllSprites()
        self.semi_collision_sprites = AllSprites()
        self.damage_sprites = AllSprites()
        self.ratto_sprites = AllSprites()
        self.item_sprites = AllSprites()
        self.zombie_sprites = AllSprites()
        self.tmx_map = tmx_map          
        self.level_frames = level_frames

        self.setup(tmx_map, level_frames)

    def setup(self, tmx_map, level_frames):
        
        for layer in ['BG0','BG1','BG2', 'Collisions','Platforms', 'FG']:
            for x,y,surf in tmx_map.get_layer_by_name(layer).tiles():
                scaled_surf = pygame.transform.scale(surf, (tile_size, tile_size))
                groups = [self.all_sprites]
                if layer == 'Collisions':
                    groups.append(self.collision_sprites)
                elif layer == 'Platforms':
                    groups.append(self.semi_collision_sprites)
                match layer:
                     case 'BG0': z = LEVEL_LAYERS['bg1']
                     case 'BG1': z = LEVEL_LAYERS['bg2']
                     case 'BG2': z = LEVEL_LAYERS['bg3']
                     case 'FG': z = LEVEL_LAYERS['fg']
                     case _: z = LEVEL_LAYERS['main']

                Sprite((x*tile_size,y*tile_size),scaled_surf, groups, z)
        
        for obj in tmx_map.get_layer_by_name('Objects'):
            if obj.name == 'Player':
                self.spawn_point = (obj.x * scale, obj.y * scale)
                self.player = Player(
                    pos=self.spawn_point,
                    groups=self.all_sprites,
                    collision_sprites=self.collision_sprites, 
                    semi_collision_sprites=self.semi_collision_sprites,
                    frames=level_frames['Player'])
            else:
                if obj.name in ('Banner', 'Painting'):
                    scaled_surf = pygame.transform.scale( obj.image, (int(obj.width * scale), int(obj.height * scale)))
                    Sprite((obj.x * scale, obj.y * scale), scaled_surf, self.all_sprites, z = LEVEL_LAYERS['bg3'])

        for obj in tmx_map.get_layer_by_name('Moving Objects'):
             frames = level_frames[obj.name]
             if obj.name == 'Elevator':
                    if obj.width > obj.height:
                         move_dir = 'x'
                         start_pos = (obj.x, obj.y + obj.height/2)
                         end_pos = (obj.x + obj.width, obj.y + obj.height/2)
                    else: 
                         move_dir = 'y'
                         start_pos = (obj.x + obj.width/2, obj.y)
                         end_pos = (obj.x + obj.width/2, obj.y + obj.height)
                    speed = obj.properties['speed']
                    MovingSprite(frames ,(self.all_sprites,self.semi_collision_sprites),start_pos,end_pos,move_dir,speed, obj.width, obj.height)

        for obj in tmx_map.get_layer_by_name('Enemies'):
             if obj.name == 'Ratto':
                  Ratto((obj.x * scale, obj.y * scale), level_frames['Ratto'], (self.all_sprites, self.damage_sprites, self.ratto_sprites), self.collision_sprites)
        for obj in tmx_map.get_layer_by_name('Enemies'):
            if obj.name == 'Zombie':
                Zombie((obj.x * scale, obj.y * scale), (self.all_sprites, self.damage_sprites, self.zombie_sprites), self.collision_sprites, self.player, level_frames['Zombie'])
            if obj.name == 'Boss':
                Boss((obj.x * scale, obj.y * scale), (self.all_sprites, self.damage_sprites, self.zombie_sprites), self.collision_sprites, self.player, level_frames['Boss'])
        for obj in tmx_map.get_layer_by_name('Items'):
             if obj.name == 'Health Potion' or obj.name == 'Death':
                Item(obj.name, ((obj.x * scale)+tile_size/8, (obj.y * scale) + (tile_size/8))  , level_frames['Items'][obj.name], (self.all_sprites,self.item_sprites))

    def draw_player_health(self):
        bar_width = 250
        bar_height = 40
        bar_x = 20
        bar_y = 580

        health_ratio = self.player.player_health / 100
        current_width = int(bar_width * health_ratio)

        pygame.draw.rect(self.display_surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(self.display_surface, (155, 87, 92), (bar_x, bar_y, current_width, bar_height))
        pygame.draw.rect(self.display_surface, (20, 20, 20), (bar_x, bar_y, bar_width, bar_height), 2)

    def reset(self):
        self.__init__(self.tmx_map, self.level_frames)

    def item_collision(self):
         if self.item_sprites:
              item_sprites = pygame.sprite.spritecollide(self.player, self.item_sprites, True)
              for item in item_sprites:
                   if item.item_type == 'Health Potion':
                        self.player.player_health += 50
                        if self.player.player_health > 100:
                             self.player.player_health = 100
                   if item.item_type == 'Death':
                        self.player.player_health = 0

    def attack_collision(self):
        targets = self.ratto_sprites.sprites() + self.zombie_sprites.sprites()
        for target in targets:
            facing_target = (self.player.rect.centerx < target.rect.centerx and self.player.facing_right or self.player.rect.centerx > target.rect.centerx and not self.player.facing_right
            )
            if target.rect.colliderect(self.player.attack_hitbox) and self.player.attacking and facing_target:
                if target not in self.player.hit_targets:
                    target.take_damage(10)
                    self.player.hit_targets.add(target)

    def damage_collision(self):
        enemies = self.ratto_sprites.sprites()
        for enemy in enemies:
            if enemy.rect.colliderect(self.player.hitbox_rect):
                 if enemy not in self.player.damage_sources and not enemy.state == 'Death':
                     self.player.take_damage(10)
                     self.player.damage_sources.add(enemy)

    def run(self, dt):
        self.attack_collision()
        self.damage_collision()

        if self.player.player_health <= 0:
            self.reset()
            return
        for sprite in self.zombie_sprites:
            if isinstance(sprite, Boss) and not sprite.alive and not self.boss_defeated:
                self.boss_defeated = True
                self.boss_death_timer = pygame.time.get_ticks()  
        if self.boss_defeated:
            if pygame.time.get_ticks() - self.boss_death_timer >= 3000:
                pygame.quit()
                sys.exit()

        self.display_surface.fill('black')
        self.all_sprites.update(dt)
        self.item_collision()
        self.all_sprites.draw(self.player.hitbox_rect.center)
        self.draw_player_health()

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf = pygame.Surface((tile_size, tile_size)), groups = None, z = LEVEL_LAYERS['main']):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft = pos)
        self.old_rect = self.rect.copy()
        self.z = z

class AnimatedSprite(Sprite):
     def __init__(self, pos, frames, groups = None, z = LEVEL_LAYERS['main'], animation_speed = ANIMATION_SPEED):
          self.frames = [pygame.transform.scale(frame, (int(frame.get_width()*scale), int(frame.get_height()*scale))) for frame in frames]
          self.frame_index = 0
          super().__init__(pos, self.frames[self.frame_index], groups, z)
          self.animation_speed = animation_speed

     def animate(self, dt):
              self.frame_index += self.animation_speed * dt
              self.image = self.frames[int(self.frame_index % len(self.frames))]
          
     def update(self, dt):
          self.animate(dt)

class Item(AnimatedSprite):
     def __init__(self, item_type, pos, frames, groups):
          super().__init__(pos, frames, groups)
          self.rect.center = pos
          self.item_type = item_type

class MovingSprite(AnimatedSprite):
     def __init__(self, frames , groups, start_pos, end_pos, move_dir, speed, width, height):
          scaled_pos = (start_pos[0] * scale, start_pos[1] * scale)
          scaled_end_pos = (end_pos[0] * scale, end_pos[1] * scale)
          super().__init__(scaled_pos, frames, groups)
          if move_dir == 'x':
               self.rect.midleft = scaled_pos
          else:
               self.rect.midtop = scaled_pos

          self.start_pos = scaled_pos
          self.end_pos = scaled_end_pos

          #movement
          self.moving = True
          self.speed = speed
          self.direction = vector(1,0) if move_dir == 'x' else vector(0,1)
          self.move_dir = move_dir

     def check_border(self):
          if self.move_dir == 'x':
               if self.rect.right >= self.end_pos[0] and self.direction.x ==1:
                    self.direction.x = -1
                    self.rect.right = self.end_pos[0]
               if self.rect.right <= self.start_pos[0] and self.direction.x ==-1:
                    self.direction.x = 1
                    self.rect.right = self.start_pos[0]
          else:
               if self.rect.bottom >= self.end_pos[1] and self.direction.y ==1:
                    self.direction.y = -1
                    self.rect.bottom = self.end_pos[1]
               if self.rect.bottom <= self.start_pos[1] and self.direction.y ==-1:
                    self.direction.y = 1
                    self.rect.bottom = self.start_pos[1]
               
     def update(self, dt):
          self.old_rect = self.rect.copy()
          self.rect.topleft += self.direction * self.speed * dt
          self.check_border()
          self.animate(dt)
     
class Ratto(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, collision_sprites):
        super().__init__(groups)
        self.frames = { state: [pygame.transform.scale(frame, (int(frame.get_width() * scale), int(frame.get_height() * scale)))for frame in frame_list]
            for state, frame_list in frames.items()}

        self.state = 'Run'          
        self.frame_index = 0
        self.image = self.frames[self.state][self.frame_index]
        self.rect = self.image.get_frect(topleft=pos)
        self.z = LEVEL_LAYERS['main']

        self.direction = choice((-1,1))
        self.speed = 100
        self.collision_rects = [sprite.rect for sprite in collision_sprites]

        self.health = 20
        self.damage_timer = Timer(250)   
        self.alive = True

    def take_damage(self, damage):
        if self.alive and not self.damage_timer.active:
            self.health -= damage
            self.state = 'Hit'             
            self.frame_index = 0
            self.damage_timer.activate()

            if self.health <= 0:
                self.state = 'Death'
                self.frame_index = 0
                self.alive = False

    def update_state(self):
        if self.state == 'Hit' and self.frame_index >= len(self.frames['Hit']):
            if self.alive:
                self.state = 'Run'
                self.frame_index = 0
        if self.state == 'Death' and self.frame_index >= len(self.frames['Death']):
            self.kill()

    def update(self, dt):
        self.damage_timer.update()
        self.frame_index += ANIMATION_SPEED * dt
        current_frames = self.frames[self.state]
        self.image = current_frames[int(self.frame_index % len(current_frames))]
        self.image = pygame.transform.flip(self.image, True, False) if self.direction < 0 else self.image
        self.update_state()
        if self.alive and self.state == 'Run':
            self.rect.x += self.direction * self.speed * dt
            floor_rect_right = pygame.FRect(self.rect.bottomright, (1,1))
            floor_rect_left = pygame.FRect(self.rect.bottomleft, (-1,1))
            wall_rect = pygame.FRect(self.rect.topleft + vector(-1,0), (self.rect.width + 2,1))
            if floor_rect_right.collidelist(self.collision_rects) < 0 and self.direction > 0 or \
               floor_rect_left.collidelist(self.collision_rects) < 0 and self.direction < 0 or \
               wall_rect.collidelist(self.collision_rects) != -1:
                self.direction *= -1

class Zombie(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites, player, frames):
        super().__init__(groups)
        self.frames = {state: [pygame.transform.scale(frame, (int(frame.get_width() * scale), int(frame.get_height() * scale))) for frame in frame_list]
            for state, frame_list in frames.items()}
        
        self.state = 'Idle'
        self.frame_index = 0
        self.image = self.frames[self.state][self.frame_index]
        self.rect = self.image.get_frect(topleft=pos)
        self.z = LEVEL_LAYERS['main']

        self.player = player
        self.collision_rects = [sprite.rect for sprite in collision_sprites]

        self.direction = vector()
        self.speed = 80
        self.gravity = 1000

        self.health = 30
        self.alive = True
        self.attack_cooldown = Timer(3000)
        self.damage_timer = Timer(500)
        self.attack_hitbox = pygame.Rect(20, 0, 40, self.rect.height)
        self.has_hit = False

        self.hitbox = self.rect

        self.detection_radius = 300
        self.attack_radius = 80

    def get_distance(self):
        player_pos = vector(self.player.hitbox_rect.center)
        zombie_pos = vector(self.hitbox.center)
        distance = (player_pos - zombie_pos).length()
        if distance != 0:
            direction = (player_pos - zombie_pos).normalize()
        else:
            direction = vector()
        return distance, direction

    def update_attack_hitbox(self):
        if self.player.hitbox_rect.centerx < self.hitbox.centerx:
            self.attack_hitbox.topright = self.hitbox.topleft
        else:
            self.attack_hitbox.topleft = self.hitbox.topright

    def take_damage(self, damage):
        if self.alive and not self.damage_timer.active:
            self.health -= damage
            self.state = 'Hit'
            self.frame_index = 0
            self.damage_timer.activate()
            if self.health <= 0:
                self.state = 'Death'
                self.frame_index = 0
                self.alive = False

    def deal_damage(self):
        if self.state != 'Attack':
            return
        if self.has_hit:
            return
        current_frame = int(self.frame_index)
        if 2 <= current_frame <= 4:
            if self.attack_hitbox.colliderect(self.player.hitbox_rect):
                self.player.take_damage(10)
                self.has_hit = True
                
    def update_state(self):
        if not self.alive:
            return
        distance, direction = self.get_distance()
        if self.state == 'Attack':
            return
        if distance <= self.attack_radius and not self.attack_cooldown.active:
            self.state = 'Attack'
            self.frame_index = 0
            self.attack_cooldown.activate()
            self.direction.x = 0  
            self.has_hit = False
        elif distance <= self.detection_radius:
            self.state = 'Run'
            self.direction.x = direction.x if abs(self.player.hitbox_rect.centerx - self.hitbox.centerx) > 80 else 0
            if self.direction.x == 0:
                 self.state = 'Idle'
        else:
            self.state = 'Idle'
            self.direction.x = 0

    def move(self, dt):
        self.hitbox.x += self.direction.x * self.speed * dt
        for rect in self.collision_rects:
            if rect.colliderect(self.hitbox):
                if self.direction.x > 0:
                    self.hitbox.right = rect.left
                elif self.direction.x < 0:
                    self.hitbox.left = rect.right
                    
        self.direction.y += self.gravity * dt
        self.hitbox.y += self.direction.y * dt
        for rect in self.collision_rects:   
            if rect.colliderect(self.hitbox):
                if self.direction.y > 0: 
                    self.hitbox.bottom = rect.top
                    self.direction.y = 0
                elif self.direction.y < 0: 
                    self.hitbox.top = rect.bottom
                    self.direction.y = 0

        self.rect.center = self.hitbox.center

    def animate(self, dt):
        self.frame_index += ANIMATION_SPEED * dt
        current_frames = self.frames[self.state]
        if self.frame_index >= len(current_frames):
            if self.state == 'Hit':
                self.state = 'Idle'
            elif self.state == 'Attack':
                self.state = 'Idle'
                self.frame_index = 0
            elif self.state == 'Death':
                self.kill()
                return
        self.image = current_frames[int(self.frame_index % len(current_frames))]
        if self.player.hitbox_rect.centerx < self.hitbox.centerx:
            self.image = pygame.transform.flip(self.image, True, False)

    def update(self, dt):
        self.update_attack_hitbox()
        self.deal_damage()
        self.damage_timer.update()
        self.attack_cooldown.update()
        if self.alive:
            if self.state not in ['Hit', 'Death']:
                self.update_state()
                self.move(dt)
        self.animate(dt)

class Boss(Zombie):
    def __init__(self, pos, groups, collision_sprites, player, frames):
        super().__init__(pos, groups, collision_sprites, player, frames)
        self.health = 200
        self.attack_states = ['Attack', 'Attack2']
        self.attack_radius = 150  
        self.detection_radius = 400  
        self.attack_hitbox = pygame.Rect(0, 0, self.rect.width + 100, self.rect.height + 50)

    def update_attack_hitbox(self):
        padding_x = 50 
        padding_y = 25 
        self.attack_hitbox.width = self.rect.width + padding_x * 2
        self.attack_hitbox.height = self.rect.height + padding_y * 2
        self.attack_hitbox.center = self.rect.center

    def update_state(self):
        if not self.alive:
            return
        distance, direction = self.get_distance()

        if self.state in self.attack_states:
            return
        if distance <= self.attack_radius and not self.attack_cooldown.active:
            self.state = choice(self.attack_states)
            self.frame_index = 0
            self.attack_cooldown.activate()
            self.direction.x = 0
            self.has_hit = False
        elif distance <= self.detection_radius:
            self.state = 'Run'
            self.direction.x = direction.x if abs(self.player.hitbox_rect.centerx - self.hitbox.centerx) > 80 else 0
            if self.direction.x == 0:
                self.state = 'Idle'
        else:
            self.state = 'Idle'
            self.direction.x = 0

    def move(self, dt):
        self.hitbox.x += self.direction.x * self.speed * dt
        for rect in self.collision_rects:
            if rect.colliderect(self.hitbox):
                if self.direction.x > 0:
                    self.hitbox.right = rect.left
                elif self.direction.x < 0:
                    self.hitbox.left = rect.right
        self.rect.center = self.hitbox.center

    def animate(self, dt):
        self.frame_index += ANIMATION_SPEED * dt
        current_frames = self.frames[self.state]
        if self.frame_index >= len(current_frames):
            if self.state in ['Hit']:
                self.state = 'Idle'
            elif self.state in self.attack_states:
                self.state = 'Idle'
                self.frame_index = 0
            elif self.state == 'Death':
                self.kill()
                return
        self.image = current_frames[int(self.frame_index % len(current_frames))]
        if self.player.hitbox_rect.centerx < self.hitbox.centerx:
            self.image = pygame.transform.flip(self.image, True, False)

    def deal_damage(self):
        if self.state not in self.attack_states:
            return
        if self.has_hit:
            return

        current_frame = int(self.frame_index)
        if 2 <= current_frame <= 4: 
            if self.attack_hitbox.colliderect(self.player.hitbox_rect):
                self.player.take_damage(20)  
                self.has_hit = True

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites, semi_collision_sprites, frames):
        super().__init__(groups)
        self.frames = {state: [pygame.transform.scale( frame, (int(frame.get_width() * scale), int(frame.get_height() * scale))) for frame in frame_list]
            for state, frame_list in frames.items()}

        self.frame_index = 0
        self.state = 'idle'
        self.facing_right = True

        self.image = self.frames[self.state][self.frame_index]
    
        self.z = LEVEL_LAYERS['main']

        self.rect = self.image.get_frect(topleft = pos)

        self.rect = self.image.get_frect(topleft = pos)
        self.hitbox_rect = self.rect.inflate(-40,0)
        self.old_rect = self.hitbox_rect.copy()

        self.direction = vector() 
        self.speed = 200
        self.gravity = 1300
        self.jump = False
        self.jump_height = 600

        self.attacking = False
        self.attack_hitbox = pygame.Rect(0,0, self.hitbox_rect.width + 40, self.hitbox_rect.height) 
        self.hit_targets = set()
        self.damage_sources = set()
        
        self.collision_sprites = collision_sprites
        self.semi_collision_sprites = semi_collision_sprites
        self.on_surface = {'floor': False, 'left': False, 'right': False}
        self.platform = None

        self.player_health = 100

        self.timers = {
             'wall jump': Timer(500),
             'wall slide block': Timer(250),
             'platform skip': Timer(100),
             'attack block': Timer(500),
             'hit cooldown': Timer(1000)
        }

    def input(self):
        keys = pygame.key.get_pressed()
        input_vector = vector(0,0)
        if not self.timers['wall jump'].active:
            if keys[pygame.K_RIGHT]:
                input_vector.x = 1  
                self.facing_right = True
            if keys[pygame.K_LEFT]:
                input_vector.x = -1
                self.facing_right = False
            if keys[pygame.K_DOWN]:
                 self.timers['platform skip'].activate()
            if keys[pygame.K_x]:
                 self.attack()
            self.direction.x = input_vector.normalize().x if input_vector else 0
        if keys[pygame.K_SPACE]:
            self.jump = True
    
    def attack(self):
         if not self.timers['attack block'].active:
            self.attacking = True
            self.frame_index = 0
            self.hit_targets.clear()
            self.timers['attack block'].activate()

    def take_damage(self, damage):
            if not self.timers['hit cooldown'].active:
                self.player_health -= damage
                self.state = 'hit'
                self.frame_index = 0
                self.timers['hit cooldown'].activate()
                if self.player_health <= 0:
                     pass

    def move(self, dt):
        self.hitbox_rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')

        if not self.on_surface['floor'] and any((self.on_surface['left'], self.on_surface['right'])) and not self.timers['wall slide block'].active:
            self.direction.y = 0
            self.hitbox_rect.y += self.gravity / 10 * dt
        else:
            self.direction.y += self.gravity / 2 * dt
            self.hitbox_rect.y += self.direction.y * dt
            self.direction.y += self.gravity / 2 * dt
            
        if self.jump:
            if self.on_surface['floor']:
                self.direction.y = -self.jump_height
                self.timers['wall slide block'].activate()
                self.hitbox_rect.bottom -= 1
            elif any((self.on_surface['left'], self.on_surface['right'])) and not self.timers['wall slide block'].active:
                self.timers['wall jump'].activate()
                self.direction.y = -self.jump_height
                self.direction.x = 1 if self.on_surface['left'] else -1
            self.jump = False

        self.collision('vertical')
        self.semi_collision()
        self.rect.center = self.hitbox_rect.center

    def update_attack_hitbox(self):
        if self.facing_right:
            self.attack_hitbox.topleft = self.hitbox_rect.topright + vector(0, 0)
        else:
            self.attack_hitbox.topright = self.hitbox_rect.topleft + vector(0, 0)
        
    def platform_move(self, dt):
         if self.platform:
              self.hitbox_rect.topleft += self.platform.direction * self.platform.speed * dt

    def collision(self, axis):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if axis == 'horizontal':
                    if self.hitbox_rect.left <= sprite.rect.right and int(self.old_rect.left) >= int(sprite.old_rect.right):
                        self.hitbox_rect.left = sprite.rect.right
                    if self.hitbox_rect.right >= sprite.rect.left and int(self.old_rect.right) <= int(sprite.old_rect.left):
                        self.hitbox_rect.right = sprite.rect.left
                else:
                    if self.hitbox_rect.top <= sprite.rect.bottom and int(self.old_rect.top) >= int(sprite.old_rect.bottom):
                        self.hitbox_rect.top = sprite.rect.bottom
                        if hasattr(sprite, 'moving'):
                             self.hitbox_rect.top += 6
                    if self.hitbox_rect.bottom >= sprite.rect.top and int(self.old_rect.bottom) <= int(sprite.old_rect.top):
                        self.hitbox_rect.bottom = sprite.rect.top
                    self.direction.y = 0

    def semi_collision(self):
         if not self.timers['platform skip'].active:
            for sprite in self.semi_collision_sprites:
                if sprite.rect.colliderect(self.hitbox_rect):
                    if self.hitbox_rect.bottom >= sprite.rect.top and int(self.old_rect.bottom) <= int(sprite.old_rect.top):
                            self.hitbox_rect.bottom = sprite.rect.top
                            if self.direction.y >= 0:  
                                self.direction.y = 0
    
    def check_contact(self):

        floor_rect = pygame.Rect(self.hitbox_rect.bottomleft,(self.hitbox_rect.width,2))
        right_rect = pygame.Rect(self.hitbox_rect.topright + vector(0,self.hitbox_rect.height/4),(2,self.hitbox_rect.height/2))
        left_rect = pygame.Rect(self.hitbox_rect.topleft +vector(-2,self.hitbox_rect.height/4),(2,self.hitbox_rect.height/2))

        collide_rects = [sprite.rect for sprite in self.collision_sprites]
        semi_collide_rects = [sprite.rect for sprite in self.semi_collision_sprites]

        self.on_surface['floor'] = True if floor_rect.collidelist(collide_rects) >= 0 or floor_rect.collidelist(semi_collide_rects) >= 0 and self.direction.y >= 0 else False
        self.on_surface['right'] = True if right_rect.collidelist(collide_rects) >= 0 else False
        self.on_surface['left'] = True if left_rect.collidelist(collide_rects) >= 0 else False

        self.platform = None
        sprites = self.semi_collision_sprites.sprites() + self.collision_sprites.sprites()
        for sprite in [sprite for sprite in sprites if hasattr(sprite, 'moving')]:
             if sprite.rect.colliderect(floor_rect):
                  self.platform = sprite
                   
    def update_timers(self):
        for timer in self.timers.values():
              timer.update()

    def animate(self, dt):
         self.frame_index += ANIMATION_SPEED * dt

         if self.state in ('attack', 'hit') and self.frame_index >= len(self.frames[self.state]):
              self.state = 'idle'
         self.image = self.frames[self.state][int(self.frame_index % len(self.frames[self.state]))]
         self.image = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)

         if self.attacking and self.frame_index > len(self.frames[self.state]):
              self.attacking = False

    def get_state(self):
         if self.on_surface['floor']:
              if self.state == 'hit':
                   return
              if self.attacking:
                   self.state = 'attack'
              else:
                   self.state = 'idle' if self.direction.x == 0 else 'run'
              
         else:
              if self.attacking:
                   self.state = 'air_attack'
              else:
                if self.state == 'hit':
                   return
                if any((self.on_surface['left'], self.on_surface['right'])):
                    self.state = 'wall'
                else:
                    self.state = 'jump' if self.direction.y < 0 else 'fall'
         
    def update(self, dt):
        self.damage_sources.clear()
        self.old_rect = self.hitbox_rect.copy()
        self.update_timers()

        self.input()
        self.platform_move(dt)
        self.move(dt)
        self.check_contact()

        self.update_attack_hitbox()
        self.get_state()
        self.animate(dt)

class Game:
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Another Dungeon Explorer Game')
        self.clock = pygame.time.Clock()
        self.tmx_maps = {0: load_pygame(join('Levels', 'Dungeon.tmx'))}
        self.import_assets()
        self.current_level = Level(self.tmx_maps[0], self.level_frames)

    def import_assets(self):
         self.level_frames = {
              'Player'  :import_sub_folders('Assets','Player'),
              'Elevator' : import_folder('Assets','Props','Elevator'),
              'Zombie' : import_sub_folders('Assets','Enemies','Zombie'),
              'Ratto' : import_sub_folders('Assets','Enemies','Ratto'),
              'Items' : import_sub_folders('Assets','Usable Items'),
              'Boss' : import_sub_folders('Assets', 'Boss')
         }
        
    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.current_level.run(dt)
            pygame.display.update()

Game().run()