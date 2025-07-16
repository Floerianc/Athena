class GPTMemory:
    def __init__(self) -> None:
        self.history = []
        self.max_entries = 10