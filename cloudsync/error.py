class Error (Exception):
    def __str__(self):
        return ' '.join(map(str, self.args))
