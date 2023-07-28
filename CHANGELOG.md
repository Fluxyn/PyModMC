# Changelog
This file documents the changes of PyModMC.

## [Alpha 1.2.2](https://pypi.org/project/PyModMC/1.2.2a0/) - 7/28/2023
 - Migrated to Modrinth API v2.
 - Fixed extra tab characters on the saving mod timer.
 - Added the use of Github API to find the most recent template branch to download.
 - Changed docstring format from Google to PEP 257.
 - Changed `Item` and `FoodItem` to classes.
 - Updated the error logging system.
 - Changed how locales are detected to work on Windows.
 - Added `change_locale` function.
 - Updated Java code to newer versions of Fabric API.

## [Alpha 0.2.2](https://pypi.org/project/PyModMC/0.2.2a0/) - 12/12/2021
 - Only generates Gradle wrapper and gives executable permissions to `gradlew` when the mod is first made, instead of every time Gradle is used.
 - Switched from running `chmod` command to using `os.chmod`.
 - Added automatic detection of locale code.
 - Changed the default mod directory from the desktop to the current working directory.
 - Added `LOCALE_CODE` and `logger` to `__init__.py`.
 - Added retry if rate-limited by the Modrinth API.
 - Added handling the fact that some unstable Minecraft versions are not recorded in Fabric's Modrinth Page.

## [Alpha 0.1.2](https://pypi.org/project/PyModMC/0.1.2a0/) - 9/4/2021
 - Added `Build` function to `Mod` class. Exports the mod as a jar file.
 - Added compatibility with the logging module.

## [Alpha 0.0.2](https://pypi.org/project/PyModMC/0.0.2a0/) - 7/6/2021
 - Added `FoodItem` function to `Mod` class.
 - Added timer to `Mod.save` function.
 - Added docstrings to functions.
 - Fixed `ModuleNotFoundError` in `__init__.py`.

## [Alpha 0.0.1](https://pypi.org/project/PyModMC/0.0.1a0/) - 7/1/2021
Initial release of PyModMC.