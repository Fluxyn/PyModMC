import glob
import io
import json
import locale
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import timeit
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as et
import zipfile

locale_file = open(os.path.join(os.path.dirname(__file__), 'locale_codes.txt'))
locale_codes = locale_file.read().split('\n')[1:]
locale_file.close()

LOCALE_CODE = locale.getdefaultlocale()[0].lower()

if platform.system() == 'Darwin':
    # workaround for a bug on OSX where it returns None for the locale
    # described/discussed at stackoverflow.com/q/1629699
    if LOCALE_CODE == 'none':
        LOCALE_CODE = 'en_us'

if LOCALE_CODE not in locale_codes:
    # attempt to find the closest language to the locale
    for lc in locale_codes:
        if lc.startswith(LOCALE_CODE[:2]):
            LOCALE_CODE = lc
    if LOCALE_CODE not in locale_codes:
        LOCALE_CODE = 'en_us'

logger = logging.getLogger()
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

def change_locale(code):
    global LOCALE_CODE
    if code in locale_codes:
        LOCALE_CODE = code
    else:
        logger.error('Locale code is not valid.')
        sys.exit(1)

def run_cmd(command, directory=None):
    '''Used as an internal function to run and log shell commands.'''
    logger.debug(command)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=directory)
    while True:
        out, error = process.communicate()
        logger.debug(out.decode())

        if b'error:' in error:
            for i in re.findall('error: (.*\r\n.*\r\n.*)\r\n', error.decode()):
                error_str = i.split('\r\n')[0] + '\n'
                error_str += i.split('\r\n')[1][4:] + '\n'
                error_str += i.split('\r\n')[2][4:]
                logger.error(error_str)
            logger.debug(error.decode())
            sys.exit(1)
        else:
            break

def generate_mod(maven_group, modid, mod_name, description, mod_version, minecraft_version, directory, authors, website):
    minecraft_versions = json.loads(urllib.request.urlopen('https://meta.fabricmc.net/v2/versions/game').read())
    minecraft_version_list = [i['version'] for i in minecraft_versions]
    stable_minecraft_versions = [i['version'] for i in minecraft_versions if i['stable']]
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'fabric_versions.json')):
        fabric_versions_file = open(os.path.join(os.path.dirname(__file__), 'fabric_versions.json'), 'r')
        fabric_minecraft_versions = json.load(fabric_versions_file)
        fabric_versions_file.close()
    else:
        fabric_minecraft_versions = {}

    # Accounts for unstable Minecraft versions not being recorded in Fabric's Modrinth page
    if not stable_minecraft_versions[1] in fabric_minecraft_versions:
        logger.info('Collecting fabric versions...')
        fabric_data = urllib.request.urlopen('https://api.modrinth.com/v2/project/P7dR8mSH').read()
        modrinth_versions = json.loads(fabric_data)['versions']

        fabric_minecraft_versions = {}
        def get_version(modrinth_version, fabric_minecraft_versions):
            version_url = 'https://api.modrinth.com/v2/project/P7dR8mSH/version/' + modrinth_version
            try:
                game_versions = json.loads(urllib.request.urlopen(version_url).read())['game_versions']
                fabric_version = json.loads(urllib.request.urlopen(version_url).read())['version_number']
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    logger.debug('Rate-limited by Modrinth API. Trying again.')
                    time.sleep(0.4)
                    get_version(modrinth_version, fabric_minecraft_versions)
            for game_version in game_versions:
                fabric_minecraft_versions[game_version] = fabric_version

        threads = []
        for modrinth_version in modrinth_versions:
            threads.append(threading.Thread(target=get_version, args=(modrinth_version, fabric_minecraft_versions)))

        for thread in threads:
            thread.start()
            time.sleep(0.4) # prevents getting rate-limited by the Modrinth API

        for thread in threads:
            thread.join()
        fabric_versions_file = open(os.path.join(os.path.dirname(__file__), 'fabric_versions.json'), 'w')
        json.dump(fabric_minecraft_versions, fabric_versions_file, indent=4)
        fabric_versions_file.close()

    os.chdir(directory)

    logger.info('Cloning example mod...')

    template_branch = json.loads(urllib.request.urlopen('https://api.github.com/repos/FabricMC/fabric-example-mod').read())['default_branch']
    template_zip = urllib.request.urlopen('https://github.com/FabricMC/fabric-example-mod/archive/' + template_branch + '.zip').read()
    zipfile.ZipFile(io.BytesIO(template_zip), 'r').extractall()
    os.rename('fabric-example-mod-' + template_branch, mod_name)

    os.remove(os.path.join(mod_name, 'LICENSE'))
    os.remove(os.path.join(mod_name, 'README.md'))
    shutil.rmtree(os.path.join(mod_name, '.github'))

    logger.info('Configuring mod...')

    properties = json.loads(urllib.request.urlopen('https://meta.fabricmc.net/v1/versions/loader/' + minecraft_version).read())

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
    # TODO: Add support for licences
    #json_config['license'] = '...'
    json_config['icon'] = 'assets/' + modid + '/icon.png'
    # TODO: Add support for mixins
    #json_config['mixins'] = [modid + '.mixins.json']
    json_config['mixins'] = []
    json_config['entrypoints']['main'] = [maven_group + '.' + mod_name.title().replace(' ', '')]

    json.dump(json_config, json_file, indent=4)
    json_file.close()

    shutil.rmtree(os.path.join('src', 'main', 'java'))
    shutil.rmtree(os.path.join('src', 'main', 'resources', 'assets', 'modid'))

    main_entrypoint = os.path.join('src', 'main', 'java', *maven_group.split('.'))
    os.makedirs(main_entrypoint)
    assets = os.path.join('src', 'main', 'resources', 'assets', modid)
    os.makedirs(assets)

    # TODO: Add default mod icon with link below
    'https://github.com/FabricMC/fabric-example-mod/raw/master/src/main/resources/assets/modid/icon.png'

    data_file = open('data.txt', 'w')
    data_file.write(f'''# This file was auto-generated by PyModMC.
# Feel free to delete this file when uploading this mod's source code.

main entrypoint: {os.path.join('src', 'main', 'java', *maven_group.split('.'), mod_name.title().replace(' ', '') + '.java')}
assets: {assets}''')
    data_file.close()

    gradlew = os.stat('gradlew')
    os.chmod('gradlew', gradlew.st_mode | stat.S_IEXEC)

    command = 'gradlew wrapper'
    if os.name == 'posix':
        command = './' + command
    run_cmd(command, os.path.join(directory, mod_name))

    logger.info('Successfully generated mod!')

