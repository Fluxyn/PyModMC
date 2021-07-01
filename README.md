# PyModMC
PyModMC is a Minecraft modding library made for Python. PyModMC is built on top of the [Fabric API](https://fabricmc.net/).

In order to make minecraft mods, you need a JDK (Java Development Kit). You can get one here: https://adoptopenjdk.net. 


# Installation
You can download PyModMC from PyPI using this pip command:
```
$ pip install PyModMC
```

# Usage
Here is an example of PyModMC:
```
from PyModMC import Mod

description = 'A test mod.'
test_mod = Mod('Test Mod', '0.0.1', description, '1.16', ['fluxyn'])

test_mod.Item('Donut', 'food')
test_mod.run()
```
###### Note: A wiki containing detailed instructions is coming soon.
