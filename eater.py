bl_info = {
    "name": "eater",
    "blender": (4,1,0),
    "category": "Animation"
}

import bpy

class TreeNode:
    def __init__(self, x):
        self.obj = x
        self.left = None
        self.right = None

### OPERATORS

class EATER_add_selected_objs(bpy.types.Operator):
    bl_idname = 'eater.add_selected_objs'
    bl_label = 'Add Selected Objects to List'
    bl_description = 'Adds all the items selected in the viewport to the list'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        scn = context.scene
        selected_objs = context.selected_objects
        
        unique_objs = set()
        for obj in scn.selected_objs:
            unique_objs.add(obj.name)
        
        if selected_objs:
            for obj in selected_objs:
                if obj.name in unique_objs:
                    self.report({'INFO'}, '%s is already in list' % obj.name)
                    continue
                
                item = scn.selected_objs.add()
                item.name = obj.name
                item.obj = obj
        else:
            self.report({'INFO'}, 'Nothing selected in viewport, no objects added')
        return {'FINISHED'}
      
class EATER_remove_selected_objs(bpy.types.Operator):
    bl_idname = 'eater.remove_selected_objs'
    bl_label = 'Remove Selected Objects'
    bl_description = 'Removes objects selected in the list widget (not in the viewport)'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    def execute(self, context):
        scn = context.scene
        idx = scn.selected_objs_index
        try:
            obj = scn.selected_objs[idx]
        except IndexError:
            self.report({'INFO'}, 'Object could not be found')
        else:
            scn.selected_objs_index -= 1
            scn.selected_objs.remove(idx)
        return {'FINISHED'}
      
class EATER_remove_selected_objs_viewport(bpy.types.Operator):
    bl_idname = 'eater.remove_selected_objs_viewport'
    bl_label = 'Remove Selected Objects (Viewport)'
    bl_description = 'Removes from the list any objects that are selected in the viewport'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    def execute(self, context):
        scn = context.scene
        to_be_removed = context.selected_objects
        
        if to_be_removed:
            for obj in to_be_removed:
                
                # inefficient to recompute this dict everytime but (supposedly) necessary because blender updates the indexes
                unique_objs = {}
                for i, selected in enumerate(scn.selected_objs):
                    unique_objs[selected.name] = i
                
                if unique_objs.get(obj.name) != None:
                    idx = unique_objs.get(obj.name)
                    scn.selected_objs_index -= 1
                    scn.selected_objs.remove(idx)
                    unique_objs.pop(obj.name)
                else:
                    self.report({'INFO'}, 'Selected object is not in list, no objects removed')
        else:
            self.report({'INFO'}, 'Nothing selected in viewport, no objects removed')
        return {'FINISHED'}
      
class EATER_clear_list(bpy.types.Operator):
    bl_idname = 'eater.clear_list'
    bl_label = 'Clear List'
    bl_description = 'Removes all objects from the list'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    def execute(self, context):
        if context.scene.selected_objs:
            context.scene.selected_objs.clear()
            self.report({'INFO'}, 'List cleared')
        else:
            self.report({'INFO'}, 'Nothing to clear')
        return {'FINISHED'}
        
class EATER_execute(bpy.types.Operator):
    bl_idname = 'eater.execute'
    bl_label = 'Go'
    bl_description = 'Go'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    def execute(self, context):
        scn = context.scene
        
        ### steps ###
        # create an object to store our arguments
        # use these arguments to call the correct functions
        # make sure that every object in the list IS STILL AN EXISTING OBJECT
        # follow the access template below to send the correct array
        
        ### ACCESS TEMPLATE ###
        #for item in scn.selected_objs:
            #obj = item.obj
            #obj.location.x += 1.0
        
        return {'FINISHED'}
        
### UI

class EATER_OBJ_UL(bpy.types.UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        
        custom_icon = "OUTLINER_OB_%s" % item.obj.type
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item.obj, 'name', text='', emboss=False, icon=custom_icon)
        else:
            layout.alignment = 'CENTER'
            layout.label(text='', icon=custom_icon)
            