def edit_mod(directory, java, lang, models, textures):
    os.chdir(directory)

    data_file = open('data.txt', 'r')
    main_entrypoint, assets_dir = [i.split(': ')[1].replace('\n', '') for i in data_file.readlines()[3:]]
    data_file.close()

    java_file = open(main_entrypoint, 'w')
    java_file.write(java)
    java_file.close()

    if not os.path.isdir(os.path.join(assets_dir, 'lang')):
        os.mkdir(os.path.join(assets_dir, 'lang'))

    # TODO: Add support for item translations
    lang_file = open(os.path.join(assets_dir, 'lang', LOCALE_CODE + '.json'), 'w')
    json.dump(lang, lang_file, indent=4, sort_keys=True)
    lang_file.close()

    os.makedirs(os.path.join(assets_dir, 'models', 'item'), exist_ok=True)
    os.makedirs(os.path.join(assets_dir, 'textures', 'item'), exist_ok=True)

    # TODO: Add support for block textures when the block is function added
    for name, model in models[0].items():
        model_file = open(os.path.join(assets_dir, 'models', 'item', name + '.json'), 'w')
        json.dump(model, model_file, indent=4, sort_keys=True)
        model_file.close()
        
    for texture in textures[0]:
        shutil.copy(texture, os.path.join(assets_dir, 'textures', 'item', name + '.png'))
        
class Mod:
    '''A class to represent a mod.'''
    def __init__(self, mod_name, mod_version, description, minecraft_version, authors, website='', directory=os.getcwd()):
        '''
        Creates a mod.

        Parameters:
        mod_name (str): Name of the mod.
        mod_version (str): Version number of the mod.
        description (str): Description of the mod.
        minecraft_version (str): Minecraft version of the mod.
        authors (list): List of the mod's authors.
        website (str, optional): Website for mod, defaults to None.
        directory (str, optional): Path for the mod folder, defaults to the current working directory.
        '''
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

        self.imports = {'net.fabricmc.api.ModInitializer', 'net.minecraft.util.Identifier', 'net.minecraft.registry.Registry', 'net.minecraft.registry.Registries'}
        self.definitions = []
        self.registry = []

        self.item_textures = []
        self.item_models = {}
        self.block_textures = []
        self.block_models = {}

        self.lang = {}

        if website:
            parsed_url = urllib.parse.urlparse(website)
            self.maven_group = ('.'.join(parsed_url.netloc.split('.')[::-1])
            + parsed_url.path.replace('/', '.')).replace('-', '_').lower()
        else:
            self.maven_group = (re.sub('[^a-zA-Z0-9_]', '', authors[0]) + '.'
            + re.sub('[^a-zA-Z0-9_ ]', '', mod_name).replace(' ', '.')).lower()
            
    def save(self):
        '''Saves the mod data into the mod folder.'''
        
        timer_start = timeit.default_timer()
        
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
            logger.info('Found existing mod folder.')
            edit_mod(self.mod_folder, java, self.lang, [self.item_models, self.block_models], [self.item_textures, self.block_textures])
        else:
            generate_mod(self.maven_group, self.modid, self.mod_name,
                         self.description, self.mod_version, self.minecraft_version,
                         self.directory, self.authors, self.website)
        
            timer_end = timeit.default_timer()
            elapsed_time = timer_end - timer_start
            time_string = f'{int(divmod(elapsed_time, 60)[0])}m {int(divmod(elapsed_time, 60)[1])}s \
{int(round(divmod(elapsed_time, 60)[1], 3) % 1 * 1000)}ms'
            logger.info('Finished saving mod in ' + time_string)
        
    def run(self):
        '''Runs the Minecraft client.'''
        self.save()

        logger.info('Launching Minecraft client...')

        command = 'gradlew runClient'
        if os.name == 'posix':
            command = './' + command
        run_cmd(command, self.mod_folder)

    def build(self, directory=os.getcwd()):
        '''
        Exports the mod as a jar file.

        Parameters:
        directory (str): The directory where the jar file is exported to. Defualts to the current working directory.
        '''
        timer_start = timeit.default_timer()
        
        self.save()

        logger.info('Building your mod...')

        if os.name == 'posix':
            command = './gradlew build'
        else:
            command = 'gradlew build'

        run_cmd(command, self.mod_folder)

        jar_file = os.path.join(self.mod_folder, 'build', 'libs', self.modid + '-' + self.mod_version + '.jar')

        shutil.copyfile(jar_file, directory)

        timer_end = timeit.default_timer()
        elapsed_time = timer_end - timer_start
        time_string = f'{int(divmod(elapsed_time, 60)[0])}m {int(divmod(elapsed_time, 60)[1])}s \
                        {int(round(divmod(elapsed_time, 60)[1], 3) % 1 * 1000)}ms'
        logger.info('Finished building in ' + time_string)

