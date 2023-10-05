# io_import_pskx

Experimental ActorX PSK/PSA importer for Blender 3.0+

I strongly recommend that you use https://github.com/DarklightGames/io_scene_psk_psa over this repo as I have only tested it with my custom sub-formats for PSK.

## Installation

- Download the repository (`Code -> Download ZIP` in the top right, or clone the repository.)
- Remove `-develop` from the filename.
- Open Blender.
- Navigate through Edit -> Preferences -> Addons.
- Click "Install..."
- Navigate to where the repository is downloaded.
- Install the zip/folder.

Alternatively copy the repository directory into your Blender Addons folder:

- `%APPDATA%/Blender Foundation/Blender/3.0/scripts/addons` on Windows.
- `~/.config/blender/3.0/scripts/addons` on Linux-based systems.
- `~/Library/Application Support/Blender/3.0/scripts/addons` on macOS.

The folder may not exist, if so you should create it. The `3.0` may be a different number.

- In the Addons Preferences window again, click refresh if you manually copied the folder.
- Search `Import ActorX`, click the checkbox to the left of the name.

## Usage

To import a PSK or PSA file, use the appropriate importer from `File -> Import -> ActorX ...`

## Notice

A lot of functionality in this addon is non-standard, such as the inclusion of custom chunks like `MORPHTARGET` and the
custom `ANIXHEAD` animation format. These are described below.

These are implemented in my fork of [CUE4Parse](https://github.com/yretenai/CUE4Parse), as of right now neither UModel
or FModel support these new chunks.

This addon has **only** been tested in the output of the modified library, of which the mesh exporter has undergone
significant changes to replicate Gltf exporting behavior and to accomodate for morph targets.

I do not plan or expect for official libraries to support these changes, nor will I support the output files from
"normal" programs.

## Outline of format-level changes

### PSK - MORPHTARGET#

Repeated chunk with different suffixes, similar to EXTRAUVS (`MORPHTARGET0`, `MORPHTARGET1`, ...)

Suffix indicates morph target index.

`16 bytes = int vertex_id, Vector position`

Maps wedge indexes to a different location for shape keys (morph target.)

### PSK - MORPHNAMES

Single chunk.

`64 bytes - char[64] name`

Maps morph target indexes to a non-unique name.

### PSK - PHYSICS0

Single Chunk.

`101 bytes - char[64] bone_name, byte type (0 = box, 1 = sphere, 2 = sphylinder), Vector offset, Vector rotation, Vector scale`

Attaches a shape to a bone.

### PSA - ANIXHEAD

Functionally identical to ANIMHEAD. Used to prevent issues with importers trying to import the standard format.

If the file signature is ANIXHEAD, expect SEQUENCES, POSTRACK and ROTTRACK streams instead of ANIMINFO and ANIMKEYS

### PSA - SEQUENCES

Single Chunk.

`72 bytes - char[64] name, float frame_rate, int additive_mode`

Lists sequences present in the file, along with it's projected frame rate.

`additive_mode` =

0. None
1. Both Position and Rotation are handled additively
2. Only position is handled additively(?)

### PSA - ROTTRACK#:#

Repeated chunk with different suffixes, different to EXTRAUVS.

Suffix indicates both the sequence and bone index: `ROTTRACK[SEQUENCEID]:[BONEID]` = `ROTTRACK0:0`, `ROTTRACK0:1`

`20 bytes - float time, Quaternion rotation`

Rotation keyframes for each sequence, bone and point in time. Will be interpolated linearly by Blender.

### PSA - POSTRACK#:#

Repeated chunk with different suffixes, different to EXTRAUVS.

Suffix indicates both the sequence and bone index: `POSTRACK[SEQUENCEID]:[BONEID]` = `ROTTRACK0:0`, `ROTTRACK0:1`

`16 bytes - float time, Vector position`

Location keyframes for each sequence, bone and point in time. Will be interpolated linearly by Blender.

### PSW - WRLDHEAD

File identifier for psw files

### PSW - WORLDACTORS

Single Chunk.

`368 bytes - char[64] name, char[256] asset_path, int parent, Vector position, Quaternion rotation, Vector scale,
int flags`

Lists actors present in the world.

### PSW - INSTMATERIAL

Single Chunk.

`72 bytes - int actor_id, int material_id, char[64] name`

Specifies material overrides for a specific actor.

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

## Why an animation format change?

The old format is quite inefficient by duplicating idle keyframes. This leads to ballooned keyframe sizes, along with
significant slowdown in Blender when used excessively (i.e. a long animation.)

The new format only stores keyframes if they actually change bone data, resulting in a smaller file and a more
traditional approach to animations.

This is a breaking change, thus a different magic value is used.
