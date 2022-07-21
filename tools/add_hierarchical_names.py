""" This is a Fusion 360 script that updates body names based on the presence
    of tags of the form: TAG(<name>) in the hierarchy component names. It is
    useful as a preprocessor for exports that flatten the hierarchy (like the
    OBJ file export for example) """

import adsk.core, adsk.fusion, adsk.cam, traceback

def FindTag(name):
    """ Find something looking like TAG(###) in the name
    Args:
      name: the name to explore
    Returns:
      the tag if it exists, None otherwise
    """
    tag_start = name.find('TAG(')
    if tag_start == -1:
        return None
    tag_start += 4
    tag_end = name.find(')', tag_start)
    if tag_end == -1:
        return None
    return name[tag_start:tag_end]


def ListAllTaggedOccurences(occurence):
    """ List all the occurences that are tagged under this occurence
    Args :
      occurence: The occurence to explore
    Returns:
      A list of (tag, occurence) tuples
    """
    name = occurence.name
    tag = FindTag(name)
    if tag:
        return [(tag, occurence)]
    children = occurence.childOccurrences
    if (len(children)):
        occs = []
        for child in children:
            occs += ListAllTaggedOccurences(child)
        return occs
    else:
        return []
    

def ListAllSubBodies(occurence):
    """ List all the components under this occurence
    Args :
      occurence: The occurence to explore
    Returns:
      A list of bodies
    """
    children = occurence.childOccurrences
    if (len(children)):
        components = []
        for child in children:
            components += ListAllSubBodies(child)
        return components
    else:
        return occurence.component.bRepBodies

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        title = 'Hierarchy rename'
        if not design:
            ui.messageBox('No active design', title)
            return

        # Get all occurrences at the top level
        root = design.rootComponent
        occs = root.occurrences

        tags = []
        for occ in occs:
            tags += ListAllTaggedOccurences(occ)

        num_tags_touched = 0
        num_tags_updated = 0
        for (tag, occ) in tags:
            ui.messageBox("Processing tag: " + tag)
            bodies = ListAllSubBodies(occ)
            names = []
            for body in bodies:
                num_tags_touched += 1
                name = body.name
                new_name = name
                # Check if we already tagged that body in the past, in
                # which case we just remove the old tag
                tag_end = name.find('/')
                if(tag_end != -1):
                    new_name = new_name[(tag_end+1):]
                if (tag != "delete"):
                    new_name = tag + "/" + new_name
                body.name = new_name
                if new_name != name:
                    num_tags_updated += 1
        ui.messageBox("Touched %d bodies, updated %d of them" % (num_tags_touched, num_tags_updated))
                
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
