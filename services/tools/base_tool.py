from abc import ABC, abstractmethod

class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs):
        """Execute the tool and return the result."""
        pass