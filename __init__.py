# Copyright (c) 2023, Mirko Barthauer
# All rights reserved.

# This source code is licensed under the MIT-style license found in the
# LICENSE file in the same directory of this source tree.

bl_info = {
    "name": "Render Partial Scene",
    "author": "m-kro",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "Add > Rendered Scene",
    "description": "Render a selection of strips to hard disk and add the rendered movie strip to the original scene in the first free channel",
    "warning": "",
    "doc_url": "",
    "category": "Sequencer",
}

import os
import bpy
from datetime import date

def firstEmptyChannel(startFrame, endFrame):
    if len(bpy.context.scene.sequence_editor.sequences_all) == 0:
        return 1
    return max(sequence.channel 
               for sequence in bpy.context.scene.sequence_editor.sequences_all 
               if startFrame < sequence.frame_start + .5*sequence.frame_duration < endFrame
               )

def findUnusedFileName(dir, defaultName):
    defaultPath = os.path.join(dir, defaultName)
    if not os.path.exists(defaultPath):
        return defaultPath
    counter = 0
    templateName = "%s_%%d%s" % (os.path.splitext(defaultName))
    while counter < 1000:
        newPath = os.path.join(dir, templateName % counter)
        if not os.path.exists(newPath):
            return newPath
        counter += 1
    return None

def contextReady(context):
    return context and context.scene and context.scene.sequence_editor

def copyAttributes(fromObj, toObj):
    fromSettings = {}
    for prop in fromObj.bl_rna.properties:
        if not prop.is_readonly:
            key = prop.identifier
            fromSettings[key] = getattr(fromObj, key)
    for key, val in fromSettings.items():
        setattr(toObj, key, val)

def selectInputStrips(strip, inferFromInput=False):
    inputAttrs = ('input_1', 'input_2')
    selectedMore = 0
    for inputAttr in inputAttrs:
        if getattr(strip, inputAttr, None) is not None:
            inputStrip = getattr(strip, inputAttr)
            if inferFromInput:
                if inputStrip.select and not strip.select:
                    strip.select = True
                    selectedMore += 1
            else:
                if strip.select and not inputStrip.select:
                    inputStrip.select = True
                    selectedMore += 1
    return selectedMore

    
