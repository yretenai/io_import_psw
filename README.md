# io_import_pskx

ActorX PSK/PSA importer for Blender 3.0+

## Installation

- Download the repository (`Code -> Download ZIP` in the top right, or clone the repository.)
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

These are implemented in my fork of [CUE4Parse](https://github.colm/yretenai/CUE4Parse), as of right now neither UModel
or FModel support these new chunks.

This addon has **only** been tested in the output of the modified library, of which the mesh exporter has undergone
significant changes to replicate Gltf exporting behavior and to accomodate for morph targets.

I do not plan or expect for official libraries to support these changes, nor will I support the output files from 
"normal" programs.

## Outline of format-level changes

### PSK - MORPHTARGET#

Repeated chunk with different suffixes, similar to EXTRAUVS (`MORPHTARGET0`, `MORPHTARGET1`, ...)

Suffix indicates morph target index.

`16 bytes = int vertex_id, FVector position`

Maps wedge indexes to a different location for shape keys (morph target.)

### PSK - MORPHNAMES

Single chunk.

`64 bytes - char[64] name`

Maps morph target indexes to a non-unique name.

### PSK - PHYSICS0

Single Chunk.

`101 bytes - char[64] bone_name, byte type (0 = box, 1 = sphere, 2 = sphylinder), FVector offset, FVector rotation, FVector scale`

Attaches a shape to a bone.

### PSA - ANIXHEAD

Functionally identical to ANIMHEAD. Used to prevent issues with importers trying to import the standard format.

If the file signature is ANIXHEAD, expect SEQUENCES, POSTRACK and ROTTRACK streams instead of ANIMINFO and ANIMKEYS

### PSA - SEQUENCES

Single Chunk.

`68 bytes - char[64] name, float32 frame_rate`

Lists sequences present in the file, along with it's projected frame rate.

### PSA - ROTTRACK#:#

Repeated chunk with different suffixes, different to EXTRAUVS.

Suffix indicates both the sequence and bone index: `ROTTRACK[SEQUENCEID]:[BONEID]` = `ROTTRACK0:0`, `ROTTRACK0:1`

`20 bytes - float32 time, FQuaternion rotation`

Rotation keyframes for each sequence, bone and point in time. Will be interpolated linearly by Blender.

### PSA - POSTRACK#:#

Repeated chunk with different suffixes, different to EXTRAUVS.

Suffix indicates both the sequence and bone index: `POSTRACK[SEQUENCEID]:[BONEID]` = `ROTTRACK0:0`, `ROTTRACK0:1`

`16 bytes - float32 time, FVector position`

Location keyframes for each sequence, bone and point in time. Will be interpolated linearly by Blender.

### PSW - WRLDHEAD

File identifier for psw files

### PSA - WORLDACTORS

Single Chunk.

`368 bytes - char[64] name, char[256] asset_path, int parent, FVector position, FQuaternion rotation, FVector scale, 
int flags`

Lists actors present in the world.

### PSW - INSTMATERIAL

Single Chunk.

`72 bytes - int actor_id, int material_id, char[64] name`

Specifies material overrides for a specific actor.

### PSW - LANDSCAPE

Single Chunk.

`284 bytes - char[256] map_path, int actor_id, float x, float y, int type, int size, float scale, float offset`

Specifies landscape components, last two values are speculative and uncertain how it functions. 
These values are the X and Z of the "Bias" property.

Landscape importing is imprefect at best, and often completely wrong, but it constructs
the tiles correctly, at least.

## Why an animation format change?

The old format is quite inefficient by duplicating idle keyframes. This leads to ballooned keyframe sizes, along with 
significant slowdown in Blender when used excessively (i.e. a long animation.)

The new format only stores keyframes if they actually change bone data, resulting in a smaller file and a more 
traditional approach to animations.

This is a breaking change, thus a different magic value is used.
