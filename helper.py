from functools import wraps

def _xy_to_index(function):
    '''Wraps a function to feed it a map index rather than xy coordinath'''
    @wraps(function)
    def wrapped(*args, **kwargs):
        if "x" not in kwargs.keys() and len(args) == 3 and not isinstance(args[0], list):
            # 3 not keyword arguments. First is self ( the map )
            index = _xy_convert(args[1], args[2])
            args = [args[0]]
        else:
            # x and y sent as named parameters
            index = _xy_convert(kwargs["x"], kwargs["y"])
            del kwargs["x"]
            del kwargs["y"]
        return function(index = index, *args, **kwargs)
    return wrapped

def _xy_convert(x, y):
    '''Convert to corrosponding index value'''
    return (x - 1) * 8 + (y - 1)
