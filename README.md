# PyModMC
PyModMC is a Minecraft modding library made for Python. It is built on top of the [Fabric API](https://fabricmc.net/). The project is still in it's early stages and in future updates I am planning to add:
 - Blocks
 - Potions
 - Tools and Armor
 - Crops
 - Crafting Recipes
 - UI
 - Entities
 - World Generation/Dimensions

In order to make Minecraft mods, you need a Java Development Kit. You can get one [here](https://adoptium.net/releases.html). You might have already downloaded a JDK on your computer. In that case, you can run the `javac` command in your terminal to find out.

# Installation
Install PyModMC with [pip](https://pypi.org/):
```
$ pip install PyModMC
```

# Usage
Here is an example of PyModMC:
```python
from PyModMC import Mod

test_mod = Mod('Test Mod', '0.0.1', 'A test mod.', '1.16', ['Fluxyn'])
test_mod.Item('Donut', 'food')
test_mod.run()
```

## The Mod Class
The `Mod` class is all you need to get started. It contains several functions:
 - __save__ - Converts data into Java and saves it in the mod folder. Used internally by `run` and `build`.
 - __run__ - Launches a new instance of Minecraft with Fabric and the mod installed.
 - __build__ - Exports mod as jar file.
 - __Item__ - Creates a new item.
 - __FoodItem__ - Similar to `Item`, but it is edible.

# Other Notes
 - On your first run, PyModMC will scrape the Modrinth API to get every single Fabric version and the corresponding Minecraft version. This can take a couple of minutes, but the data is cached and won't be updated until another version of Fabric is released.
