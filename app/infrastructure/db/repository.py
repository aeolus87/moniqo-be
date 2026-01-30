"""
Base Repository

Abstract base class for repository pattern implementation.
Provides common CRUD operations using DatabaseProvider for automatic routing.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import db_provider


class BaseRepository(ABC):
    """
    Abstract base repository class.
    
    Provides common CRUD operations that all repositories must implement.
    Automatically uses DatabaseProvider to route to correct database (real/demo).
    """
    
    def __init__(self, collection_name: str):
        """
        Initialize repository.
        
        Args:
            collection_name: Name of the collection
        """
        self.collection_name = collection_name
    
    def _get_collection(self):
        """
        Get collection for current trading mode.
        
        Automatically routes to correct database based on contextvars.
        
        Returns:
            Motor collection instance
        """
        db = db_provider.get_db()
        return db[self.collection_name]
    
    async def find_one(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single document.
        
        Args:
            filter: MongoDB filter dictionary
            projection: Optional projection dictionary
            
        Returns:
            Document dict or None if not found
        """
        collection = self._get_collection()
        return await collection.find_one(filter, projection)
    
    async def find(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 0,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents.
        
        Args:
            filter: MongoDB filter dictionary
            projection: Optional projection dictionary
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting
            
        Returns:
            List of document dicts
        """
        collection = self._get_collection()
        cursor = collection.find(filter, projection)
        
        if sort:
            cursor = cursor.sort(sort)
        
        if skip > 0:
            cursor = cursor.skip(skip)
        
        if limit > 0:
            cursor = cursor.limit(limit)
        
        return await cursor.to_list(length=limit if limit > 0 else None)
    
    async def count_documents(self, filter: Dict[str, Any]) -> int:
        """
        Count documents matching filter.
        
        Args:
            filter: MongoDB filter dictionary
            
        Returns:
            Number of matching documents
        """
        collection = self._get_collection()
        return await collection.count_documents(filter)
    
    async def insert_one(self, document: Dict[str, Any]) -> ObjectId:
        """
        Insert a single document.
        
        Args:
            document: Document dictionary to insert
            
        Returns:
            Inserted document ID
        """
        collection = self._get_collection()
        result = await collection.insert_one(document)
        return result.inserted_id
    
    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[ObjectId]:
        """
        Insert multiple documents.
        
        Args:
            documents: List of document dictionaries to insert
            
        Returns:
            List of inserted document IDs
        """
        collection = self._get_collection()
        result = await collection.insert_many(documents)
        return list(result.inserted_ids)
    
    async def update_one(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """
        Update a single document.
        
        Args:
            filter: MongoDB filter dictionary
            update: MongoDB update dictionary
            upsert: If True, create document if it doesn't exist
            
        Returns:
            True if document was updated/created
        """
        collection = self._get_collection()
        result = await collection.update_one(filter, update, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)
    
    async def update_many(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any]
    ) -> int:
        """
        Update multiple documents.
        
        Args:
            filter: MongoDB filter dictionary
            update: MongoDB update dictionary
            
        Returns:
            Number of documents updated
        """
        collection = self._get_collection()
        result = await collection.update_many(filter, update)
        return result.modified_count
    
    async def delete_one(self, filter: Dict[str, Any]) -> bool:
        """
        Delete a single document.
        
        Args:
            filter: MongoDB filter dictionary
            
        Returns:
            True if document was deleted
        """
        collection = self._get_collection()
        result = await collection.delete_one(filter)
        return result.deleted_count > 0
    
    async def delete_many(self, filter: Dict[str, Any]) -> int:
        """
        Delete multiple documents.
        
        Args:
            filter: MongoDB filter dictionary
            
        Returns:
            Number of documents deleted
        """
        collection = self._get_collection()
        result = await collection.delete_many(filter)
        return result.deleted_count
    
    async def find_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Find document by ID.
        
        Args:
            document_id: Document ID string
            
        Returns:
            Document dict or None if not found
        """
        try:
            return await self.find_one({"_id": ObjectId(document_id)})
        except Exception:
            return None