class EATER_Props(bpy.types.PropertyGroup):
    
    frame_step: bpy.props.IntProperty(
        name = "Frame Step",
        description = "Controls how many frames to wait before processing another set of objects",
        step = 1,
        min = 1,
        soft_max = 60,
        default = 1
    )
    
    object_step: bpy.props.IntProperty(
        name = "Object Step",
        description = "Controls how many objects are simultaneously processed at every step",
        step = 1,
        min = 1,
        soft_max = 10,
        default = 1
    )
    
    process_order: bpy.props.EnumProperty(
        items = (
                    ('0', 'Random', 'The next objects to be affected are chosen at random'),
                    ('1', 'Location-based', 'The next objects to be affected are based on proximity to the last affected objects')
                )
    )
    
    starting_point: bpy.props.PointerProperty(
        type = bpy.types.Object,
        description = 'Choose where the animation will propagate from'
    )
    
    start_visibility: bpy.props.EnumProperty(
        items = (
                    ('0', 'Start Visible', 'Objects start visible and are gradually toggled invisible'),
                    ('1', 'Start Invisible', 'Objects start invisible and are gradually toggled visible')
                )
    )
    
    start_frame: bpy.props.IntProperty(
        name = "Start Frame",
        description = "Controls the frame where the animation will begin",
        step = 1,
        default = 1
    )

class EATER_UI(bpy.types.Panel):
    
    bl_label = 'eater'
    bl_category = 'eater'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "objectmode"
    
    def draw(self, context):
        scn = context.scene
        layout = self.layout
        eater_props = context.scene.eater_props
        
        layout.separator()
        
        ### OBJECT SELECTION ###
        layout.label(text='Selected objects:')
        row = layout.row()
        row.template_list('EATER_OBJ_UL', 'OBJS', scn, 'selected_objs', scn, 'selected_objs_index', type='DEFAULT')
        
        row = layout.row()
        row.operator('eater.add_selected_objs', icon='ADD')
        
        row = layout.row()
        row.operator('eater.remove_selected_objs', icon='REMOVE')
        
        row = layout.row()
        row.operator('eater.remove_selected_objs_viewport', icon='REMOVE')
        
        row = layout.row()
        row.operator('eater.clear_list', icon='X')
        
        layout.separator()
        
        ### BATCHING CONTROLS ###
        row = layout.row()
        row.prop(eater_props, 'frame_step')
        
        row = layout.row()
        row.prop(eater_props, 'object_step')
        
        layout.separator()
        
        ### ALGORITHM CONTROLS ###
        row = layout.row()
        row.prop(eater_props, 'process_order', expand=True)
        if eater_props.process_order == '1':
            layout.label(text='Starting point:')
            layout.prop_search(eater_props, 'starting_point', bpy.data, "objects", text='')
        
        layout.separator()
        
        ### BEGIN-STATE CONFIGURATION ###
        row = layout.row()
        row.prop(eater_props, 'start_visibility', expand=True)
        
        row = layout.row()
        row.prop(eater_props, 'start_frame')
        
        ### EXECUTION ###
        layout.separator()
        
        row = layout.row()
        row.operator('eater.execute')
        

class EATER_PG_OBJ_Collection(bpy.types.PropertyGroup):
    
    obj: bpy.props.PointerProperty(
        name = "Object",
        type = bpy.types.Object
    )
        
classes = [
    EATER_add_selected_objs, 
    EATER_remove_selected_objs, 
    EATER_remove_selected_objs_viewport,
    EATER_clear_list, 
    EATER_execute,
    EATER_UI, 
    EATER_Props, 
    EATER_OBJ_UL, 
    EATER_PG_OBJ_Collection
]

def register():    
    for cl in classes:
        bpy.utils.register_class(cl)
        
    bpy.types.Scene.eater_props = bpy.props.PointerProperty(type=EATER_Props)
    bpy.types.Scene.selected_objs = bpy.props.CollectionProperty(type=EATER_PG_OBJ_Collection)
    bpy.types.Scene.selected_objs_index = bpy.props.IntProperty()

def unregister():
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)
        
    del bpy.types.Scene.eater_props
    del bpy.types.Scene.selected_objs
    del bpy.types.Scene.selected_objs_index

if __name__ == "__main__":
    register()