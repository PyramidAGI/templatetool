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
                'name': 'Sales Rep: Discovery Call',
                'description': 'Step-by-step discovery workflow for a sales representative',
                'category': 'Sales',
                'icon': '☎️',
                'color': '#4F46E5',
                'is_public': True,
                'template_json': json.dumps({
                    'steps': [
                        {
                            'name': 'Lead Context',
                            'fields': [
                                {'name': 'Lead Name', 'type': 'text', 'required': True},
                                {'name': 'Company', 'type': 'text', 'required': True},
                                {'name': 'Role', 'type': 'text', 'required': True},
                                {'name': 'Discovery Call Date', 'type': 'date', 'required': True},
                                {'name': 'Primary Pain Point', 'type': 'textarea', 'required': True}
                            ]
                        },
                        {
                            'name': 'Qualification Notes',
                            'fields': [
                                {'name': 'Need', 'type': 'textarea', 'required': True},
                                {'name': 'Budget', 'type': 'text', 'required': False},
                                {'name': 'Timeline', 'type': 'text', 'required': True},
                                {'name': 'Decision Process', 'type': 'textarea', 'required': False},
                                {'name': 'Next Step', 'type': 'text', 'required': True}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Customer Success: Onboarding Kickoff',
                'description': 'Workflow step for a CSM to launch a new customer onboarding',
                'category': 'Customer Success',
                'icon': '🤝',
                'color': '#EC4899',
                'is_public': True,
                'template_json': json.dumps({
                    'steps': [
                        {
                            'name': 'Customer Profile',
                            'fields': [
                                {'name': 'Account Name', 'type': 'text', 'required': True},
                                {'name': 'Primary Contact', 'type': 'text', 'required': True},
                                {'name': 'Kickoff Date', 'type': 'date', 'required': True},
                                {'name': 'Implementation Goal', 'type': 'textarea', 'required': True},
                                {'name': 'Stakeholders', 'type': 'textarea', 'required': False}
                            ]
                        },
                        {
                            'name': 'Onboarding Plan',
                            'fields': [
                                {'name': 'Milestones', 'type': 'textarea', 'required': True},
                                {'name': 'Internal Owner', 'type': 'text', 'required': True},
                                {'name': 'Dependencies', 'type': 'textarea', 'required': False},
                                {'name': 'Risks', 'type': 'textarea', 'required': False}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Product Manager: Sprint Planning',
                'description': 'Planning workflow step for a product manager to align a sprint',
                'category': 'Product',
                'icon': '🧭',
                'color': '#10B981',
                'is_public': True,
                'template_json': json.dumps({
                    'steps': [
                        {
                            'name': 'Sprint Basics',
                            'fields': [
                                {'name': 'Sprint Name', 'type': 'text', 'required': True},
                                {'name': 'Start Date', 'type': 'date', 'required': True},
                                {'name': 'End Date', 'type': 'date', 'required': True},
                                {'name': 'Sprint Goal', 'type': 'textarea', 'required': True},
                                {'name': 'Capacity (points)', 'type': 'number', 'required': False}
                            ]
                        },
                        {
                            'name': 'Stories Committed',
                            'fields': [
                                {'name': 'Story Title', 'type': 'text', 'required': True},
                                {'name': 'Priority', 'type': 'select', 'options': ['P0', 'P1', 'P2'], 'required': True},
                                {'name': 'Owner', 'type': 'text', 'required': True},
                                {'name': 'Definition of Done', 'type': 'textarea', 'required': False}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Recruiter: Candidate Screen',
                'description': 'Screening workflow step for a recruiter to qualify a candidate',
                'category': 'People',
                'icon': '🧑‍💼',
                'color': '#F59E0B',
                'is_public': True,
                'template_json': json.dumps({
                    'steps': [
                        {
                            'name': 'Candidate Profile',
                            'fields': [
                                {'name': 'Candidate Name', 'type': 'text', 'required': True},
                                {'name': 'Role', 'type': 'text', 'required': True},
                                {'name': 'Source', 'type': 'text', 'required': False},
                                {'name': 'Screen Date', 'type': 'date', 'required': True},
                                {'name': 'Location', 'type': 'text', 'required': False}
                            ]
                        },
                        {
                            'name': 'Screen Outcome',
                            'fields': [
                                {'name': 'Motivation', 'type': 'textarea', 'required': True},
                                {'name': 'Skills Match', 'type': 'textarea', 'required': True},
                                {'name': 'Comp Expectations', 'type': 'text', 'required': False},
                                {'name': 'Next Step', 'type': 'select', 'options': ['Advance', 'Hold', 'Reject'], 'required': True}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Support Agent: Ticket Triage',
                'description': 'Triage workflow step for a support agent to route new tickets',
                'category': 'Support',
                'icon': '🛠️',
                'color': '#8B5CF6',
                'is_public': True,
                'template_json': json.dumps({
                    'steps': [
                        {
                            'name': 'Ticket Intake',
                            'fields': [
                                {'name': 'Ticket ID', 'type': 'text', 'required': True},
                                {'name': 'Customer', 'type': 'text', 'required': True},
                                {'name': 'Channel', 'type': 'select', 'options': ['Email', 'Chat', 'Phone', 'Web'], 'required': True},
                                {'name': 'Issue Summary', 'type': 'textarea', 'required': True},
                                {'name': 'Severity', 'type': 'select', 'options': ['Low', 'Medium', 'High', 'Urgent'], 'required': True}
                            ]
                        },
                        {
                            'name': 'Routing',
                            'fields': [
                                {'name': 'Category', 'type': 'text', 'required': True},
                                {'name': 'Assigned Team', 'type': 'text', 'required': True},
                                {'name': 'SLA Tier', 'type': 'select', 'options': ['Standard', 'Priority', 'Premium'], 'required': True},
                                {'name': 'First Response Sent', 'type': 'select', 'options': ['Yes', 'No'], 'required': True}
                            ]
                        }
                    ]
                })
            },
            {
                'user_id': demo_user_id,
                'name': 'Designer: Handoff Review',
                'description': 'Handoff workflow step for a designer to align with engineering',
                'category': 'Design',
                'icon': '🎨',
                'color': '#EF4444',
                'is_public': True,
                'template_json': json.dumps({
                    'steps': [
                        {
                            'name': 'Design Package',
                            'fields': [
                                {'name': 'Feature', 'type': 'text', 'required': True},
                                {'name': 'Design Link', 'type': 'text', 'required': True},
                                {'name': 'Assets Included', 'type': 'textarea', 'required': False},
                                {'name': 'Spec Status', 'type': 'select', 'options': ['Draft', 'Ready', 'Final'], 'required': True},
                                {'name': 'Review Date', 'type': 'date', 'required': True}
                            ]
                        },
                        {
                            'name': 'Engineering Notes',
                            'fields': [
                                {'name': 'Implementation Notes', 'type': 'textarea', 'required': False},
                                {'name': 'Open Questions', 'type': 'textarea', 'required': False},
                                {'name': 'Sign-off', 'type': 'select', 'options': ['Pending', 'Approved'], 'required': True}
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
