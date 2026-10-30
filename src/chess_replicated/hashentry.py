class EntryType:
    EXACT = 0
    LOWER_BOUND = 1
    UPPER_BOUND = 2

class HashEntry:
    def __init__(self, score, depth, entry_type):
        self.score = score
        self.depth = depth
        self.type = entry_type
    def getScore(self):
        return self.score
    def getType(self):
        return self.type
    def getDepth(self):
        return self.depth