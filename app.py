from flask import Flask, jsonify, request, send_from_directory, redirect, url_for, flash, session
import sqlite3
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = 'templates.db'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return User(row[0], row[1], row[2])
    return None

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the users, templates, and template_instances tables."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create templates table with user_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            icon TEXT,
            color TEXT,
            template_json TEXT NOT NULL,
            is_public BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create template_instances table with user_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            instance_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (template_id) REFERENCES templates (id)
        )
    ''')
    
    # Check if we need to migrate existing data
    cursor.execute("PRAGMA table_info(templates)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_id' not in columns:
        # Migrate existing templates to a default user
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'default_user'")
        if cursor.fetchone()[0] == 0:
            # Create a default user
            default_password_hash = generate_password_hash('password')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', ('default_user', 'default@example.com', default_password_hash))
            default_user_id = cursor.lastrowid
            
            # Migrate existing templates
            cursor.execute('ALTER TABLE templates ADD COLUMN user_id INTEGER')
            cursor.execute('ALTER TABLE templates ADD COLUMN is_public BOOLEAN DEFAULT 0')
            cursor.execute('UPDATE templates SET user_id = ?, is_public = 1', (default_user_id,))
            
            # Migrate existing instances
            cursor.execute('ALTER TABLE template_instances ADD COLUMN user_id INTEGER')
            cursor.execute('UPDATE template_instances SET user_id = ?', (default_user_id,))
    
    # Check if we already have templates
    cursor.execute('SELECT COUNT(*) FROM templates')
    if cursor.fetchone()[0] == 0:
        # Create a default user for sample templates
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'demo_user'")
        if cursor.fetchone()[0] == 0:
            demo_password_hash = generate_password_hash('demo')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', ('demo_user', 'demo@example.com', demo_password_hash))
            demo_user_id = cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM users WHERE username = 'demo_user'")
            demo_user_id = cursor.fetchone()[0]
        
        # Insert sample templates
        sample_templates = [
            {
                'user_id': demo_user_id,
                'name': 'Project Management',
                'description': 'Track tasks, milestones, and team progress for any project',
                'category': 'Business',
                'icon': '📊',
                'color': '#4F46E5',
                'is_public': True,
                'template_json': json.dumps({
                    'sections': [
                        {
                            'name': 'Project Overview',
                            'fields': [
                                {'name': 'Project Name', 'type': 'text', 'required': True},
                                {'name': 'Start Date', 'type': 'date', 'required': True},
                                {'name': 'End Date', 'type': 'date', 'required': True},
                                {'name': 'Project Manager', 'type': 'text', 'required': True},
                                {'name': 'Budget', 'type': 'number', 'required': False}
                            ]
                        },
                        {
                            'name': 'Tasks',
                            'fields': [
                                {'name': 'Task Name', 'type': 'text', 'required': True},
                                {'name': 'Assignee', 'type': 'text', 'required': True},
                                {'name': 'Due Date', 'type': 'date', 'required': True},
                                {'name': 'Status', 'type': 'select', 'options': ['Not Started', 'In Progress', 'Completed'], 'required': True},
                                {'name': 'Priority', 'type': 'select', 'options': ['Low', 'Medium', 'High'], 'required': True}
                            ]
                        },
                        {
                            'name': 'Milestones',
                            'fields': [
                                {'name': 'Milestone Name', 'type': 'text', 'required': True},
                                {'name': 'Target Date', 'type': 'date', 'required': True},
                                {'name': 'Description', 'type': 'textarea', 'required': False}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Marketing Campaign',
                'description': 'Plan and execute marketing campaigns with tracking metrics',
                'category': 'Marketing',
                'icon': '📣',
                'color': '#EC4899',
                'is_public': True,
                'template_json': json.dumps({
                    'sections': [
                        {
                            'name': 'Campaign Details',
                            'fields': [
                                {'name': 'Campaign Name', 'type': 'text', 'required': True},
                                {'name': 'Objective', 'type': 'textarea', 'required': True},
                                {'name': 'Target Audience', 'type': 'text', 'required': True},
                                {'name': 'Budget', 'type': 'number', 'required': True},
                                {'name': 'Start Date', 'type': 'date', 'required': True},
                                {'name': 'End Date', 'type': 'date', 'required': True}
                            ]
                        },
                        {
                            'name': 'Channels',
                            'fields': [
                                {'name': 'Channel Name', 'type': 'select', 'options': ['Social Media', 'Email', 'PPC', 'Content', 'SEO'], 'required': True},
                                {'name': 'Budget Allocation', 'type': 'number', 'required': True},
                                {'name': 'KPIs', 'type': 'textarea', 'required': False}
                            ]
                        },
                        {
                            'name': 'Content Calendar',
                            'fields': [
                                {'name': 'Content Title', 'type': 'text', 'required': True},
                                {'name': 'Publish Date', 'type': 'date', 'required': True},
                                {'name': 'Platform', 'type': 'text', 'required': True},
                                {'name': 'Status', 'type': 'select', 'options': ['Draft', 'Review', 'Scheduled', 'Published'], 'required': True}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Product Roadmap',
                'description': 'Plan product features, releases, and long-term vision',
                'category': 'Product',
                'icon': '🗺️',
                'color': '#10B981',
                'is_public': True,
                'template_json': json.dumps({
                    'sections': [
                        {
                            'name': 'Product Vision',
                            'fields': [
                                {'name': 'Product Name', 'type': 'text', 'required': True},
                                {'name': 'Vision Statement', 'type': 'textarea', 'required': True},
                                {'name': 'Target Market', 'type': 'text', 'required': True}
                            ]
                        },
                        {
                            'name': 'Features',
                            'fields': [
                                {'name': 'Feature Name', 'type': 'text', 'required': True},
                                {'name': 'Description', 'type': 'textarea', 'required': True},
                                {'name': 'Priority', 'type': 'select', 'options': ['Must Have', 'Should Have', 'Nice to Have'], 'required': True},
                                {'name': 'Quarter', 'type': 'select', 'options': ['Q1', 'Q2', 'Q3', 'Q4'], 'required': True},
                                {'name': 'Status', 'type': 'select', 'options': ['Planned', 'In Development', 'Testing', 'Released'], 'required': True}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Event Planning',
                'description': 'Organize events with venue, guest lists, and schedules',
                'category': 'Events',
                'icon': '🎉',
                'color': '#F59E0B',
                'is_public': True,
                'template_json': json.dumps({
                    'sections': [
                        {
                            'name': 'Event Details',
                            'fields': [
                                {'name': 'Event Name', 'type': 'text', 'required': True},
                                {'name': 'Event Type', 'type': 'select', 'options': ['Conference', 'Workshop', 'Webinar', 'Social', 'Other'], 'required': True},
                                {'name': 'Date', 'type': 'date', 'required': True},
                                {'name': 'Location', 'type': 'text', 'required': True},
                                {'name': 'Expected Attendees', 'type': 'number', 'required': True},
                                {'name': 'Budget', 'type': 'number', 'required': False}
                            ]
                        },
                        {
                            'name': 'Agenda',
                            'fields': [
                                {'name': 'Session Title', 'type': 'text', 'required': True},
                                {'name': 'Start Time', 'type': 'text', 'required': True},
                                {'name': 'Duration (minutes)', 'type': 'number', 'required': True},
                                {'name': 'Speaker', 'type': 'text', 'required': False}
                            ]
                        },
                        {
                            'name': 'Vendors',
                            'fields': [
                                {'name': 'Vendor Name', 'type': 'text', 'required': True},
                                {'name': 'Service', 'type': 'text', 'required': True},
                                {'name': 'Cost', 'type': 'number', 'required': True},
                                {'name': 'Contact', 'type': 'text', 'required': False}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Content Strategy',
                'description': 'Plan and manage content creation and publishing',
                'category': 'Marketing',
                'icon': '✍️',
                'color': '#8B5CF6',
                'is_public': True,
                'template_json': json.dumps({
                    'sections': [
                        {
                            'name': 'Strategy Overview',
                            'fields': [
                                {'name': 'Content Goal', 'type': 'textarea', 'required': True},
                                {'name': 'Target Audience', 'type': 'text', 'required': True},
                                {'name': 'Key Topics', 'type': 'textarea', 'required': True},
                                {'name': 'Tone of Voice', 'type': 'text', 'required': False}
                            ]
                        },
                        {
                            'name': 'Content Pieces',
                            'fields': [
                                {'name': 'Title', 'type': 'text', 'required': True},
                                {'name': 'Type', 'type': 'select', 'options': ['Blog Post', 'Video', 'Infographic', 'Podcast', 'Social Post'], 'required': True},
                                {'name': 'Author', 'type': 'text', 'required': True},
                                {'name': 'Due Date', 'type': 'date', 'required': True},
                                {'name': 'Status', 'type': 'select', 'options': ['Idea', 'Writing', 'Editing', 'Ready', 'Published'], 'required': True}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Bug Tracker',
                'description': 'Track and manage software bugs and issues',
                'category': 'Development',
                'icon': '🐛',
                'color': '#EF4444',
                'is_public': True,
                'template_json': json.dumps({
                    'sections': [
                        {
                            'name': 'Bug Report',
                            'fields': [
                                {'name': 'Bug Title', 'type': 'text', 'required': True},
                                {'name': 'Description', 'type': 'textarea', 'required': True},
                                {'name': 'Steps to Reproduce', 'type': 'textarea', 'required': True},
                                {'name': 'Expected Behavior', 'type': 'textarea', 'required': True},
                                {'name': 'Actual Behavior', 'type': 'textarea', 'required': True},
                                {'name': 'Severity', 'type': 'select', 'options': ['Critical', 'High', 'Medium', 'Low'], 'required': True},
                                {'name': 'Status', 'type': 'select', 'options': ['Open', 'In Progress', 'Fixed', 'Closed', 'Won\'t Fix'], 'required': True},
                                {'name': 'Assigned To', 'type': 'text', 'required': False},
                                {'name': 'Environment', 'type': 'text', 'required': False}
                            ]
                        }
                    ]
                })
            }
        ]
        
        for template in sample_templates:
            cursor.execute('''
                INSERT INTO templates (user_id, name, description, category, icon, color, is_public, template_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (template['user_id'], template['name'], template['description'], template['category'], 
                  template['icon'], template['color'], template['is_public'], template['template_json']))
    
    conn.commit()
    conn.close()

