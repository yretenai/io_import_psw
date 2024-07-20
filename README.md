# io_import_psw

PSW importer for Blender 4.0+

PSW files are scene files exported using my [CUE4Parse fork's](https://github.com/yretenai/CUE4Parse) "AssetDumper" utility program. **Zero support is given.**

## Requirements

- [UEFormat](https://github.com/halfuwu/UEFormat/)

## Installation

- Download the repository (`Code -> Download ZIP` in the top right, or clone the repository.)
- Remove `-develop` from the filename.
- Open Blender.
- Navigate through Edit -> Preferences -> Addons.
- Click "Install..."
- Navigate to where the repository is downloaded.
- Install the zip/folder.

Alternatively copy the repository directory into your Blender Addons folder:

- `%APPDATA%/Blender Foundation/Blender/4.0/scripts/addons` on Windows.
- `~/.config/blender/4.0/scripts/addons` on Linux-based systems.
- `~/Library/Application Support/Blender/4.0/scripts/addons` on macOS.

The folder may not exist, if so you should create it. The `4.0` may be a different number.

- In the Addons Preferences window again, click refresh if you manually copied the folder.
- Search `Import PSW`, click the checkbox to the left of the name.

## Outline of format

### PSW - WRLDHEAD

File identifier for psw files

### PSW - WORLDACTORS

Single Chunk.

`368 bytes - char[64] name, char[256] asset_path, int parent, Vector position, Quaternion rotation, Vector scale,
int flags`

Lists actors present in the world, deprecated

### PSW - WORLDACTORS::2

Single Chunk.

`560 bytes - char[256] name, char[256] asset_path, int parent, Vector position, Quaternion rotation, Vector scale,
int flags`

Lists actors present in the world, deprecated

### PSW - WORLDACTORS::3

Single Chunk.

`568 bytes - char[256] name, char[256] asset_path, int parent, Vector position, Quaternion rotation, Vector scale,
int flags, int material_start, int material_end`

Lists actors present in the world.

### PSW - INSTMATERIAL

Single Chunk.

`72 bytes - int actor_id, int material_id, char[64] name`

Specifies material overrides for a specific actor, deprecated

### PSW - INSTMATERIAL::2

Single Chunk.

`264 bytes - int actor_id, int material_id, char[256] name`

Specifies material overrides for a specific actor, deprecated

### PSW - ACTORMATERIAL

Single Chunk.

`512 bytes - char[256] name, char[256] asset_path`

Material path info

### PSW - LANDSCAPE

Single Chunk.

`296 bytes - char[256] map_path, int actor_id, float[2] xy, int type, int size, float height_mod, float[2] offset, int[2] dimensions`

Sector size is a cube of size.

Specifies landscape components. To get the real value of the height, subtract 0.5 and multiply by 2 then by height_mod.

Height_mod is calculated as `256 / (scale.UP + 1)`. When height maps are calculated, the UP value is eqauivalent to
size.

So if scale.UP is not identical to size, adjust accordingly. You can optimize it by setting the vertical scale to 256
and ignoring height_mod.

Offset is the offset in the texture map, multiple sectors can subdivide the same texture. `Dimensions` indicates how many
sectors should be in the texture.
