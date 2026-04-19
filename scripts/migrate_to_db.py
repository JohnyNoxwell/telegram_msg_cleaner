import os
import sys
import json
from tqdm import tqdm
from dataclasses import fields
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from tg_msg_manager.exporter import MessageData
from tg_msg_manager.storage import SQLiteStorage

def migrate_jsonl_to_db(data_dir: str, db_path: str):
    storage = SQLiteStorage(db_path)
    
    # Get valid fields from MessageData dataclass
    valid_fields = {f.name for f in fields(MessageData)}
    
    # Find all .jsonl files
    files = [f for f in os.listdir(data_dir) if f.endswith(".jsonl")]
    
    if not files:
        print(f"No .jsonl files found in {data_dir}")
        return

    print(f"Found {len(files)} files to migrate.")
    
    total_migrated = 0
    for filename in files:
        file_path = os.path.join(data_dir, filename)
        print(f"Migrating: {filename}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
            for line in tqdm(lines, desc=f"   {filename[:30]}...", leave=False):
                try:
                    data = json.loads(line)
                    
                    # 1. Handle schema variations
                    # Map old 'reply_to' object to 'original_msg'
                    if "reply_to" in data and "original_msg" not in data:
                        data["original_msg"] = data.pop("reply_to")
                    
                    # 2. Robust date parsing
                    for date_field in ["date", "edit_date"]:
                        if data.get(date_field) and isinstance(data[date_field], str):
                            try:
                                data[date_field] = datetime.fromisoformat(data[date_field])
                            except ValueError:
                                data[date_field] = None
                                
                    # 3. Filter fields to match MessageData dataclass
                    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                    
                    # Ensure mandatory fields have defaults if missing (though they shouldn't be)
                    if "date" not in filtered_data:
                        filtered_data["date"] = datetime.now()
                    
                    # Create MessageData instance
                    m = MessageData(**filtered_data)
                    
                    # Save to DB
                    storage.save_message(m)
                    total_migrated += 1
                except Exception as e:
                    # Print more context for debugging
                    print(f"\n   ⚠️ Error in {filename}: {e}")
                    # print(f"   Line: {line[:100]}...")
                    
    print(f"\n✅ Migration complete!")
    print(f"📊 Total messages processed: {total_migrated}")
    print(f"🗄️ Database: {db_path}")

if __name__ == "__main__":
    DATA_DIR = "PUBLIC_GROUPS"
    DB_PATH = "messages.db"
    migrate_jsonl_to_db(DATA_DIR, DB_PATH)