class RenderStripSelectionOperator(bpy.types.Operator):
    """Render a selection of strips to hard disk and add the rendered movie strip to the original scene in the first free channel"""

    bl_idname = "sequencer.renderpartialscene"
    bl_label = "Render Partial Scene"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        return contextReady(context)

    def execute(self, context):
        # Check for the context and selected strips
        if not contextReady(context):
            self.report({'ERROR'}, "No valid context")
            return {'CANCELLED'}

        # Get the current scene and sequencer
        currentScene = context.scene
        sequencer = currentScene.sequence_editor
        currentFrame = bpy.context.scene.frame_current

        # Check if there are any selected strips
        if not any(strip.select for strip in sequencer.sequences_all):
            self.report({'ERROR'}, "Please select at least one strip.")
            return {'CANCELLED'}

        # Get the selected sequences in the sequencer
        selectedStrips = bpy.context.selected_sequences
        hasSound = len(set(["MOVIE", "SOUND"]).intersection([strip.type for strip in selectedStrips])) > 0
        
        # check if more related strips have to be selected
        selectedMore = 0
        for strip in selectedStrips:
            if len(strip.modifiers) > 0:
                for modifier in strip.modifiers:
                    if modifier.input_mask_type == 'STRIP' and modifier.input_mask_strip not in selectedStrips:
                        modifier.input_mask_strip.select = True
                        selectedMore += 1
            if isinstance(strip, bpy.types.EffectSequence):
                selectedMore += selectInputStrips(strip, inferFromInput=False)
        for strip in bpy.context.sequences:
            if not strip.select and isinstance(strip, bpy.types.EffectSequence):
                selectedMore += selectInputStrips(strip, inferFromInput=True)
        if selectedMore > 0:
            self.report({'INFO'}, "%d more related strips were selected." % selectedMore)
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        
        # Create a new scene
        newScene = bpy.ops.scene.new(type='EMPTY')
        newScene = bpy.context.scene 
        newScene.sequence_editor_create() 
        context.window.scene = newScene
        # Copy the scene properties from the current scene to the new scene
        newScene.world = currentScene.world
        newScene.frame_start = 0
        newScene.frame_end = 1
        if currentScene.render.image_settings.file_format == "FFMPEG":
            copyAttributes(currentScene.render.ffmpeg, newScene.render.ffmpeg)
        else:
            newScene.render.resolution_x = currentScene.render.resolution_x
            newScene.render.resolution_y = currentScene.render.resolution_y
            newScene.render.resolution_percentage = currentScene.render.resolution_percentage
            newScene.render.pixel_aspect_x = currentScene.render.pixel_aspect_x
            newScene.render.pixel_aspect_y = currentScene.render.pixel_aspect_y
            newScene.render.fps = currentScene.render.fps
            newScene.render.fps_base = currentScene.render.fps_base
            newScene.render.sequencer_gl_preview = currentScene.render.sequencer_gl_preview
            newScene.render.use_sequencer_override_scene_strip = currentScene.render.use_sequencer_override_scene_strip
            newScene.render.image_settings.file_format = "FFMPEG"
            newScene.render.ffmpeg.format = "MPEG4"
            newScene.render.ffmpeg.audio_codec = "AAC"
            
        # Set the path to the blend file
        renderDir = os.path.join(bpy.utils.user_resource("DATAFILES"),"RenderPartialScene_%s_%s" % (os.path.basename(bpy.data.filepath), str(date.today())))
        if not os.path.exists(renderDir):
            os.makedirs(renderDir)
        # Set the output path for the rendering
        outputPath = findUnusedFileName(renderDir, "rendered.mp4")
        if outputPath is None:
            # Switch back to the original scene
            bpy.data.scenes.remove(newScene, do_unlink=True)
            context.window.scene = currentScene
            self.report({"ERROR"}, "Too many similarly named movies in the user directory")
            return {"CANCELLED"}
        newScene.render.filepath = outputPath
        newScene.frame_start = min([strip.frame_final_start for strip in selectedStrips])
        newScene.frame_end = max([strip.frame_final_start + strip.frame_final_duration for strip in selectedStrips])
        newScene.frame_current = newScene.frame_start
        globalFrameStart = newScene.frame_start
        globalFrameEnd = newScene.frame_end

        # copy/paste strips between scenes
        area = [area for area in context.screen.areas if area.type == "SEQUENCE_EDITOR"][0]
        context.window.scene = currentScene
        bpy.ops.sequencer.copy()
        context.window.scene = newScene
        with bpy.context.temp_override(area=area):
            bpy.ops.sequencer.paste()

        # Render the strip to hard disk
        bpy.ops.render.opengl(animation=True, sequencer=True)

        # Switch back to the original scene
        bpy.data.scenes.remove(newScene, do_unlink=True)
        context.window.scene = currentScene

        # Reset to total top channel
        area = [area for area in context.screen.areas if area.type == "SEQUENCE_EDITOR"][0]
        with bpy.context.temp_override(area=area):
            insertChannel = firstEmptyChannel(globalFrameStart, globalFrameEnd)
            bpy.ops.sequencer.movie_strip_add(
                channel=insertChannel,
                filepath=outputPath,
                frame_start=globalFrameStart,
                overlap=0,
                sound=hasSound
            )
        
        # Clean up, redraw
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        bpy.context.scene.frame_current = currentFrame
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(RenderStripSelectionOperator.bl_idname, icon="SEQ_STRIP_DUPLICATE")


def register():
    bpy.utils.register_class(RenderStripSelectionOperator)
    bpy.types.SEQUENCER_MT_add.append(menu_func)


def unregister():
    bpy.types.SEQUENCER_MT_strip.remove(menu_func)
    bpy.utils.unregister_class(RenderStripSelectionOperator)


if __name__ == "__main__":
    register()
