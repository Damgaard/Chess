'''Terminal Chess simulator

   Hard Problem 68 on r/dailyprogrammer
'''

import copy
import os
import sys
import random
try:
    from termcolor import colored
    has_term_color = True
except ImportError:
    has_term_color = False

from helper import _xy_to_index, _xy_convert

class Piece:
    '''Class representing a chess piece'''
    piece_avatar = {"pawn" : "p",
                    "knight" : "k",
                     "bishop" : "b",
                     "rock" : "r",
                     "queen" : "Q",
                     "king" : "K"}

    def __init__(self, name, from_pos, player, model):
        self.name = name
        self.player = player
        self.x, self.y = from_pos
        self.model = model
        self.update_stats()

    def _rotate(self, moves):
        '''Takes a quater of all moves, returns full moves

           It does this by rotating the moves in each of the other three
           directions'''
        result = moves
        result += map(lambda (x, y): (x * -1, y * -1), moves)
        result += map(lambda (x, y): (y * -1, x), moves)
        # Remove any duplicates
        return list(set(result + map(lambda (x, y): (y, x * -1), moves)))

    def change_model(self, new_model):
        '''Change the reference to the model state.

           Usuful for AI's and the board test of checkmate'''
        self.model = new_model

    def set_pos(self, x, y):
        self.x = x
        self.y = y

    def update_stats(self):
        '''Set stats after name. Used in initialisation and pawn transform'''
        self.avatar = self.piece_avatar[self.name]
        if self.name == 'pawn':
           self.pawn_move_modifier = -1
           if self.player == 0:
               self.pawn_move_modifier = 1
           self.movement = [(0, self.pawn_move_modifier),
                            (0, 2 * self.pawn_move_modifier),
                            (-1, self.pawn_move_modifier), 
                            (1, self.pawn_move_modifier)]
        elif self.name == 'bishop':
            self.movement = self._rotate(zip(range(1, 9), range(1, 9)))
        elif self.name == "knight":
            self.movement = self._rotate([(2, 1), (1, 2)])
        elif self.name == 'rock':
            self.movement = self._rotate(zip([0] * 8, range(1, 9)))
        elif self.name == 'queen':
            fake_rock = Piece("rock", (self.x, self.y), self.player, self.model)
            fake_bishop = Piece("bishop", (self.x, self.y), self.player, self.model)
            self.movement = fake_rock.movement + fake_bishop.movement
        elif self.name == 'king':
            self.movement = self._rotate([(1, 1), (1, 0)])

    def legal_moves(self):
        '''Return all legal moves for this unit.

           Mainly used by AI's and to test for checkmate'''
        moveable_positions = map(lambda (x, y): (x + self.x, y + self.y),
                                 self.movement)
        return [(x, y) for x, y in moveable_positions if
                    self.model.is_inside(x, y) and self.is_legal_move(x, y)]

    def is_legal_move(self, x, y):
        '''Test whether the proposed move is legal'''
        # Assume move is within self.model and not current pos
        # Test whether we could theoretically get there with normal moves
        # Then test if all the intervening space is free
        # Finally test if destination is free or enemy
        intervening = []
        if self.name == "king":
            if abs(x - self.x) > 1 or abs(y - self.y) > 1:
                return False
        elif self.name == "queen":
            fake_rock = Piece("rock", (self.x, self.y), self.player, self.model)
            fake_bishop = Piece("bishop", (self.x, self.y), self.player, self.model)
            return (fake_rock.is_legal_move(x, y) or fake_bishop.is_legal_move(x, y))
        elif self.name == "rock":
            if x != self.x and y != self.y:
                return False
            for ix in range(min(x, self.x), max(x, self.x) + 1):
                intervening += [(ix, iy) for iy in range(min(y, self.y),
                                                         max(y, self.y) + 1)]
            # Destination is treated different
            intervening.remove((x, y))
            intervening.remove((self.x, self.y))
        elif self.name == "bishop":
            if abs(x - self.x) != abs(y - self.y):
                return False
            step_x = 1 if self.x < x else -1
            step_y = 1 if self.y < y else -1
            intervening = [(self.x + i * step_x, self.y + i * step_y) 
                                   for i in range(abs(self.x - x) + 1)]
            # Destination is treated different
            intervening.remove((x, y))
            intervening.remove((self.x, self.y))
        elif self.name == "knight":
            if not ((abs(self.x - x) == 2 and abs(self.y - y) == 1) or
                    (abs(self.x - x) == 1 and abs(self.y - y) == 2)):
                return False
        elif self.name == "pawn":
            # Move 1 up
            if x == self.x and y == self.y + 1 * self.pawn_move_modifier:
                return self.model.get_point(x, y) == None
            # Move 2 up
            elif (x == self.x and (self.y == 2 or self.y == 7)
                              and y == self.y + 2 * self.pawn_move_modifier):
                return (self.model.get_point(x = x, 
                            y = self.y + 1 * self.pawn_move_modifier) == None 
                        and self.model.get_point(x=x, y=y) == None)
            # Move 1 up and 1 sideways. Eg try to take enemy piece
            elif abs(x - self.x) == 1 and y == self.y + 1 * self.pawn_move_modifier:
                piece = self.model.get_point(x, y)
                return piece != None and piece.player != self.player
            # Any other move
            return False

        # Return false if it has to pass over a non-empty point
        if any(self.model.get_point(x, y) != None for x, y in intervening):
            return False

        # Return False if the final position is occupied by friendly unit
        # Else return true
        final = self.model.get_point(x, y)
        return final == None or final.player != self.player

