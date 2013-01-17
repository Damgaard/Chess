"""
Terminal Chess Game

Hard Problem 68 on r/dailyprogrammer
"""

import copy
import itertools
import os
import sys
try:
    from termcolor import colored
    has_term_color = True
except ImportError:
    has_term_color = False

from ai import RandomAI, SmartAI

class Piece:
    """Class representing a chess piece"""
    piece_avatar = {"pawn" : "p", "knight" : "n", "bishop" : "b",
                    "rock" : "r", "queen" : "q", "king" : "k"}

    moves = {"pawn" : [[(0, 1), (0, 2), (-1, 1), (1, 1)],
                       [(0, -1), (0, -2), (-1, 1), (1, 1)]],
             "knight" : list(itertools.product([1, -1], [2, -2])) +
                        list(itertools.product([2, -2], [1, -1])),
             "rock" : list(itertools.product(range(-7, 0) + range(1, 8), [0])),
             "bishop" : [(i, i) for i in range(-7, 8) if i != 0] +
                        [(-i , i) for i in range(-7, 8) if i != 0],
             "king" : list(itertools.product([-1, 0, 1], [-1, 0, 1]))}

    def __init__(self, name, from_pos, player, model):
        self.name = name
        self.player = player
        self.x, self.y = from_pos
        self.model = model
        self.update_stats()

    def change_model(self, new_model):
        """
        Change the reference to the model state.

        Useful for AI's and the board test of checkmate.
        """
        self.model = new_model

    def is_legal_move(self, x, y):
        """Test whether the proposed move is legal"""
        # Assume move is within self.model and not current pos.
        potential_moves = [(self.x + tmp_x, self.y + tmp_y) for (tmp_x, tmp_y)
                                                            in self.movement]
        if (x, y) not in potential_moves:
            return False
        final = self.model.get_point(x, y)
        if self.name == 'pawn':
            if x != self.x: # Trying to take a piece
                return final != None and final.player != self.player
            else: # Just trying to move
                middle_point = None
                if abs(self.y - y) == 2:
                    middle_point = self.model.get_point(self.x, self.y +
                                                       self.pawn_move_modifier)
                return final is None and middle_point is None

        intervening = []
        if self.name == 'rock' or self.name == 'queen':
            for ix in range(min(x, self.x), max(x, self.x) + 1):
                intervening = [(ix, iy) for iy in range(min(y, self.y),
                                                        max(y, self.y) + 1)]
        if self.name == "bishop" or self.name == 'queen':
            step_x = 1 if self.x < x else -1
            step_y = 1 if self.y < y else -1
            intervening += [(self.x + i * step_x, self.y + i * step_y)
                                   for i in range(abs(self.x - x) + 1)]

        # Return false if it has to pass over a non-empty point
        intervening = [i for i in intervening
                         if i != (x, y) and i!= (self.x, self.y)]
        if any(self.model.get_point(x, y) != None for x, y in intervening):
            return False

        # Final pos must be vacant or occupied by enemy
        return final == None or final.player != self.player

    def legal_moves(self):
        """
        Return all legal moves for this unit.

        Mainly used by AI's and to test for checkmate.
        """
        potential_moves = [(self.x + tmp_x, self.y + tmp_y) for (tmp_x, tmp_y)
                                                            in self.movement]
        return [(x, y) for x, y in potential_moves if
                    self.model.is_inside(x, y) and self.is_legal_move(x, y)]

    def set_pos(self, x, y):
        """Set position of the piece to x, y."""
        self.x = x
        self.y = y

    def update_stats(self):
        """Set stats after name. Used in initialisation and pawn transform."""
        self.avatar = self.piece_avatar[self.name]
        self.pawn_move_modifier = 1 if self.player == 0 else -1
        if self.name == 'pawn':
            self.movement = self.moves['pawn'][self.player]
        elif self.name == 'queen':
            self.movement = self.moves['rock'] + self.moves['bishop']
        else:
            self.movement = self.moves[self.name]

