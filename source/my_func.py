def add(a, b):
    return a + b


class Calculator:
    def __init__(self):
        self.store = 0.0

    def integrate(self, in_value):
        self.store += in_value
        return self.store

    def reset(self):
        self.store = 0.0
