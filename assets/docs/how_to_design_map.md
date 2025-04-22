# How to Design Map

- You can easily design maps using `map_designer.xlsx`. 
- After completing the design, copy the whole map and directly paste to `assets/map/map{LEVEL}.txt`.
- Create a `assets/map/unit{LEVEL}.txt` file and add initial units and buildings.

### Format

map0.txt:
```
P	P	P	P
P	P	P	H
P	F	P	P
P	F	F	P
```

unit0.txt:（x	y	type	player_id）
```
0	0	commando	0
0	1	tank	1
0	2	factory	0
```

### Notes
- map coordinates start at (0,0)
- player index starts at 0, -1 means neutral
- index of map file and unit file should be identical