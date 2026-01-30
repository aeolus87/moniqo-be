"""
Shared Models

Base classes for domain models with automatic ObjectId handling.
Uses Pydantic v2's core schema system for seamless ObjectId serialization.
"""

from decimal import Decimal
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, ConfigDict
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    """
    Custom ObjectId type for Pydantic v2.
    
    Automatically handles ObjectId ↔ string conversion in serialization/deserialization.
    No manual conversion needed in models.
    """
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any
    ) -> core_schema.CoreSchema:
        """
        Generate Pydantic core schema for ObjectId.
        
        Handles:
        - String input → ObjectId (validation)
        - ObjectId input → ObjectId (pass through)
        - ObjectId output → String (serialization)
        """
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(
                        lambda x: ObjectId(x) if isinstance(x, str) else x
                    ),
                ]),
            ]),
            serialization=core_schema.plain_serializer_function_lambda_instance(str),
        )


class DomainModel(BaseModel):
    """
    Base domain model for all domain entities.
    
    Provides:
    - Automatic ObjectId handling via PyObjectId
    - Proper Pydantic v2 configuration
    - JSON encoders for ObjectId and Decimal
    """
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        json_encoders={
            ObjectId: str,
            Decimal: str,
        },
        # Use enum values in JSON
        use_enum_values=True,
    )
