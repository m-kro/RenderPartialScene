# License
This work is licensed under the MIT license.

# Installation
The folder ./ contains all the necessary files. Make a zip archive out of it and you are ready to 
install in in the Blender UI: 
`Menu > Edit > Preferences > Addons > Install...`.

# Usage
This addon automates a workflow during video editing in Blender. It lets you render the selected strips in a 
separate scene to your user directory and import it immediately afterwards in the first free channel above the existing strips.
Render settings will be inferred from the current ones - only if the current settings do not lead to video output some default settings 
will be applied.

This helps with complex compositions consisting of several normal and effect strips on which you want to apply further modifiers, effects or transitions.
Those can only applied to an exact number of input strips (usually up to two). Instead of doing all the rendering manually, the addon gives you the option 
to get the result strip within a few clicks.

- Open the VSE view if you haven't done yet
- Select the strips you want to render (strips connected through modifiers and effect strip input are selected automatically)
- Choose Add > Render Partial Scene from the VSE menu
- Wait for the render process to finish - the result strip is placed on the frame range used by the union of the selected strips

The result strips are written to a subdirectory of the Blender installation application data directory, which on Windows defaults to 
```
C:\Users\username\AppData\Roaming\Blender Foundation\Blender\version\datafiles
```