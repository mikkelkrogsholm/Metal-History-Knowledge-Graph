"""
Database service for Kuzu connection management
"""

import kuzu
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Manages Kuzu database connections and queries"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db: Optional[kuzu.Database] = None
        self.conn: Optional[kuzu.Connection] = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found at {self.db_path}")
            
            self.db = kuzu.Database(str(self.db_path))
            self.conn = kuzu.Connection(self.db)
            logger.info(f"Connected to database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.conn is not None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn = None
        if self.db:
            self.db = None
        logger.info("Database connection closed")
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as list of dicts"""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        try:
            if parameters:
                result = self.conn.execute(query, parameters)
            else:
                result = self.conn.execute(query)
            
            # Convert to list of dicts
            df = result.get_as_df()
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_node_count(self, node_type: str) -> int:
        """Get count of nodes by type"""
        query = f"MATCH (n:{node_type}) RETURN COUNT(n) as count"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        query = "CALL SHOW_TABLES() RETURN *"
        tables = self.execute_query(query)
        
        node_tables = [t for t in tables if t['type'] == 'NODE']
        rel_tables = [t for t in tables if t['type'] == 'REL']
        
        return {
            "node_tables": [t['name'] for t in node_tables],
            "relationship_tables": [t['name'] for t in rel_tables],
            "total_nodes": len(node_tables),
            "total_relationships": len(rel_tables)
        }