class Model:
    '''Class holding information about the state of the game'''
    def __init__(self):
        self.chess_map = [None] * 64
#        self.setup_queen_map()
        self.setup_standard_map()
        self.moves = []

    # Functions used in initialisation
    def _mirror(self, x, y):
        '''Take an x an y coordinate, return it mirrored'''
        return (x, 9 - y)

    def _mirror_map(self):
        '''Mirror all existing pieces to the other side of the map. Swap owner'''
        for piece in self.get_pieces():
            new_player = 1 if piece.player == 0 else 0
            new_x, new_y = self._mirror(piece.x, piece.y)
            mirror_piece = copy.copy(piece)
            mirror_piece.player = new_player
            mirror_piece.update_stats()
            mirror_piece.set_pos(new_x, new_y)
            self.set_point(mirror_piece, x = new_x, y = new_y)

    def setup_standard_map(self):
        '''Create and place pieces for a standard game'''
        # Officers
        y = 1
        for x in (1, 8):
            self.set_point(Piece("rock", (x, y), 0, self), x=x, y=y)
        for x in (3, 6):
            self.set_point(Piece("bishop", (x, y), 0, self), x=x, y=y)
        for x in (2, 7):
            self.set_point(Piece("knight", (x, y), 0, self), x=x, y=y)
        self.set_point(Piece("queen", (4, y), 0, self), x=4, y=y)
        self.set_point(Piece("king", (5, y), 0, self), x=5, y=y)

        # Pawns
        for x in range(1, 9):
            self.set_point(Piece("pawn", (x, 2), 0, self), x=x, y=2)

        # Black pieces
        self._mirror_map()

    def setup_pawn_map(self):
        '''Create and place pieces for a pawn game'''
        for x in range(1, 9):
            self.set_point(Piece("pawn", (x, 2), 0, self), x = x, y = y)
        self.set_point(Piece("king", (5, 1), 0, self), x = 5, y = 1)
        self._mirror_map()

    def setup_queen_map(self):
        '''A map with one player having 7 queens and the other 1 rock'''
        for x in range(1, 9):
            self.set_point(Piece("queen", (x, 1), 0, self), x =x, y=1)
        self.set_point(Piece("king", (5, 1), 0, self), x=5, y=1)
        self.set_point(Piece("rock", (5, 7), 1, self), x=5, y=7)
        self.set_point(Piece("king", (5, 8), 1, self), x=5, y=8)

    # Often used functions in execution
    @_xy_to_index
    def get_point(self, index):
        return self.chess_map[index]

    @_xy_to_index
    def set_point(self, thing, index):
        self.chess_map[index] = thing

    def get_pieces(self):
        '''Return all game pieces'''
        return ([self.chess_map[i] for i in range(0, 8 * 8) 
                                   if self.chess_map[i] != None])

    def pawn_transform(self):
        '''Transform pawns that reach the final line to a queen.'''
        pawns = (p for p in self.get_pieces() if p.name == 'pawn')
        for pawn in pawns:
           if pawn.y == 1 or pawn.y == 8:
                pawn.name = "queen"
                pawn.update_stats()
                # Assume only one pawn can reach final line pr turn
                return

    def move_unit(self, (from_x, from_y), (to_x, to_y)):
        '''Move a unit from (from_x, from_y) to (to_x, to_y)'''
        unit = self.get_point(from_x, from_y)
        self.moves.append((self.get_point(to_x, to_y), (from_x, from_y), 
                                                       (to_x, to_y)))
        self.set_point(unit, x = to_x, y = to_y)
        self.set_point(None, x = from_x, y = from_y)
        unit.set_pos(to_x, to_y)

    def undo_move(self):
        '''Undo the last move. Cannot currently redo moves'''
        unit, (from_x, from_y), (to_x, to_y) = self.moves.pop()
        moved_unit = self.get_point(x = to_x, y = to_y)
        self.set_point(unit, x = to_x, y = to_y)
        self.set_point(moved_unit, x = from_x, y = from_y)
        if unit != None:
            unit.set_pos(to_x, to_y)
        moved_unit.set_pos(from_x, from_y)

    # Test if model state during execution
    def game_not_over(self):
        '''Test whether the game has ended'''
        # The game ends when there is less than 2 kings on the model
        return sum(self.chess_map[i] != None and 
                   self.chess_map[i].name == "king" 
                   for i in range(0, 8*8)) == 2 and not self.is_in_checkmate()

    def is_inside(self, x, y):
        '''Is the coordinate within the game model?'''
        return x in range(1, 9) and y in range(1, 9)

    def is_in_check(self, test_for):
        pieces = self.get_pieces()
        checker_pieces = (x for x in pieces if x.player == test_for)
        other_king = [x for x in pieces if x.name == "king"
                                        and x.player != test_for]
        if not len(other_king):
            # No enemy king, it has been taken
            return False
        other_king = other_king[0]
        return any(piece.is_legal_move(other_king.x, other_king.y) \
                                       for piece in checker_pieces)

    def is_in_checkmate(self):
        if not len(self.moves):
            return False
        _, _, to_pos = self.moves[-1]
        last_mover = self.get_point(*to_pos).player
        pieces = self.get_pieces()
        other_pieces = [x for x in pieces if x.player != last_mover]
        checker_pieces = (x for x in pieces if x.player == last_mover)
        other_king = [x for x in pieces if x.name == "king" and x.player != last_mover]
        if not len(other_king):
            return False
        else:
            other_king = other_king[0]
        is_in_checkmate = False
        for piece in checker_pieces:
            if piece.is_legal_move(other_king.x, other_king.y):
                is_in_checkmate = True
                for piece2 in other_pieces:
                    for move in piece2.legal_moves():
                        self.move_unit((piece2.x, piece2.y), move)
                        if not self.is_in_check(last_mover):
                            # Found a move that prevent piece from taking
                            # king in next move. Eg its a check not checkmate
                            is_in_checkmate = False
                            self.undo_move()
                            break
                        self.undo_move()
                    else:
                        continue
                    break
        return is_in_checkmate

