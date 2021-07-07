import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as et
from io import BytesIO
from timeit import default_timer
from zipfile import ZipFile

LOCALE_CODE = 'en_us'
DEBUG = False

def generate_mod(maven_group, modid, mod_name, description, mod_version, minecraft_version, directory, authors, website):
    minecraft_versions = json.loads(urllib.request.urlopen('https://meta.fabricmc.net/v2/versions/game').read())
    minecraft_version_list = [i['version'] for i in minecraft_versions]
    if os.path.exists(os.path.join(__file__, 'fabric_versions.json')):
        fabric_versions_file = open(os.path.join(__file__, 'fabric_versions.json'), 'r')
        fabric_minecraft_versions = json.load(fabric_versions_file)
        fabric_versions_file.close()
    else:
        fabric_minecraft_versions = {}

    if not minecraft_versions[1]['version'] in fabric_minecraft_versions:
        print('Collecting fabric versions...')
        modrinth_versions = json.loads(urllib.request.urlopen('https://api.modrinth.com/api/v1/mod/P7dR8mSH').read())['versions']

        fabric_minecraft_versions = {}
        def get_version(modrinth_version, fabric_minecraft_versions):
            version_url = 'https://api.modrinth.com/api/v1/version/' + modrinth_version
            game_versions = json.loads(urllib.request.urlopen(version_url).read())['game_versions']
            fabric_version = json.loads(urllib.request.urlopen(version_url).read())['version_number']
            for game_version in game_versions:
                fabric_minecraft_versions[game_version] = fabric_version

        threads = []
        for modrinth_version in modrinth_versions:
            threads.append(threading.Thread(target=get_version, args=(modrinth_version, fabric_minecraft_versions)))

        for thread in threads:
            thread.start()
            time.sleep(0.4)

        for thread in threads:
            thread.join()
        fabric_versions_file = open('fabric_versions.json', 'w')
        json.dump(fabric_minecraft_versions, fabric_versions_file, indent=4)
        fabric_versions_file.close()

    os.chdir(directory)

    print('Cloning example mod...')

    if minecraft_version in minecraft_version_list[:minecraft_version_list.index('1.16.5')]:
        template_link = 'https://github.com/FabricMC/fabric-example-mod/archive/1.17.zip'
        template_name = 'fabric-example-mod-1.17'
    else:
        template_link = 'https://github.com/FabricMC/fabric-example-mod/archive/master.zip'
        template_name = 'fabric-example-mod-master'

    template_zip = urllib.request.urlopen(template_link).read()
    ZipFile(BytesIO(template_zip), 'r').extractall()
    os.rename(template_name, mod_name)

    os.remove(os.path.join(mod_name, 'LICENSE'))
    os.remove(os.path.join(mod_name, 'README.md'))
    shutil.rmtree(os.path.join(mod_name, '.github'))

    print('Configuring mod...')

    properties = json.loads(urllib.request.urlopen(f'https://meta.fabricmc.net/v1/versions/loader/{minecraft_version}').read())

    archives_base_name = re.sub('[^a-zA-Z0-9_]', '', mod_name).replace(' ', '-').lower()
    gradle_properties = f'''# Done to increase the memory available to gradle.
    org.gradle.jvmargs = -Xmx1G

    # Fabric Properties
    minecraft_version = {minecraft_version}
    yarn_mappings = {properties[0]['mappings']['version']}
    loader_version = {properties[0]['loader']['version']}

    # Mod Properties
    mod_version = {mod_version}
    maven_group = {maven_group}
    archives_base_name = {archives_base_name}

    # Dependencies
    fabric_version = {fabric_minecraft_versions[minecraft_version]}'''

    os.chdir(os.path.join(directory, mod_name))

    properties_file = open('gradle.properties', 'w')
    properties_file.write(gradle_properties)
    properties_file.close()

    json_data_file = open(os.path.join('src', 'main', 'resources', 'fabric.mod.json'), 'r')
    json_data = json_data_file.read()
    json_data_file.close()
    
    json_file = open(os.path.join('src', 'main', 'resources', 'fabric.mod.json'), 'w')
    json_config = json.loads(json_data)

    json_config['id'] = modid
    json_config['name'] = mod_name
    json_config['description'] = description
    json_config['authors'] = authors 
    json_config['contact']['homepage'] = website
    json_config['contact']['sources'] = ''
    json_config['license'] = '' #TODO: Add support for licences.
    json_config['icon'] = 'assets/' + modid + '/icon.png'
    #TODO: Add support for mixins.
    #json_config['mixins'] = [modid + '.mixins.json']
    json_config['mixins'] = []
    json_config['entrypoints']['main'] = [maven_group + '.' + mod_name.title().replace(' ', '')]

    json.dump(json_config, json_file, indent=4)
    json_file.close()

    shutil.rmtree(os.path.join('src', 'main', 'java', 'net'))
    shutil.rmtree(os.path.join('src', 'main', 'resources', 'assets', 'modid'))

    main_entrypoint = os.path.join('src', 'main', 'java', *maven_group.split('.'))
    os.makedirs(main_entrypoint)
    assets = os.path.join('src', 'main', 'resources', 'assets', modid)
    os.makedirs(assets)

    #TODO: Add default mod icon with link below.
    'https://github.com/FabricMC/fabric-example-mod/raw/master/src/main/resources/assets/modid/icon.png'

    data_file = open('data.txt', 'w')
    data_file.write(f'''# This file was auto-generated by pyFabricMC.
# Feel free to delete this file when uploading this mod's source code.

main entrypoint: {os.path.join('src', 'main', 'java', *maven_group.split('.'), mod_name.title().replace(' ', '') + '.java')}
assets: {assets}''')
    data_file.close()

    print('Successfully generated mod!')

