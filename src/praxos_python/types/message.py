from datetime import datetime
from pydantic import BaseModel, Field
import typing

class Message(BaseModel):
    content: str = Field(
        description="The content of the message",
        min_length=1
    )
    
    role: typing.Optional[str] = Field(
        description="The role of the message sender (e.g., 'user', 'assistant', 'system')",
    )
    
    timestamp: datetime = Field(
        description="The timestamp when the message was created",
        default_factory=datetime.now
    )

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """
        Create a Message instance from a dictionary.
        
        Args:
            data (dict): Dictionary containing message data with keys:
                - content (str): The message content
                - role (str, optional): The role of the message sender
                - timestamp (str, optional): ISO format timestamp string
                
        Returns:
            Message: A new Message instance
        """
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
    