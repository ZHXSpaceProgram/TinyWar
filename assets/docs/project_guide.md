# Project Guide

## Code Structure

### main.py

- **Main Loop**
    - Handle events like keyboard, mouse, etc.
    - Render the game

### game.py

- **class GameManager:**

    - Manage game status(players, units, map, etc.)
    - Handle game logic(select, move, attack, etc.)
    - Save and load game

- **class GameMap:**

- **class Player:**

- **class Effect:**

    - For visual effect over the map

- **class Shop:**


### unit.py

- **class Unit:**

    - initial properties of unit are recorded in `Unit.PROPERTIES`


- **class Build(Unit):**

### const.py

- **class Terrain:**

## Design Notes

### Selection, Move and Attack

- **Selection**
    - `main.select_and_interact()` is called in handling events.
    - `main.select_and_interact()` calls `GameManager.select_unit()` to try selecting a unit.
    - `select_unit()` checks if there are any units or builds in the cell under the mouse.
    - `select_unit()` calls `GameManager.calculate_possible_moves()` to calculate possible move and attack positions, which are recorded in `GameManager.possible_moves` and `GameManager.possible_attacks`.
    - `calculate_possible_moves()` calls `GameManager._can_attack()` to check if the source can attack the target based on the units' properties.
    - If `select_unit()` succeeded, `select_and_interact()` checks if the selected unit is interactable.

- **Move**
    - `GameManager.move_selected_unit()` is called in handling events.
    - If the position to move is not in `GameManager.possible_moves`, `move_selected_unit()` returns False.
    - `move_selected_unit()` moves the unit.
    - If the unit can't attack after it moved (due to the unit's traits or lack of legal targets), `move_selected_unit()` sets `unit.attacked` to True and return False.
    - If the unit can still attack, return True.

- **Attack**
    - `GameManager.attack()` is called in handling events.
    - `attack()` checks if the position of the source and the target are as recorded in `possible_attacks`.
    - `attack()` checks if the target is capturable.
    - `attack()` calls `GameManager._calculate_damage()` and deals damage to the target.
    - If the target dies, `attack()` calls `GameManager._unit_die()` to capture the target.
    - Else `attack()` calls `GameManager._can_attack()` to check if the target can fight back the source.
    - If so, calls `_calculate_damage()`, deals damage to the source and check death likewise.

### Map

    - GameMap.terrain[y][x]: The first index is y, the second index is x
## Todo

- Add a new state for selecting target area with mouse, for special skills or constructing buildings