# ==================== Authentication Routes ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log in the user
        user = User(user_id, username, email)
        login_user(user)
        
        return jsonify({'message': 'User registered successfully', 'user': {'id': user_id, 'username': username, 'email': email}}), 201
    
    return send_from_directory('.', 'register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username))
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row[3], password):  # password_hash is at index 3
            user = User(user_row[0], user_row[1], user_row[2])
            login_user(user)
            return jsonify({'message': 'Login successful', 'user': {'id': user.id, 'username': user.username, 'email': user.email}}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    
    return send_from_directory('.', 'login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/user')
@login_required
def get_current_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email
    })

# ==================== Template API Routes ====================

# Serve the main page
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return send_from_directory('.', 'index.html')

# API: Get all templates (user's own + public templates)
@app.route('/api/templates', methods=['GET'])
@login_required
def get_templates():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM templates 
        WHERE user_id = ? OR is_public = 1
        ORDER BY CASE WHEN user_id = ? THEN 0 ELSE 1 END, category, name
    ''', (current_user.id, current_user.id))
    rows = cursor.fetchall()
    conn.close()
    
    templates = []
    for row in rows:
        templates.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'name': row['name'],
            'description': row['description'],
            'category': row['category'],
            'icon': row['icon'],
            'color': row['color'],
            'is_public': bool(row['is_public']),
            'template_json': json.loads(row['template_json']),
            'created_at': row['created_at']
        })
    
    return jsonify(templates)

# API: Get single template
@app.route('/api/templates/<int:template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM templates WHERE id = ? AND (user_id = ? OR is_public = 1)', (template_id, current_user.id))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return jsonify({'error': 'Template not found'}), 404
    
    template = {
        'id': row['id'],
        'user_id': row['user_id'],
        'name': row['name'],
        'description': row['description'],
        'category': row['category'],
        'icon': row['icon'],
        'color': row['color'],
        'is_public': bool(row['is_public']),
        'template_json': json.loads(row['template_json']),
        'created_at': row['created_at']
    }
    
    return jsonify(template)

# API: Create new template
@app.route('/api/templates', methods=['POST'])
@login_required
def create_template():
    data = request.json
    
    if not data.get('name') or not data.get('template_json'):
        return jsonify({'error': 'Name and template_json are required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO templates (user_id, name, description, category, icon, color, is_public, template_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        current_user.id,
        data['name'],
        data.get('description', ''),
        data.get('category', 'Custom'),
        data.get('icon', '📄'),
        data.get('color', '#6B7280'),
        data.get('is_public', False),
        json.dumps(data['template_json'])
    ))
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'id': template_id, 'message': 'Template created successfully'}), 201

# API: Update template
@app.route('/api/templates/<int:template_id>', methods=['PUT'])
@login_required
def update_template(template_id):
    # Check if user owns this template
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM templates WHERE id = ?', (template_id,))
    row = cursor.fetchone()
    
    if not row or row['user_id'] != current_user.id:
        conn.close()
        return jsonify({'error': 'Template not found or access denied'}), 404
    
    data = request.json
    cursor.execute('''
        UPDATE templates 
        SET name = ?, description = ?, category = ?, icon = ?, color = ?, is_public = ?, template_json = ?
        WHERE id = ? AND user_id = ?
    ''', (
        data.get('name'),
        data.get('description'),
        data.get('category'),
        data.get('icon'),
        data.get('color'),
        data.get('is_public', False),
        json.dumps(data.get('template_json', {})),
        template_id,
        current_user.id
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Template updated successfully'})

# API: Delete template
@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    # Check if user owns this template
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM templates WHERE id = ?', (template_id,))
    row = cursor.fetchone()
    
    if not row or row['user_id'] != current_user.id:
        conn.close()
        return jsonify({'error': 'Template not found or access denied'}), 404
    
    cursor.execute('DELETE FROM templates WHERE id = ? AND user_id = ?', (template_id, current_user.id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Template deleted successfully'})

# ==================== Template Instances API ====================

# API: Get all instances for a template
@app.route('/api/templates/<int:template_id>/instances', methods=['GET'])
@login_required
def get_template_instances(template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM template_instances 
        WHERE template_id = ? AND user_id = ?
        ORDER BY updated_at DESC
    ''', (template_id, current_user.id))
    rows = cursor.fetchall()
    conn.close()
    
    instances = []
    for row in rows:
        instances.append({
            'id': row['id'],
            'template_id': row['template_id'],
            'instance_name': row['instance_name'],
            'data_json': json.loads(row['data_json']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    
    return jsonify(instances)

# API: Get all instances (across all templates)
@app.route('/api/instances', methods=['GET'])
@login_required
def get_all_instances():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ti.*, t.name as template_name, t.icon, t.color 
        FROM template_instances ti
        JOIN templates t ON ti.template_id = t.id
        WHERE ti.user_id = ?
        ORDER BY ti.updated_at DESC
    ''', (current_user.id,))
    rows = cursor.fetchall()
    conn.close()
    
    instances = []
    for row in rows:
        instances.append({
            'id': row['id'],
            'template_id': row['template_id'],
            'template_name': row['template_name'],
            'icon': row['icon'],
            'color': row['color'],
            'instance_name': row['instance_name'],
            'data_json': json.loads(row['data_json']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    
    return jsonify(instances)

# API: Get single instance
@app.route('/api/instances/<int:instance_id>', methods=['GET'])
@login_required
def get_instance(instance_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ti.*, t.name as template_name, t.icon, t.color, t.template_json
        FROM template_instances ti
        JOIN templates t ON ti.template_id = t.id
        WHERE ti.id = ? AND ti.user_id = ?
    ''', (instance_id, current_user.id))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return jsonify({'error': 'Instance not found'}), 404
    
    return jsonify({
        'id': row['id'],
        'template_id': row['template_id'],
        'template_name': row['template_name'],
        'icon': row['icon'],
        'color': row['color'],
        'template_json': json.loads(row['template_json']),
        'instance_name': row['instance_name'],
        'data_json': json.loads(row['data_json']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    })

# API: Create new instance
@app.route('/api/templates/<int:template_id>/instances', methods=['POST'])
@login_required
def create_instance(template_id):
    data = request.json
    
    if not data.get('instance_name'):
        return jsonify({'error': 'instance_name is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO template_instances (user_id, template_id, instance_name, data_json)
        VALUES (?, ?, ?, ?)
    ''', (
        current_user.id,
        template_id,
        data['instance_name'],
        json.dumps(data.get('data_json', {}))
    ))
    conn.commit()
    instance_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'id': instance_id, 'message': 'Instance created successfully'}), 201

# API: Update instance
@app.route('/api/instances/<int:instance_id>', methods=['PUT'])
@login_required
def update_instance(instance_id):
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE template_instances 
        SET instance_name = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (
        data.get('instance_name'),
        json.dumps(data.get('data_json', {})),
        instance_id,
        current_user.id
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Instance updated successfully'})

# API: Delete instance
@app.route('/api/instances/<int:instance_id>', methods=['DELETE'])
@login_required
def delete_instance(instance_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM template_instances WHERE id = ? AND user_id = ?', (instance_id, current_user.id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Instance deleted successfully'})

if __name__ == '__main__':
    init_db()
    print("Starting Template Tool server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
