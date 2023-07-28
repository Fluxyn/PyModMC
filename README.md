# PyModMC
PyModMC is a Minecraft modding library made for Python. It is built on top of the [Fabric API](https://fabricmc.net/). The project is still in its early stages. In future updates I am planning to add:
 - Blocks
 - Potions
 - Tools and Armor
 - Crops
 - Crafting Recipes
 - UI
 - Entities
 - World Generation/Dimensions

```python
from PyModMC import *

test_mod = Mod('Test Mod', '0.0.1', 'A test mod.', '1.20.1', ['Fluxyn'])
FoodItem(test_mod, 'Donut', 1, 1)
test_mod.run()
```

In order to make Minecraft mods, you need a Java Development Kit. Run the `javac` command to see if you already have one. If not, you can get one [here](https://adoptium.net/releases.html). Make sure to enable 'Set JAVA_HOME variable' and restart your computer after installation.

# Installation
Install PyModMC with [pip](https://pypi.org/):
```
$ pip install PyModMC
```
On your first run, PyModMC will scrape the Modrinth API to get every single Fabric version and the corresponding Minecraft version. This can take a couple of minutes, but the data is cached and won't be updated until another version of Fabric is released.

# Documentation
## `Mod` class
```python
Mod(mod_name, mod_version, description, minecraft_version, authors, website='', directory=os.getcwd())
```
The `Mod` class represents a Minecraft mod. Upon initializing, it will copy the file structure from the [Fabric example mod](https://github.com/FabricMC/fabric-example-mod/) and configure it using the values above.
 -  The `save` function converts the python data into Java and saves it in the mod folder. Used internally by `run` and `build`.
    ```python
    mod.save()
    ```
 - The `run` function Saves and launches a new instance of Minecraft with Fabric and the mod installed. Useful for testing your mod.
    ```python
    mod.run()
    ```
 - The `build` function Saves and exports your mod as a .jar file.
    ```python
    mod.export()
    ```
## Object classes
Object classes represent any object you can mod into Minecraft such as items and blocks. In the future, these classes will have shared event and Java scripting functions, making it easy to add custom behavior to any item or block you add.

 - The `Item` class creates an item.
    ```python
    Item(mod, name, itemgroup, image=None):
    ```

 - The `FoodItem` class creates an edible item. Inherets from `Item`.
    ```python
    FoodItem(mod, name, hunger, saturation, itemgroup='FOOD_AND_DRINK', image=None)
    ```

## Other functions
 - The `change_locale` function takes a Minecraft locale code (check `locale_codes.txt`) and replaces the current locale detected by the library.
    ```python
    change_locale(code)
    ```