import sqlite3
import json

DATABASE = 'templates.db'

def show_users():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    
    print("Users in the database:")
    print("-" * 60)
    for user in users:
        print(f"ID: {user[0]} | Username: {user[1]} | Email: {user[2]} | Created: {user[3]}")
    print("-" * 60)
    print()
    
    conn.close()

def show_tables():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("Present tables in the database:")
    print("-" * 40)
    for table in tables:
        print(f"• {table[0]}")
    print("-" * 40)
    print()
    
    conn.close()

def query_all_templates():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, category, description FROM templates ORDER BY category, name')
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} templates:")
    print("-" * 80)
    
    for row in rows:
        print(f"ID: {row['id']} | {row['name']} | {row['category']}")
        print(f"   {row['description']}")
        print("-" * 80)
    
    conn.close()

def query_template_by_id(template_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM templates WHERE id = ?', (template_id,))
    row = cursor.fetchone()
    
    if row is None:
        print(f"No template found with ID {template_id}")
        conn.close()
        return
    
    print(f"Template Details (ID: {template_id}):")
    print("=" * 80)
    print(f"Name: {row['name']}")
    print(f"Description: {row['description']}")
    print(f"Category: {row['category']}")
    print(f"Icon: {row['icon']}")
    print(f"Color: {row['color']}")
    print(f"User ID: {row['user_id']}")
    print(f"Is Public: {bool(row['is_public'])}")
    print(f"Created At: {row['created_at']}")
    print(f"Template JSON:")
    template_json = json.loads(row['template_json'])
    print(json.dumps(template_json, indent=2))
    print("=" * 80)
    
    conn.close()

def query_all_instances():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='template_instances'")
    if not cursor.fetchone():
        print("\nNo template_instances table found yet.")
        conn.close()
        return
    
    cursor.execute('''
        SELECT ti.*, t.name as template_name 
        FROM template_instances ti
        JOIN templates t ON ti.template_id = t.id
        ORDER BY ti.updated_at DESC
    ''')
    rows = cursor.fetchall()
    
    print(f"\n{'='*80}")
    print(f"Found {len(rows)} saved instances:\n")
    print("-" * 80)
    
    for row in rows:
        print(f"ID: {row['id']}")
        print(f"Template: {row['template_name']} (ID: {row['template_id']})")
        print(f"Instance Name: {row['instance_name']}")
        print(f"Created At: {row['created_at']}")
        print(f"Updated At: {row['updated_at']}")
        print(f"Data JSON:")
        data_json = json.loads(row['data_json'])
        print(json.dumps(data_json, indent=2))
        print("-" * 80)
    
    conn.close()

def main():
    while True:
        print("\nTemplate Tool Database Query")
        print("=" * 30)
        print("1. Show table list")
        print("2. Show all templates")
        print("3. Show template by ID")
        print("4. Show all saved instances")
        print("5. Show all users")
        print("6. Exit")
        print("=" * 30)
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            show_tables()
        elif choice == '2':
            query_all_templates()
        elif choice == '3':
            try:
                template_id = int(input("Enter template ID: ").strip())
                query_template_by_id(template_id)
            except ValueError:
                print("Invalid template ID. Please enter a number.")
        elif choice == '4':
            query_all_instances()
        elif choice == '5':
            show_users()
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-6.")
        
        input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()
