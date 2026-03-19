


class PersonTracker: 
    def __init__(self):
        self.locked = False # has the user pressed lock
        self.center_x = None # last known x position 
        self.center_y = None # last known y position
        self.velocity_x = 0 # how fast they are moving in x 
        self.velocity_y = 0 # how fast they are moving in y
        self.color = None # saved clothing color sample 
        self.box_w = None # saved box width
        self.box_h = None # saved box height

        
