import os
import sys
from sqlalchemy import create_engine, MetaData, Table, select, insert, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend to path for local imports if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

SQLITE_URL = "sqlite:///data/scouting.db"
POSTGRES_URL = os.environ.get('DATABASE_URL')

if not POSTGRES_URL:
    print("Error: DATABASE_URL not found in .env")
    sys.exit(1)

# Ensure postgresql:// prefix
if POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql://", 1)

def migrate():
    print(f"🚀 Starting migration from {SQLITE_URL} to PostgreSQL...")
    
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(POSTGRES_URL)
    
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)
    
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)
    
    # Table order to respect foreign keys
    tables_to_migrate = [
        'team',
        'event',
        'event_team',
        'user',
        'pit_scout_data',
        'match_scout_data',
        'scout_assignment'
    ]
    
    with pg_engine.begin() as pg_conn:
        # 1. Clean up existing data (Optional but safer for a fresh migration)
        print("🧹 Cleaning up existing data in PostgreSQL...")
        for table_name in reversed(tables_to_migrate):
            if table_name in pg_meta.tables:
                pg_conn.execute(text(f'DELETE FROM "{table_name}"'))
        
        # 2. Copy data
        for table_name in tables_to_migrate:
            if table_name not in sqlite_meta.tables:
                print(f"⚠️ Table {table_name} not found in SQLite, skipping.")
                continue
            
            print(f"📦 Migrating table: {table_name}...")
            sqlite_table = sqlite_meta.tables[table_name]
            pg_table = pg_meta.tables[table_name]
            
            # Fetch all data from SQLite
            sqlite_conn = sqlite_engine.connect()
            rows = sqlite_conn.execute(select(sqlite_table)).fetchall()
            sqlite_conn.close()
            
            if not rows:
                print(f"  (Table {table_name} is empty)")
                continue
            
            # Prepare data for insertion
            data = [dict(row._mapping) for row in rows]
            
            # Insert into Postgres
            pg_conn.execute(insert(pg_table), data)
            print(f"  ✅ Migrated {len(rows)} rows.")
            
        # 3. Reset Postgres Sequences (Crucial for SERIAL columns)
        print("🔄 Resetting PostgreSQL sequences...")
        sequence_tables = ['team', 'event', 'user', 'pit_scout_data', 'match_scout_data', 'scout_assignment']
        for table_name in sequence_tables:
            if table_name in pg_meta.tables:
                # Get the max ID
                result = pg_conn.execute(text(f'SELECT MAX(id) FROM "{table_name}"'))
                max_id = result.scalar()
                if max_id:
                    pg_conn.execute(text(f"SELECT setval(pg_get_serial_sequence('\"{table_name}\"', 'id'), {max_id})"))
                    print(f"  ✅ Sequence reset for {table_name} to {max_id}.")

    print("\n🎉 Migration completed successfully!")
    print("Check your website at https://frc-scouting-app.nayl.ca/ !")

if __name__ == "__main__":
    migrate()