class Terminal_view:
    def __init__ (self, model):
        self.model = model
        self.msg = None

    def refresh_map(self):
        '''Draw the model to terminal'''
        os.system( [ 'clear', 'cls' ][ os.name == 'nt' ] )
        player_colors = ["white", "blue"]
        bg_colors = ["on_yellow", "on_green"]
        for y in range(1, 9)[::-1]:
            line = [str(y), " "]
            for x in range(1, 9):
                piece = self.model.get_point(x, y)
                if piece != None:
                    char = piece.avatar
                    if has_term_color:
                        char = (colored(char, 
                                    player_colors[piece.player],
                                    bg_colors[(x + y) % 2]))
                else:
                    char = " "
                    if has_term_color:
                        char = (colored(char, None, 
                                bg_colors[(x + y) % 2]))
                line.append(char)
            print "".join(line)
        print 
        print "  abcdefgh"
        print

    def to_move(self, color):
        print "It's %s's turn to move" % color
        if self.msg != None:
            print self.msg
            self.msg = None

    def print_moves(self):
        '''Print all moves that have been made in chess notation'''
        notation = []
        for index, move in enumerate(self.model.moves):
            if index % 2 == 0:
                notation.append("\n%i. " % (index / 2 + 1))
            else:
                notation.append(", ")
            notation.append(coordinates_to_human_notation(move))
        print "".join(notation)

    def is_in_check(self):
        '''Function called when the player to move is in check'''
        self.msg = "You are in check!"

    def is_in_checkmate(self):
        self.msg = "You have been checkmated!"

    def print_loss_screen(self, color):
        self.refresh_map()
        self.print_moves()
        print "%s just Lost the Game" % color
        if self.msg != None:
            print self.msg

def coordinates_to_human_notation((unit, (from_x, from_y), (to_x, to_y))):
    '''Translate coordinates like 21-31 to Kb1-f3'''
    x_names = "abcdefgh"
    uniter = "-" if unit == None else "x"
    return x_names[from_x - 1] + str(from_y) + uniter + \
           x_names[to_x - 1] + str(to_y)

