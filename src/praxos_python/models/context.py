from typing import Dict, Any

class Context:
    """A context object."""
    def __init__(self, score: float, data: Dict[str, Any], sentence: str):
        self.score = score
        self.data = data
        self.sentence = sentence

    def __repr__(self) -> str:
        return f"<Context score={self.score} data={self.data} sentence={self.sentence}>"