class Model:
    """Class holding information about the state of the game"""
    def __init__(self):
        self.chess_map = [None] * 64
#        self.setup_queen_map()
        self.setup_standard_map()
#        self.setup_pawn_map()
        self.moves = []

    # Functions used in initialisation
    def _mirror(self, x, y):
        """Take an x an y coordinate, return it mirrored"""
        return (x, 9 - y)

    def _mirror_map(self):
        """Mirror top side to bottom. Flip ownership of other half pieces."""
        for piece in self.get_pieces():
            new_player = 1 if piece.player == 0 else 0
            new_x, new_y = self._mirror(piece.x, piece.y)
            mirror_piece = copy.copy(piece)
            mirror_piece.player = new_player
            mirror_piece.update_stats()
            mirror_piece.set_pos(new_x, new_y)
            self.set_point(mirror_piece, x = new_x, y = new_y)

    def game_not_over(self):
        """Test whether the game has ended."""
        # The game ends when there is less than 2 kings on the model
        return sum(self.chess_map[i] != None and
                   self.chess_map[i].name == "king"
                   for i in range(0, 8*8)) == 2 and not self.is_in_checkmate()

    def get_pieces(self):
        """Return all game pieces."""
        return ([self.chess_map[i] for i in range(0, 8 * 8)
                                   if self.chess_map[i] != None])


    def get_point(self, x = None, y = None, index = None):
        """Return the piece placed on index, or None if there is no piece."""
        if (x is None) != (y is None):
            raise Exception('Both x and y must be given.')
        if (x is None) == (index is None):
            raise Exception('Provide either an x, y coordinate or an index.')
        if x is not None:
            index = (x - 1) * 8 + (y - 1)
        return self.chess_map[index]

    def is_in_check(self, test_for):
        """Is player number 'test_for' in check?"""
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
        """Is the next player in checkmate?"""
        if not len(self.moves):
            return False
        _, _, (to_x, to_y) = self.moves[-1]
        last_mover = self.get_point(to_x, to_y).player
        pieces = self.get_pieces()
        other_pieces = [x for x in pieces if x.player != last_mover]
        checker_pieces = (x for x in pieces if x.player == last_mover)
        other_king = [x for x in pieces if x.name == "king"
                        and x.player != last_mover]
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

    def is_inside(self, x, y):
        """Is the coordinate within the game model?"""
        return x in range(1, 9) and y in range(1, 9)

    def move_unit(self, (from_x, from_y), (to_x, to_y)):
        """Move a unit from (from_x, from_y) to (to_x, to_y)"""
        unit = self.get_point(from_x, from_y)
        self.moves.append((self.get_point(to_x, to_y), (from_x, from_y),
                                                       (to_x, to_y)))
        self.set_point(unit, x = to_x, y = to_y)
        self.set_point(None, x = from_x, y = from_y)
        unit.set_pos(to_x, to_y)

    def pawn_transform(self):
        """Transform pawns that reach the final line to a queen."""
        pawns = (p for p in self.get_pieces() if p.name == 'pawn')
        for pawn in pawns:
            if pawn.y == 1 or pawn.y == 8:
                pawn.name = "queen"
                pawn.update_stats()
                # Assume only one pawn can reach final line pr turn
                return

    def setup_standard_map(self):
        """Create and place pieces for a standard game"""
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

    def set_point(self, thing, x = None, y = None, index = None):
        """Set the index to contain the thing."""
        if (x is None) != (y is None):
            raise Exception('Both x and y must be given.')
        if (x is None) == (index is None):
            raise Exception('Provide either an x, y coordinate or an index.')
        if x is not None:
            index = (x - 1) * 8 + (y - 1)
        self.chess_map[index] = thing

    def setup_pawn_map(self):
        """Create and place pieces for a pawn game"""
        for x in range(1, 9):
            self.set_point(Piece("pawn", (x, 2), 0, self), x = x, y = 2)
        self.set_point(Piece("king", (5, 1), 0, self), x = 5, y = 1)
        self._mirror_map()

    def setup_queen_map(self):
        """A map with one player having 7 queens and the other 1 rock"""
        for x in range(1, 9):
            self.set_point(Piece("queen", (x, 1), 0, self), x =x, y=1)
        self.set_point(Piece("king", (5, 1), 0, self), x=5, y=1)
        self.set_point(Piece("rock", (5, 7), 1, self), x=5, y=7)
        self.set_point(Piece("king", (5, 8), 1, self), x=5, y=8)

    def undo_move(self):
        """Undo the last move. Cannot currently redo moves"""
        unit, (from_x, from_y), (to_x, to_y) = self.moves.pop()
        moved_unit = self.get_point(x = to_x, y = to_y)
        self.set_point(unit, x = to_x, y = to_y)
        self.set_point(moved_unit, x = from_x, y = from_y)
        if unit != None:
            unit.set_pos(to_x, to_y)
        moved_unit.set_pos(from_x, from_y)

