"""This file holds all the AI's."""

import random

class RandomAI:
    """Finds a random unit, randomly selects one of its random moves"""
    def __init__(self, my_player, model):
        self.my_player = my_player
        self.model = model

    def random_move(self):
        """Return a totally random legal move."""
        my_pieces = (p for p in self.model.get_pieces() if p.player
                                                            == self.my_player)
        all_moves = reduce(lambda x, y: x + y,
                (zip([(p.x, p.y)] * len(p.legal_moves()), p.legal_moves())
                for p in my_pieces))
        return random.choice(all_moves)

    def move(self):
        """Make random move."""
        return self.random_move()

class SmartAI(RandomAI):
    """VERY smart. Can see winning moves!"""
    def move(self):
        """Make a winning move if possible."""
        pieces = self.model.get_pieces()
        enemy_king = [x for x in pieces if x.name == "king" and
                                           x.player != self.my_player ][0]
        my_pieces = (p for p in pieces if p.player == self.my_player)
        # Can i take the enemy king?
        for piece in my_pieces:
            if piece.is_legal_move(enemy_king.x, enemy_king.y):
                return ((piece.x, piece.y), (enemy_king.x, enemy_king.y))
        # Failed to find winning move. Lets make a random one
        return self.random_move()