def edit_mod(directory, java, lang, models, textures):
    os.chdir(directory)

    data_file = open('data.txt', 'r')
    main_entrypoint, assets_dir = [i.split(': ')[1].replace('\n','') for i in data_file.readlines()[3:]]
    data_file.close()

    java_file = open(main_entrypoint, 'w')
    java_file.write(java)
    java_file.close()

    if not os.path.isdir(os.path.join(assets_dir, 'lang')):
        os.mkdir(os.path.join(assets_dir, 'lang'))

    lang_file = open(os.path.join(assets_dir, 'lang', LOCALE_CODE + '.json'), 'w')
    json.dump(lang, lang_file, indent=4, sort_keys=True)
    lang_file.close()

    os.makedirs(os.path.join(assets_dir, 'models', 'item'), exist_ok=True)
    os.makedirs(os.path.join(assets_dir, 'textures', 'item'), exist_ok=True)

    #TODO: Add support for block textures when the block is function added.
    for name, model in models[0].items():
        model_file = open(os.path.join(assets_dir, 'models', 'item', name + '.json'), 'w')
        json.dump(model, model_file, indent=4, sort_keys=True)
        model_file.close()
        
    for texture in textures[0]:
        shutil.copy(texture, os.path.join(assets_dir, 'textures', 'item', name + '.png'))
        
def run_cmd(command, directory=None):
    process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, cwd=directory)
    error_list = []
    while True:
        error = process.stderr.readline()

        if DEBUG:
            print(error.decode(), end='')

        if error:
            error_list.append(error.decode())
        else:
            break

    if error_list:
        for error in error_list:
            if error.startswith('Caused by'):
                print('Error: ' + error[11:])
            elif error == error_list[-1]:
                print('Error: ' + [re.sub('^[> ]+|\n', '', i) for i in error_list if '>' in i][-1])
        sys.exit()
        
