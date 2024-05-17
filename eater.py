bl_info = {
    "name": "eater",
    "blender": (4,1,0),
    "category": "Animation"
}

import bpy
import math
import random
import heapq
import collections

# refactor to take params as integers instead?
def pythagorean_distance(obj1, obj2):
    x1, y1, z1 = obj1.location.x, obj1.location.y, obj1.location.z
    x2, y2, z2 = obj2.location.x, obj2.location.y, obj2.location.z
    return math.sqrt(pow(x2-x1,2) + pow(y2-y1,2) + pow(z2-z1,2))

class TreeNode:
    def __init__(self, x):
        self.obj = x
        self.nodes = []

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
                scn.selected_objs_index = len(scn.selected_objs) - 1
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
        
        if len(scn.selected_objs) == 0:
            self.report({'INFO'}, 'No objects selected, no changes were made')
            return {'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        
        # read parameters
        frame_step = scn.eater_props.frame_step
        object_step = scn.eater_props.object_step
        process_order = scn.eater_props.process_order
        starting_point = None
        if process_order == 'LOCATION':
            starting_point = scn.eater_props.starting_point
            if starting_point == None:
                self.report({'INFO'}, 'No starting point selected, no changes were made')
                return {'CANCELLED'}
        start_visibility = scn.eater_props.start_visibility
        cur_frame = scn.eater_props.start_frame
        buffer_frame = scn.eater_props.start_frame - 1
        
        # keyframing for random mode
        if process_order == 'RANDOM':
            choices = []
            for i in range(len(scn.selected_objs)):
                choices.append(i)
                
            random.shuffle(choices)
            
            for i in range(len(choices)):
                
                # digging through types to get to the data we want 
                item = scn.selected_objs[choices[i]]
                obj = item.obj
                
                if scn.objects.find(obj.name) == -1:
                    self.report({'INFO'}, '%s was renamed or deleted' % obj.name)
                    continue

                obj.hide_render = start_visibility == 'INVISIBLE'
                obj.hide_viewport = obj.hide_render
                obj.keyframe_insert('hide_render', frame=buffer_frame)
                obj.keyframe_insert('hide_viewport', frame=buffer_frame)
                
                obj.hide_render = not obj.hide_render
                obj.hide_viewport = not obj.hide_viewport
                obj.keyframe_insert('hide_render', frame=cur_frame)
                obj.keyframe_insert('hide_viewport', frame=cur_frame)
                
                if (i + 1) % object_step == 0:
                    cur_frame += frame_step
                
        # keyframing for location-based mode        
        elif process_order == 'LOCATION':
            
            if scn.objects.find(starting_point.name) == -1:
                self.report({'INFO'}, 'Cannot resolve starting point, %s was removed or deleted. No changes were made.' % starting_point.name)
                return {'CANCELLED'}
            
            # find the index of the starting point
            # if the starting point is not a selected object, get the index of the nearest object to the starting point
            starting_idx = -1
            closest_idx = -1
            min_distance = math.inf
            for i in range(len(scn.selected_objs)):
                if scn.selected_objs[i].name == starting_point.name:
                    starting_idx = i
                    break
                if scn.objects.find(scn.selected_objs[i].name) is not -1 and pythagorean_distance(starting_point, scn.selected_objs[i].obj) < min_distance:
                    closest_idx = i
                
            if starting_idx == -1:
                starting_idx = closest_idx
            
            # calculate the distance between every possible pair of objects (expensive)
            n = len(scn.selected_objs)
            cost_map = {i : [] for i in range(n)}
            tree_map = {i : None for i in range(n)}
            for i in range(n):
                item1 = scn.selected_objs[i]
                obj1 = item1.obj
                tree_map[i] = TreeNode(obj1)
                for j in range(i + 1, n):
                    item2 = scn.selected_objs[j]
                    obj2 = item2.obj
                    cost = pythagorean_distance(obj1, obj2)
                    cost_map[i].append([cost, j])
                    cost_map[j].append([cost, i])  
            
            # prim's alg
            visited = set()
            pq = [[0,0,0]] # min heap, [cost, to object, from object]
            while len(visited) < n:
                cost, i, j = heapq.heappop(pq)
                if i in visited:
                    continue
                if i != j:
                    tree_map[i].nodes.append(j)
                    tree_map[j].nodes.append(i)
                visited.add(i)
                for newcost, newobj in cost_map[i]:
                    if newobj not in visited:
                        heapq.heappush(pq, [newcost, newobj, i])
                
            # bfs
            visited.clear()
            q = collections.deque()
            q.append(starting_idx)
            
            while q:
                lenq = len(q) # i think python avoids re-evaluating the queue length by default but this is here just in case
                for i in range(lenq):
                    
                    cur_idx = q.popleft()
                    item = scn.selected_objs[cur_idx]
                    obj = item.obj
                    visited.add(cur_idx)
                    
                    for adj_idx in tree_map[cur_idx].nodes:
                        if adj_idx in visited:
                            continue
                        q.append(adj_idx)
                        
                    if scn.objects.find(obj.name) == -1:
                        self.report({'INFO'}, '%s was renamed or deleted' % obj.name)
                        continue
                    
                    obj.hide_render = start_visibility == 'INVISIBLE'
                    obj.hide_viewport = obj.hide_render
                    obj.keyframe_insert('hide_render', frame=buffer_frame)
                    obj.keyframe_insert('hide_viewport', frame=buffer_frame)
                    
                    obj.hide_render = not obj.hide_render
                    obj.hide_viewport = not obj.hide_viewport
                    obj.keyframe_insert('hide_render', frame=cur_frame)
                    obj.keyframe_insert('hide_viewport', frame=cur_frame)
                    
                    if len(visited) % object_step == 0:
                        cur_frame += frame_step
                        
                  
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
                    ('RANDOM', 'Random', 'The next objects to be affected are chosen at random'),
                    ('LOCATION', 'Location-based', 'The next objects to be affected are based on proximity to the last affected objects')
                )
    )
    
    starting_point: bpy.props.PointerProperty(
        type = bpy.types.Object,
        description = 'Choose where the animation will propagate from'
    )
    
    start_visibility: bpy.props.EnumProperty(
        items = (
                    ('VISIBLE', 'Start Visible', 'Objects start visible and are gradually toggled invisible'),
                    ('INVISIBLE', 'Start Invisible', 'Objects start invisible and are gradually toggled visible')
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
        if eater_props.process_order == 'LOCATION':
            layout.label(text='Starting point:')
            layout.prop_search(eater_props, 'starting_point', bpy.data, "objects", text='')
        
        layout.separator()
        
        ### BEGIN-STATE CONFIGURATION ###
        row = layout.row()
        row.prop(eater_props, 'start_visibility', expand=True)
        
        row = layout.row()
        row.prop(eater_props, 'start_frame')
        
        frame_step = eater_props.frame_step
        object_step = eater_props.object_step
        start_frame = eater_props.start_frame
        num_objs = len(scn.selected_objs)
        end_frame = math.ceil(((num_objs / object_step) * frame_step) + start_frame - 1)
        layout.label(text=f'End frame: {end_frame}')
        
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