class Item:
    '''A class to represent an item.'''
    def __init__(self, mod, name, itemgroup, image=None):
        '''
        Creates an item.

        Parameters:
        mod (Mod): The mod class.
        name (str): Name of the item.
        itemgroup (str): The item's category, used for creative tabs - one of the following: COLORED_BLOCKS, NATURAL, FUNCTIONAL, REDSTONE, HOTBAR, SEARCH, TOOLS, COMBAT, FOOD_AND_DRINK, INGREDIENTS, SPAWN_EGGS, OPERATOR, or INVENTORY.
        image (str, optional): Path to the item's image. If no path is specified, it will look in the working directory for an image.
        '''

        texture = glob.glob('**/' + name.lower().replace(' ', '_') + '.png', recursive=True)
        
        if image:
            texture_file = image
        elif texture:
            texture_file = os.path.join(os.getcwd(), texture[0])
        else:
            logger.error('Could not find a texture for \'' + name + '\'')
            sys.exit()

        mod.item_models[name.lower().replace(' ', '_')] = {'parent': 'minecraft:item/generated', 'textures': {'layer0': f'{mod.modid}:item/{name.lower().replace(" ", "_")}'}}

        mod.item_textures.append(texture_file)
        
        mod.imports.add('net.minecraft.item.Item')
        mod.imports.add('net.minecraft.item.ItemGroups')
        mod.imports.add('net.fabricmc.fabric.api.item.v1.FabricItemSettings')
        mod.imports.add('net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents')
        mod.registry.append(f'Registry.register(Registries.ITEM, new Identifier("{mod.modid}", "{name.lower().replace(" ", "_")}"), {name.upper().replace(" ", "_")});')
        mod.registry.append(f'ItemGroupEvents.modifyEntriesEvent(ItemGroups.{itemgroup}).register(entries -> entries.add({name.upper().replace(" ", "_")}));')
        
        mod.lang[f'item.{mod.modid}.{name.lower().replace(" ", "_")}'] = name

        self.definition(mod, name, itemgroup)

    def definition(self, mod, name, itemgroup):
        mod.definitions.append(f'public static final Item {name.upper().replace(" ", "_")} = new Item(new FabricItemSettings());')

class FoodItem(Item):
    '''A class to represent a food item.'''
    def __init__(self, mod, name, hunger, saturation, itemgroup='FOOD_AND_DRINK', image=None):
        '''
        Creates a food item.

        Args:
        mod (Mod): The mod class.
        name (str): Name of the food.
        hunger (int): Amount of hunger points your item fills. Each hunger point is half a hunger shank.
        saturation (float): Saturation modifier for the item. The saturation modifier is equvalent to saturation restored / hunger points * 0.5.
        itemgroup (str, optional): The item's category, used for creative tabs - one of the following: COLORED_BLOCKS, NATURAL, FUNCTIONAL, REDSTONE, HOTBAR, SEARCH, TOOLS, COMBAT, FOOD_AND_DRINK, INGREDIENTS, SPAWN_EGGS, OPERATOR, or INVENTORY. Defaults to FOOD_AND_DRINK.
        image (str, optional): Path to the item's image. If no path is specified, it will look in the working directory for an image.
        '''
        self.hunger = hunger
        self.saturation = saturation
        super().__init__(mod, name, itemgroup, image)
    
    def definition(self, mod, name, itemgroup):
        mod.definitions.append(f'public static final Item {name.upper().replace(" ", "_")} = new Item(new FabricItemSettings().food(new FoodComponent.Builder().hunger({self.hunger}).saturationModifier({self.saturation}f).build()));')
        mod.imports.add('net.minecraft.item.FoodComponent')