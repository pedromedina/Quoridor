from Tkinter import *
from math import floor
import QuoridorGame as QG
import Quoridor_AI_API as ai
from sys import argv
#from QuoridorGame import QuoridorGame

# TODO - print graph

class TkBoard():
    # CONSTANTS
    SQUARE_SIZE = 50
    PLAYER_SIZE = SQUARE_SIZE * 0.8
    SQUARE_SPACING = 10
    MARGIN = 20
    PANEL_WIDTH = 200
    ICON_MARGINS = 55
    BUTTON_WIDTH = 140
    BUTTON_HEIGHT = 50
    BUTTON_MARGIN = 20
    DEFAULT_COLORS = {'bg': '#FFFFFF',
                      'square': '#333333',
                      'wall': '#DD6611',
                      'wall-error': '#CC1111',
                      'panel': '#333333',
                      'button': '#AA5303',
                      'text': '#000000',
                      'players': ['#11CC11', '#CC11CC', '#BB0011', '#00CC00']
                      }
                      
                      
    # CLASS VARIABLES - DRAWING
    tk_root = None
    tk_canv = None
    players = []
    player_ghost = None
    icon = None
    squares = [[0]*9]*9
    grid = None
    canvas_dims = (0,0)
    buttons = [] # will contain bbox and callback as tuple for each button
    walls = {}   # will be dictionary of name => id. all will exist, transparency toggled, colors changed for errors
    active_wall = ""
    active_move = ""
    
    # GAME-INTERACTION VARIABLES
    gs = None
    moveType = "move"
    game_over = False
    
    def set_default_colors(new_colors_dict={}):
        """update default colors with given dictionary of new color scheme
        
        Given colors don't need to be complete - only updates those given"""
        for k in new_colors_dict.keys():
            if k in self.DEFAULT_COLORS.keys():
                self.DEFAULT_COLORS[k] = new_colors_dict[k]
    
    def new_game(self, np=2):
        """Destroy old board, draw new board, update object state with new board
        """
        if self.tk_root:
            self.tk_root.destroy()
            
        self.tk_root = Tk()
        self.tk_root.bind("<Escape>",   lambda e: self.tk_root.destroy())
        self.tk_root.bind("<Motion>",   lambda e: self.handle_mouse_motion(e))
        self.tk_root.bind("<Button-1>", lambda e: self.handle_click(e))
        self.tk_root.bind("<Left>",     lambda e: self.handle_keypress("L"))
        self.tk_root.bind("<Right>",    lambda e: self.handle_keypress("R"))
        self.tk_root.bind("<Up>",       lambda e: self.handle_keypress("U"))
        self.tk_root.bind("<Down>",     lambda e: self.handle_keypress("D"))
        self.tk_root.bind("w",          lambda e: self.set_movetype("wall"))
        self.tk_root.bind("m",          lambda e: self.set_movetype("move"))
        self.tk_root.bind("<space>",    lambda e: self.toggle_movetype())
    
        # margin - space/2 - square - space - square - ... - square - space/2 - margin - panel
        total_height = 9*self.SQUARE_SIZE + 9*self.SQUARE_SPACING + 2*self.MARGIN
        total_width = total_height + self.PANEL_WIDTH
        self.canvas_dims = (total_width, total_height)
    
        self.tk_canv = Canvas(self.tk_root, width=total_width, height=total_height, background=self.DEFAULT_COLORS['bg'])
        self.tk_canv.pack()
        
        self.draw_squares()
        self.generate_walls()
        
        game_state = QG.QuoridorGame(np)
        self.gs = game_state
        self.players = [None]*len(game_state.players)
        self.draw_players()
        self.draw_panel()

        self.tk_root.mainloop()
    
    def refresh(self):
        self.draw_players()
        self.clear_ghost()
        for w in self.walls.keys():
            self.wall_off(w)
        for w in self.gs.walls:
            self.wall_on(w)
        self.draw_current_player_icon()
    
    def draw_current_player_icon(self):
        w, h = self.canvas_dims
        midx = w - self.PANEL_WIDTH/2
        radius = self.PLAYER_SIZE/2
        x0, x1 = midx - radius, midx + radius
        y0, y1 = self.ICON_MARGINS - radius, self.ICON_MARGINS + radius
        c = self.DEFAULT_COLORS['players'][self.gs.current_player_num -1]
        oval = self.tk_canv.create_oval(x0, y0, x1, y1, fill=c, outline="")
        if self.icon:
            self.tk_canv.delete(self.icon)
        self.icon = oval

    def new_rect_button(self, text, fill, x0, y0, x1, y1, callback):
        hover_lighten = TkBoard.alpha_hax(fill, "#FFFFFF", 0.25)
        self.tk_canv.create_rectangle(x0, y0, x1, y1, fill=fill, activefill=hover_lighten, outline="")
        midx = (x0 + x1) / 2
        midy = (y0 + y1) / 2
        self.tk_canv.create_text((midx, midy), text=text, font=("Arial", 14, "bold"))
        self.buttons.append(((x0, y0, x1, y1), callback))
    
    def set_movetype(self, type):
        self.moveType = type
        self.refresh()
    
    def toggle_movetype(self):
        if self.moveType == "wall":
            self.set_movetype("move")
        elif self.moveType == "move":
            self.set_movetype("wall")
        self.refresh()
    
    def draw_panel(self):
        # panel bg
        w, h = self.canvas_dims
        midx = w-self.PANEL_WIDTH/2
        c = self.DEFAULT_COLORS['panel']
        self.tk_canv.create_rectangle(w-self.PANEL_WIDTH, 0, w, h, fill=c)
        # current-player icon @ top
        self.draw_current_player_icon()
        # buttons!
        c = self.DEFAULT_COLORS['button']
        x0, x1 = midx-self.BUTTON_WIDTH/2, midx+self.BUTTON_WIDTH/2
        y0, y1 = 2*self.ICON_MARGINS, 2*self.ICON_MARGINS + self.BUTTON_HEIGHT
        self.new_rect_button("Move", c, x0, y0, x1, y1, lambda: self.set_movetype("move"))
        yshift = self.BUTTON_HEIGHT + self.BUTTON_MARGIN
        y0 += yshift
        y1 += yshift
        self.new_rect_button("Wall", c, x0, y0, x1, y1, lambda: self.set_movetype("wall"))

    def handle_mouse_motion(self, e):
        if self.game_over:
            return
        x = e.x
        y = e.y
        grid = self.point_to_grid((x,y))
        
        if grid and self.moveType == "move":
            move_str = QG.point_to_notation(grid)
            if move_str != self.active_move:
                self.active_move = move_str
                if self.gs.turn_is_valid(move_str, "move"):
                    self.draw_player(grid, self.gs.current_player_num-1, True)
                elif self.player_ghost:
                    self.tk_canv.delete(self.player_ghost)
                    self.player_ghost = None
            
        elif grid and self.moveType == "wall":
            orient, topleft = self.xy_to_wall_spec(grid, x, y)
            pos = QG.point_to_notation(topleft)
            wall_str = orient+pos
            if wall_str != self.active_wall:
                self.wall_off(self.active_wall)
                self.active_wall = wall_str
                if self.gs.turn_is_valid(wall_str, "wall"):
                    self.wall_on(wall_str)
                else:
                    self.wall_on(wall_str, True)
        #self.refresh()
    
    def handle_keypress(self, key):
        (cr, cc) = self.gs.current_player.position
        if key == "L":
            cc -= 1
        elif key == "R":
            cc += 1
        elif key == "U":
            cr -= 1
        elif key == "D":
            cr += 1
        move_str = QG.point_to_notation((cr, cc))
        self.exec_wrapper(move_str)
        self.refresh()
        
            
    def wall_on(self, wall_str, error=False):
        color = self.DEFAULT_COLORS['wall'] if not error else self.DEFAULT_COLORS['wall-error']
        if wall_str in self.walls:
            box_id = self.walls[wall_str]
            self.tk_canv.itemconfigure(box_id, fill=color)
        
    def wall_off(self, wall_str):
        if wall_str in self.walls:
            box_id = self.walls[wall_str]
            self.tk_canv.itemconfigure(box_id, fill="")
    
    def handle_click(self, e):
        if self.game_over:
            return
        x = e.x
        y = e.y
        # check for button press
        for b in self.buttons:
            (x0, y0, x1, y1), callback = b
            if (x0 <= x <= x1) and (y0 <= y <= y1):
                callback()
                return
        # check for turn execution
        grid = self.point_to_grid((x,y))
        success = 0
        if grid and self.moveType == "move":
            move_str = QG.point_to_notation(grid)
            self.exec_wrapper(move_str)
        elif grid and self.moveType == "wall":
            orient, topleft = self.xy_to_wall_spec(grid, x, y)
            pos = QG.point_to_notation(topleft)
            wall_str = orient+pos
            self.exec_wrapper(wall_str)
        self.refresh()

    def exec_wrapper(self, turn_str):
        success = self.gs.execute_turn(turn_str)
        if success == 1:
            self.moveType = "move"
        elif success == 2:
            # winner!
            print "Winner!!"
            print "Player", self.gs.current_player_num
            self.game_over = True

    def draw_squares(self):
        import random
        for r in range(9):
            for c in range(9):
                x = self.MARGIN + self.SQUARE_SPACING/2 + (self.SQUARE_SIZE+self.SQUARE_SPACING)*c
                y = self.MARGIN + self.SQUARE_SPACING/2 + (self.SQUARE_SIZE+self.SQUARE_SPACING)*r
                color = self.DEFAULT_COLORS['square']
                sq = self.tk_canv.create_rectangle(x, y, x+self.SQUARE_SIZE, y+self.SQUARE_SIZE, fill=color, outline="")
                self.squares[r][c] = sq
    
    def generate_walls(self):
        for w in ai.all_walls():
            (x0, y0, x1, y1) = self.wall_str_to_coords(w)
            # regular wall
            r = self.tk_canv.create_rectangle(x0, y0, x1, y1, fill="", outline="")
            self.walls[w] = r
    
    def xy_to_wall_spec(self, grid, x, y):
        cx, cy = self.grid_to_point(grid)
        dx = x-cx
        dy = y-cy
        # wall orientation - I'll explain this when you're older
        r2 = 2**0.5
        rotx = r2*dx - r2*dy
        roty = r2*dx + r2*dy
        if rotx*roty >= 0:
            orient = 'V'
        else:
            orient = 'H'
        # wall position (top-left)
        gr, gc = grid
        if dx < 0:
            gc -= 1
        if dy < 0:
            gr -= 1
        return (orient, (gr, gc))
    
    def wall_str_to_coords(self, wall_str):
        grid_pos = QG.notation_to_point(wall_str[1:])
        orient = wall_str[0]
        cx, cy = self.grid_to_point(grid_pos)
        wall_len = 2*self.SQUARE_SIZE + self.SQUARE_SPACING
        wall_wid = self.SQUARE_SPACING
        halfwidth = self.SQUARE_SIZE/2
        if orient == 'V':
            x0 = cx + halfwidth
            y0 = cy - halfwidth
            x1 = x0 + wall_wid
            y1 = y0 + wall_len
        elif orient == 'H':
            x0 = cx - halfwidth
            y0 = cy + halfwidth
            x1 = x0 + wall_len
            y1 = y0 + wall_wid
        return (x0, y0, x1, y1)
    
    def draw_players(self):
        game_state = self.gs
        # draw new ones
        for i in range(len(game_state.players)):
            p = game_state.players[i]
            self.draw_player(p.get_pos(), i)
    
    def draw_player(self, center, num, ghost=False):
        xy = self.grid_to_point(center)
        if not xy:
            return
        x, y = xy
        # remove old ovals from the board
        if not ghost and self.players[num]:
            self.tk_canv.delete(self.players[num])
        elif ghost and self.player_ghost:
            self.tk_canv.delete(self.player_ghost)
        # draw new
        c = self.DEFAULT_COLORS['players'][num]
        if ghost:
            bg = self.DEFAULT_COLORS['square']
            c = TkBoard.alpha_hax(bg, c, 0.4)
        radius = self.PLAYER_SIZE/2
        oval = self.tk_canv.create_oval(x-radius, y-radius, x+radius, y+radius, fill=c, outline="")
        if not ghost:
            self.players[num] = oval
        else:
            self.player_ghost = oval
    
    def clear_ghost(self):
        if self.player_ghost:
            self.tk_canv.delete(self.player_ghost)
            self.player_ghost = None

    def grid_to_point(self, grid_pt):
        """given (row, col), return centerpoint of that square on the canvas
        
        If not a valid grid point, return None"""
        r, c = grid_pt
        if (1 <= r <= 9) and (1 <= c <= 9):
            x = self.MARGIN + self.SQUARE_SPACING/2 + (self.SQUARE_SIZE+self.SQUARE_SPACING)*(c-1)
            y = self.MARGIN + self.SQUARE_SPACING/2 + (self.SQUARE_SIZE+self.SQUARE_SPACING)*(r-1)
            halfsquare = self.SQUARE_SIZE/2
            return (x+halfsquare, y+halfsquare)
        else:
            return None
        
    def point_to_grid(self, xy):
        """given (x, y), return (row, col) of corresponding grid space.
        
        If off the grid or one row of spacing on outside, returns None"""
        x, y = xy
        x -= self.MARGIN
        y -= self.MARGIN
        full_space = self.SQUARE_SIZE + self.SQUARE_SPACING
        r = int(floor(y / full_space) + 1)
        c = int(floor(x / full_space) + 1)
        if (1 <= r <= 9) and (1 <= c <= 9):
            return (r, c)
        else:
            return None
    
    @staticmethod
    def alpha_hax(back, front, alpha):
        """since tkinter doesnt support alpha channels as far as I can tell,
        this function does 2-color blending on hex strings, returning blended hex string"""
        
        # get numeric values
        b_r = int(back[1:3], 16)
        b_g = int(back[3:5], 16)
        b_b = int(back[5:7], 16)
        
        f_r = int(front[1:3], 16)
        f_g = int(front[3:5], 16)
        f_b = int(front[5:7], 16)
        
        # combine 'em
        new_r = int(b_r * (1-alpha) + f_r * alpha)
        new_g = int(b_g * (1-alpha) + f_g * alpha)
        new_b = int(b_b * (1-alpha) + f_b * alpha)
        
        # get hex versions, take off leading '0x' and pad with "0" when len() < 2
        hex_r = hex(new_r)[2:].rjust(2,"0")
        hex_g = hex(new_g)[2:].rjust(2,"0")
        hex_b = hex(new_b)[2:].rjust(2,"0")
        
        return "#"+hex_r+hex_g+hex_b

    def __init__(self, n):
        self.new_game(n)

if __name__ == "__main__":
    n = 2
    if len(argv) > 1:
        try:
            n = int(argv[1])
        except:
            pass
    tkb = TkBoard(n)