def human_notation_to_coordinates(move):
    '''Translate human notation like e5-a2 into coordinates.'''
    # This can have surprisingly many forms of bad input
    if len(move) != 5 or move.count("-") != 1:
        return False
    from_pos, to_pos = move.split("-")
    if len(from_pos) != len(to_pos):
        return False
    x_names = "abcdefgh"
    y_names = "12345678"
    from_x, from_y = from_pos
    to_x, to_y = to_pos
    if (from_x not in x_names or to_x not in x_names or
        from_y not in y_names or to_y not in y_names):
        return False
    return ((x_names.index(from_x) + 1, int(from_y)), 
            (x_names.index(to_x) + 1, int(to_y)))

# I think the smartest thing would be to have the AI or even players
# as classes and extend them with functionality. Such that the smart AI
# would build on the random AI and easily make a random move.
# This would remove the need to repeatedly get all the pieces from model

def human(my_player):
    '''Get move through feedback. Through terminal'''
    while True:
        move = raw_input("Whats your move?").lower()
        if move == "q":
            sys.exit(0)
        translated_move = human_notation_to_coordinates(move)
        if not translated_move:
            bad_format = "Incorrect formatting.\n"
            bad_format += "Position must be in format [a-h][1-8]-[a-h][1-8]\n"
            bad_format +=  "Such as e2-e4 or a1-h8.\n"
            print bad_format +  "Write Q to quit"
            continue

        from_pos, to_pos = translated_move
        if not (model.is_inside(*from_pos) or
                model.is_inside(*to_pos)):
            print "Move is outside the board!"
            continue
        unit = model.get_point(*from_pos)
        if unit == None or unit.player != my_player:
            print "There isn't a unit at the starting position that belongs to us"
        elif not unit.is_legal_move(*to_pos):
            print "Not legal move!"
        else:
            return (from_pos, to_pos)

def random_ai(my_player):
    '''Finds a random unit, randomly selects one of its random moves'''
    my_pieces = (p for p in model.get_pieces() if p.player == my_player)
    all_moves = reduce(lambda x, y: x + y, 
            (zip([(p.x, p.y)] * len(p.legal_moves()), p.legal_moves()) 
            for p in my_pieces))
    return random.choice(all_moves)

def smart_ai(my_player):
    '''VERY smart. Can see winning moves!'''
    pieces = model.get_pieces()
    enemy_king = [x for x in pieces if x.name == "king" and 
                                       x.player != my_player ][0]
    my_pieces = (p for p in pieces if p.player == my_player)
    # Can i take the enemy king?
    for piece in my_pieces:
        if piece.is_legal_move(enemy_king.x, enemy_king.y):
            return ((piece.x, piece.y), (enemy_king.x, enemy_king.y))
    # Failed to find winning move. Lets make a random one
    return random_ai(my_player)

def game(players = [random_ai, random_ai]):
    '''Main loop'''
    colors = ["White", "Black"]
    turn = 0

    while model.game_not_over():
        # Refresh the map
        view.refresh_map()
        # Tell view color of next player
        view.to_move(colors[turn])
        # Get the move
        from_pos, to_pos = players[turn](turn)
        # Move the unit in the model
        model.move_unit(from_pos, to_pos)
        # Test if any pawn has reached the final line and may be transformed
        model.pawn_transform()
        # See if there is a
        if model.is_in_checkmate():
            view.is_in_checkmate()
        elif model.is_in_check(turn):
            view.is_in_check()
        # Update turn and do it again
        turn = 0 if turn == 1 else 1

    view.print_loss_screen(colors[turn])

def setup():
    os.system( [ 'clear', 'cls' ][ os.name == 'nt' ] )
    players = []
    player_types = [human, random_ai, smart_ai]
    print "Welcome to terminal chess!"
    print "In game use notation like e2-e4 to move pieces"
    if not has_term_color:
        print "ERROR: You do not have the module termcolor installed."
        print "The pieces will not be colored."
    while len(players) < 2:
        print "Add a player to the game"
        print "0. Quit"
        print "1. Human"
        print "2. Random AI"
        print "3. Smart AI"
        raw_in = raw_input("I choose: ")
        if len(raw_in) != 1 or not raw_in.isdigit():
            print "Bad input"
            continue
        number_input = int(raw_in)
        if number_input not in range(0, 4):
            print "No such player"
        elif number_input == 0:
            print ":("
            sys.exit(0)
        else:
            players.append(player_types[number_input - 1])
            print "You've added a player. But chess is a 2-player game, so"
    game(players)

model = Model()
view = Terminal_view(model)

if __name__ == "__main__":
    setup()