class Mod:
    '''A class to represent a mod.

    Args:
        mod_name (str): Name of the mod.
        mod_version (str): Version number of the mod.
        description (str): Description of the mod.
        minecraft_version (str): Minecraft version of the mod.
        authors (list): List of the mod's authors.
        website (str, optional): Website of the mod, defaults to None.
        directory (str, optional): Path for the mod folder, defaults to ~/Desktop.
    '''
    def __init__(self, mod_name, mod_version, description, minecraft_version, authors, website='', directory=os.path.expanduser('~/Desktop')):
        self.mod_name = mod_name
        self.description = description
        self.minecraft_version = minecraft_version
        self.mod_version = mod_version
        self.directory = directory
        self.authors = authors
        self.website = website

        self.mod_folder = os.path.join(directory, mod_name)

        self.modid = re.sub('[^a-zA-Z0-9_]', '', self.mod_name).lower()
        self.entrypoint = self.mod_name.title().replace(' ', '')

        self.imports = {'net.fabricmc.api.ModInitializer', 'net.minecraft.util.Identifier', 'net.minecraft.util.registry.Registry'}
        self.definitions = []
        self.registry = []

        self.item_textures = []
        self.item_models = {}
        self.block_textures = []
        self.block_models = {}

        self.lang = {}

        if website:
            parsed_url = urllib.parse.urlparse(website)
            self.maven_group = ('.'.join(parsed_url.netloc.split('.')[::-1]) + parsed_url.path.replace('/', '.')).replace('-', '_').lower()
        else:
            self.maven_group = (re.sub('[^a-zA-Z0-9_]', '', authors[0]) + '.' + re.sub('[^a-zA-Z0-9_ ]', '', mod_name).replace(' ', '.')).lower()
            
    def save(self):
        '''Saves the mod data into the mod folder.'''
        
        timer_start = default_timer()
        
        newline = '\n'
        tab = '\t'
        
        java = f'''package {self.maven_group};

{newline.join(['import ' + i + ';' for i in sorted(self.imports)])}

public class {self.entrypoint} implements ModInitializer {{
    {(newline + tab * 2).join(self.definitions)}
    
    @Override
    public void onInitialize() {{
        {(newline + tab * 2).join(self.registry)}

    }}

}}'''
        if os.path.isdir(self.mod_folder):
            print('Found existing mod.')
        else:
            generate_mod(self.maven_group, self.modid, self.mod_name,
                         self.description, self.mod_version, self.minecraft_version,
                         self.directory, self.authors, self.website)

        edit_mod(self.mod_folder, java, self.lang, [self.item_models, self.block_models], [self.item_textures, self.block_textures])

        print('Mod saved.')
        
        timer_end = default_timer()
        elapsed_time = timer_end - timer_start
        time_string = f'{int(divmod(elapsed_time, 60)[0])}m {int(divmod(elapsed_time, 60)[1])}s {int(round(divmod(elapsed_time, 60)[1], 3) % 1 * 1000)}ms'
        print('Finished in ' + time_string)
        
    def run(self):
        '''Runs the Minecraft client.'''
        self.save()

        print('Launching Minecraft client...')

        if os.name == 'posix':
            run_cmd('chmod +x gradlew', self.mod_folder)
            run_cmd('./gradlew wrapper', self.mod_folder)
            command = './gradlew runClient'
        else:
            command = 'gradlew runClient'

        run_cmd(command, self.mod_folder)

    def Item(self, name, itemgroup='misc', image=None):
        '''Creates an item.

        Args:
            name (str): Name of the item.
            itemgroup (str, optional): The item's category, used for creative tabs - one
            of the following: brewing, building blocks, combat, decorations,
            food, materials, misc, redstone, tools or transportation. Defaults
            to misc.
            image (str, optional): Path to the item's image. If no path is
            specified, it will look in the working directory for an image.
        '''

        texture = glob.glob('**/' + name.lower().replace(' ', '_') + '.png', recursive=True)
        
        if image:
            texture_file = image
        elif texture:
            texture_file = os.path.join(os.getcwd(), texture[0])
        else:
            print('Error: Could not find a texture for \'' + name + '\'')
            sys.exit()

        self.item_models[name.lower().replace(' ', '_')] = {'parent': 'minecraft:item/generated', 'textures': {'layer0': f'{self.modid}:item/{name.lower().replace(" ", "_")}'}}

        self.item_textures.append(texture_file)
        
        self.definitions.append(f'public static final Item {name.upper().replace(" ", "_")} = new Item(new Item.Settings().group(ItemGroup.{itemgroup.upper().replace(" ", "_")}));')
        self.imports.add('net.minecraft.item.Item')
        self.imports.add('net.minecraft.item.ItemGroup')
        self.registry.append(f'Registry.register(Registry.ITEM, new Identifier("{self.modid}", "{name.lower().replace(" ", "_")}"), {name.upper().replace(" ", "_")});')
        
        self.lang[f'item.{self.modid}.{name.lower().replace(" ", "_")}'] = name

    def FoodItem(self, name, hunger, saturation, itemgroup='food', image=None):
        '''Creates an item.

        Args:
            name (str): Name of the item.
            hunger (int): Amount of hunger points your item fills. Each hunger
            point is half a hunger shank. 
            saturation (float): Saturation modifier for the item. The saturation
            modifier is equvalent to saturation restored / hunger points * 0.5.
            itemgroup (str, optional): The item's category, used for creative
            tabs - one of the following: brewing, building blocks, combat,
            decorations, food, materials, misc, redstone, tools or
            transportation. Defaults to misc.
            image (str, optional): Path to the item's image. If no path is
            specified, it will look in the working directory for an image.
        '''
        texture = glob.glob('**/' + name.lower().replace(' ', '_') + '.png', recursive=True)
        
        if image:
            texture_file = image
        elif texture:
            texture_file = os.path.join(os.getcwd(), texture[0])
        else:
            print('Error: Could not find a texture for \'' + name + '\'')
            sys.exit()

        self.item_models[name.lower().replace(' ', '_')] = {'parent': 'minecraft:item/generated', 'textures': {'layer0': f'{self.modid}:item/{name.lower().replace(" ", "_")}'}}

        self.item_textures.append(texture_file)
        
        self.definitions.append(f'public static final Item {name.upper().replace(" ", "_")} = new Item.Settings().group(ItemGroup.{itemgroup.upper().replace(" ", "_")}).food(new FoodComponent.Builder().hunger({hunger}).saturationModifier({saturation}f).build())')
        self.imports.add('net.minecraft.item.Item')
        self.imports.add('net.minecraft.item.ItemGroup')
        self.imports.add('net.minecraft.item.FoodComponent')

        self.registry.append(f'Registry.register(Registry.ITEM, new Identifier("{self.modid}", "{name.lower().replace(" ", "_")}"), {name.upper().replace(" ", "_")});')
        
        self.lang[f'item.{self.modid}.{name.lower().replace(" ", "_")}'] = name