class Terminal_view:
    """Handles displaying the game in a terminal."""
    def __init__ (self, model):
        self.model = model
        self.msg = None

    def is_in_check(self):
        """Function called when the player to move is in check"""
        self.msg = "You are in check!"

    def is_in_checkmate(self):
        """Tells a player he's been checkmated."""
        self.msg = "You have been checkmated!"

    def print_loss_screen(self, color):
        """Print loss screen for the player with color 'color'."""
        self.refresh_map()
        self.print_moves()
        print "%s just Lost the Game" % color
        if self.msg != None:
            print self.msg

    def print_moves(self):
        """Print all moves that have been made in chess notation"""
        notation = []
        for index, move in enumerate(self.model.moves):
            if index % 2 == 0:
                notation.append("\n%i. " % (index / 2 + 1))
            else:
                notation.append(", ")
            notation.append(coordinates_to_human_notation(move))
        print "".join(notation)

    def refresh_map(self):
        """Draw the model to terminal"""
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
                        if piece.player == 1:
                            char = char.upper()
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
        """Prints information about whose turn it is to move."""
        print "It's %s's turn to move" % color
        if self.msg != None:
            print self.msg
            self.msg = None


def coordinates_to_human_notation((unit, (from_x, from_y), (to_x, to_y))):
    """Translate coordinates like 21-31 to Kb1-f3"""
    x_names = "abcdefgh"
    uniter = "-" if unit == None else "x"
    return x_names[from_x - 1] + str(from_y) + uniter + \
           x_names[to_x - 1] + str(to_y)

def human_notation_to_coordinates(move):
    """Translate human notation like e5-a2 into coordinates."""
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

def human(my_player):
    """Get move through feedback. Through terminal"""
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

        (from_x, from_y), (to_x, to_y) = translated_move
        if not (model.is_inside(from_x, from_y) or
                model.is_inside(to_x, to_y)):
            print "Move is outside the board!"
            continue
        unit = model.get_point(from_x, from_y)
        if unit == None or unit.player != my_player:
            print "We don't have a piece at the starting position."
        elif not unit.is_legal_move(to_x, to_y):
            print "Not legal move!"
        else:
            return ((from_x, from_y), (to_x, to_y))

def game(players = None):
    """Main loop"""
    if players is None:
        players = [RandomAI(0, model), RandomAI(1, model)]
    colors = ["White", "Black"]
    turn = 0

    while model.game_not_over():
        # Refresh the map
        view.refresh_map()
        # Tell view color of next player
        view.to_move(colors[turn])
        # Get the move
        from_pos, to_pos = players[turn].move()
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
    """Clear screen and find out who is playing."""
    os.system(['clear', 'cls'][ os.name == 'nt' ] )
    players = []
    player_types = [human, RandomAI, SmartAI]
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
            players.append(player_types[number_input - 1](len(players), model))
            print "You've added a player. But chess is a 2-player game, so"
    game(players)

model = Model()
view = Terminal_view(model)

if __name__ == "__main__":
    setup()
