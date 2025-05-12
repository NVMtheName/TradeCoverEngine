"""
Add AI settings columns to the settings table.

This script adds the following columns to the settings table:
- openai_api_key: OpenAI API key for AI features
- enable_ai_advisor: Whether AI advisor is enabled
- ai_model_selection: How to select models (auto, ensemble, cost_effective, premium)
"""

import os
import logging
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add OpenAI API settings columns"""
    try:
        # Get database URL from environment
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        # Create database engine
        engine = create_engine(db_url)
        
        # Check if the columns already exist to avoid errors
        with engine.connect() as conn:
            # Check if openai_api_key column exists
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'settings' AND column_name = 'openai_api_key'"
            ))
            if result.fetchone():
                logger.info("Column 'openai_api_key' already exists")
            else:
                # Add the column
                conn.execute(text("ALTER TABLE settings ADD COLUMN openai_api_key VARCHAR(255)"))
                logger.info("Added column 'openai_api_key'")
            
            # Check if enable_ai_advisor column exists
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'settings' AND column_name = 'enable_ai_advisor'"
            ))
            if result.fetchone():
                logger.info("Column 'enable_ai_advisor' already exists")
            else:
                # Add the column with default value
                conn.execute(text("ALTER TABLE settings ADD COLUMN enable_ai_advisor BOOLEAN DEFAULT TRUE"))
                logger.info("Added column 'enable_ai_advisor'")
            
            # Check if ai_model_selection column exists
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'settings' AND column_name = 'ai_model_selection'"
            ))
            if result.fetchone():
                logger.info("Column 'ai_model_selection' already exists")
            else:
                # Add the column with default value
                conn.execute(text("ALTER TABLE settings ADD COLUMN ai_model_selection VARCHAR(50) DEFAULT 'auto'"))
                logger.info("Added column 'ai_model_selection'")
            
            conn.commit()
        
        logger.info("Migration completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration()