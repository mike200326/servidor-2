from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from flasgger import Swagger, swag_from

def create_app():
    app = Flask(__name__)
    CORS(app, origins=['http://localhost:3000'])
    swagger = Swagger(app)

    # Database configuration
    db_config = {
        'host': 'database-1.cpm0ooec0kjr.us-east-1.rds.amazonaws.com',
        'user': 'admin',
        'password': 'Elcuentodeapieron2024',
        'database': 'gamedb'
    }

    def get_db_connection():
        return mysql.connector.connect(**db_config)

    # Create tables if they don't exist before any request
    @app.before_request
    def create_tables():
        conn = get_db_connection()
        cursor = conn.cursor()

        # Ensure users table is created
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                initials VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                list VARCHAR(50),
                `group` VARCHAR(50),
                gender VARCHAR(50)
            );
        """)

        # Ensure statistics table is created
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                initials VARCHAR(255),
                games_played INT DEFAULT 0,
                average_score FLOAT DEFAULT 0,
                highest_score FLOAT DEFAULT 0,
                PRIMARY KEY (initials),
                FOREIGN KEY (initials) REFERENCES users(initials)
            );
        """)

        # Ensure leaderboard table is created
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                student_id VARCHAR(255),
                highest_score FLOAT DEFAULT 0,
                PRIMARY KEY (student_id),
                FOREIGN KEY (student_id) REFERENCES users(initials)
            );
        """)

        # Ensure objects table is created
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                score FLOAT NOT NULL,
                tries INT NOT NULL,
                user_initials VARCHAR(255),
                FOREIGN KEY (user_initials) REFERENCES users(initials)
            );
        """)

        # Ensure levels table is created
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                max_score INT NOT NULL
            );
        """)

        # Ensure user_levels table is created
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_levels (
                user_initials VARCHAR(255),
                level_id INT,
                completed BOOLEAN DEFAULT FALSE,
                score INT DEFAULT 0,
                tries INT DEFAULT 0,
                PRIMARY KEY (user_initials, level_id),
                FOREIGN KEY (user_initials) REFERENCES users(initials),
                FOREIGN KEY (level_id) REFERENCES levels(id)
            );
        """)

        # Create default levels if not exists
        cursor.execute("SELECT * FROM levels")
        cursor.fetchall()  # Consume all results to avoid "Unread result found"
        if cursor.rowcount == 0:
            default_levels = [
                ('Level 1', 100),
                ('Level 2', 200),
                ('Level 3', 300)
            ]
            cursor.executemany("INSERT INTO levels (name, max_score) VALUES (%s, %s)", default_levels)
            conn.commit()

        conn.commit()
        cursor.close()
        conn.close()

    # User class definition
    class User:
        def __init__(self, initials, password, role, list_name, group, gender):
            self.initials = initials
            self.password = generate_password_hash(password)
            self.role = role
            self.list_name = list_name
            self.group = group
            self.gender = gender

        def save_to_db(self, cursor):
            cursor.execute("""
                INSERT INTO users (initials, password, role, list, `group`, gender) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (self.initials, self.password, self.role, self.list_name, self.group, self.gender))
            cursor.execute("""
                INSERT INTO statistics (initials, games_played, average_score, highest_score) 
                VALUES (%s, %s, %s, %s)
            """, (self.initials, 0, 0, 0))
            cursor.execute("""
                INSERT INTO leaderboard (student_id, highest_score) 
                VALUES (%s, %s)
            """, (self.initials, 0))
            cursor.execute("""
                INSERT INTO user_levels (user_initials, level_id, score, tries) 
                SELECT %s, id, 0, 0 FROM levels
            """, (self.initials,))

    def _build_cors_prelight_response():
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response

    @app.route('/register', methods=['POST', 'OPTIONS'])
    @swag_from({
        'responses': {
            201: {
                'description': 'User registered successfully',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'message': {'type': 'string'}
                    }
                },
                'examples': {
                    'application/json': {
                        'success': True,
                        'message': 'Registration successful.'
                    }
                }
            },
            400: {
                'description': 'Missing data or invalid request',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'message': {'type': 'string'}
                    }
                },
                'examples': {
                    'application/json': {
                        'success': False,
                        'message': 'Missing data.'
                    }
                }
            },
            409: {
                'description': 'User already exists',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'message': {'type': 'string'}
                    }
                },
                'examples': {
                    'application/json': {
                        'success': False,
                        'message': 'User already exists.'
                    }
                }
            }
        },
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'schema': {
                    'type': 'object',
                    'properties': {
                        'initials': {'type': 'string', 'example': 'jdoe'},
                        'list': {'type': 'string', 'example': 'list1'},
                        'userType': {'type': 'string', 'example': 'student'},
                        'group': {'type': 'string', 'example': 'A'},
                        'gender': {'type': 'string', 'example': 'male'},
                        'password': {'type': 'string', 'example': 'password123'}
                    }
                }
            }
        ]
    })
    def register():
        if request.method == 'OPTIONS':
            return _build_cors_prelight_response()
        elif request.method == 'POST':
            data = request.get_json()
            print("Received registration data:", data)  # Log the received data
            if not data:
                return make_response(jsonify({'success': False, 'message': 'No data provided'}), 400)
            
            try:
                new_user = User(
                    initials=data['initials'],
                    password=data['password'],
                    role=data.get('userType', 'student'),
                    list_name=data.get('list', ''),  # Handle optional field
                    group=data.get('group', ''),     # Handle optional field
                    gender=data['gender']
                )
                print("User object created:", new_user.__dict__)  # Log the user object
            except KeyError as e:
                return make_response(jsonify({'success': False, 'message': f'Missing data for {str(e)}'}), 400)

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("SELECT * FROM users WHERE initials = %s", (new_user.initials,))
                if cursor.fetchone():
                    return make_response(jsonify({'success': False, 'message': 'User already exists.'}), 409)
                
                new_user.save_to_db(cursor)
                conn.commit()
            except Exception as e:
                print("Error during database operation:", str(e))
                return make_response(jsonify({'success': False, 'message': 'Database error occurred'}), 500)
            finally:
                cursor.close()
                conn.close()

            return make_response(jsonify({'success': True, 'message': 'Registration successful.'}), 201)

    @app.route('/login', methods=['POST'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Login successful',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'message': {'type': 'string'},
                        'user': {
                            'type': 'object',
                            'properties': {
                                'initials': {'type': 'string'},
                                'role': {'type': 'string'},
                                'list': {'type': 'string'},
                                'group': {'type': 'string'},
                                'gender': {'type': 'string'}
                            }
                        }
                    }
                },
                'examples': {
                    'application/json': {
                        'success': True,
                        'message': 'Login successful.',
                        'user': {
                            'initials': 'jdoe',
                            'role': 'student',
                            'list': 'list1',
                            'group': 'A',
                            'gender': 'male'
                        }
                    }
                }
            },
            400: {
                'description': 'Missing data or invalid request',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'message': {'type': 'string'}
                    }
                },
                'examples': {
                    'application/json': {
                        'success': False,
                        'message': 'Missing data.'
                    }
                }
            },
            401: {
                'description': 'Invalid credentials',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'message': {'type': 'string'}
                    }
                },
                'examples': {
                    'application/json': {
                        'success': False,
                        'message': 'Invalid credentials.'
                    }
                }
            }
        },
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'schema': {
                    'type': 'object',
                    'properties': {
                        'initials': {'type': 'string', 'example': 'jdoe'},
                        'password': {'type': 'string', 'example': 'password123'}
                    }
                }
            }
        ]
    })
    def login():
        data = request.get_json()
        if not data:
            return make_response(jsonify({'success': False, 'message': 'No data provided'}), 400)

        user_initials = data.get('initials')
        user_password = data.get('password')

        if not user_initials or not user_password:
            return make_response(jsonify({'success': False, 'message': 'Missing data.'}), 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE initials = %s", (user_initials,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], user_password):
            user_info = {
                'initials': user['initials'],
                'role': user['role'],
                'list': user['list'],
                'group': user['group'],
                'gender': user['gender']
            }
            cursor.close()
            conn.close()
            return make_response(jsonify({'success': True, 'message': 'Login successful.', 'user': user_info}), 200)
        else:
            cursor.close()
            conn.close()
            return make_response(jsonify({'success': False, 'message': 'Invalid credentials.'}), 401)

    @app.route('/data/points', methods=['GET'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Points data for professors',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'usuario_nombre': {'type': 'string'},
                            'grupo_nombre': {'type': 'string'},
                            'total_puntuacion': {'type': 'number'},
                            'list': {'type': 'string'},
                            'role': {'type': 'string'}
                        }
                    }
                }
            },
            'examples': {
                'application/json': [
                    {
                        'usuario_nombre': 'John',
                        'grupo_nombre': 'A',
                        'total_puntuacion': 90,
                        'list': 'list1',
                        'role': 'student'
                    },
                    {
                        'usuario_nombre': 'Jane',
                        'grupo_nombre': 'B',
                        'total_puntuacion': 80,
                        'list': 'list2',
                        'role': 'student'
                    }
                ]
            }
        }
    })
    def get_points_data():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        group = request.args.get('group', '')
        lists = request.args.getlist('lists')
        
        query = """
            SELECT 
                u.initials AS usuario_nombre, 
                u.group AS grupo_nombre, 
                u.list AS list,
                u.role AS role,
                SUM(o.score) AS total_puntuacion
            FROM users u
            JOIN objects o ON u.initials = o.user_initials
        """
        
        conditions = []
        params = []
        if group:
            conditions.append("u.group = %s")
            params.append(group)
        if lists:
            conditions.append("u.list IN (%s)" % ','.join(['%s'] * len(lists)))
            params.extend(lists)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " GROUP BY u.initials, u.group, u.list"
        
        cursor.execute(query, tuple(params))
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data), 200

    @app.route('/data/time', methods=['GET'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Time data for professors',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'usuario_nombre': {'type': 'string'},
                            'grupo_nombre': {'type': 'string'},
                            'total_tiempo': {'type': 'number'},
                            'list': {'type': 'string'},
                            'role': {'type': 'string'}
                        }
                    }
                }
            },
            'examples': {
                'application/json': [
                    {
                        'usuario_nombre': 'John',
                        'grupo_nombre': 'A',
                        'total_tiempo': 120,
                        'list': 'list1',
                        'role': 'student'
                    },
                    {
                        'usuario_nombre': 'Jane',
                        'grupo_nombre': 'B',
                        'total_tiempo': 100,
                        'list': 'list2',
                        'role': 'student'
                    }
                ]
            }
        }
    })
    def get_time_data():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        group = request.args.get('group', '')
        lists = request.args.getlist('lists')
        
        query = """
            SELECT 
                u.initials AS usuario_nombre, 
                u.group AS grupo_nombre, 
                u.list AS list,
                u.role AS role,
                SUM(o.tries * 60) AS total_tiempo  -- Assuming each try is 60 seconds
            FROM users u
            JOIN objects o ON u.initials = o.user_initials
        """
        
        conditions = []
        params = []
        if group:
            conditions.append("u.group = %s")
            params.append(group)
        if lists:
            conditions.append("u.list IN (%s)" % ','.join(['%s'] * len(lists)))
            params.extend(lists)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " GROUP BY u.initials, u.group, u.list"
        
        cursor.execute(query, tuple(params))
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data), 200

    @app.route('/data/groups', methods=['GET'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Groups data',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'group_name': {'type': 'string'}
                        }
                    }
                }
            },
            'examples': {
                'application/json': [
                    {
                        'group_name': 'A'
                    },
                    {
                        'group_name': 'B'
                    }
                ]
            }
        }
    })
    def get_groups():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT `group` AS group_name FROM users")
        groups = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(groups), 200

    @app.route('/data/lists', methods=['GET'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Lists data',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'list': {'type': 'string'}
                        }
                    }
                }
            },
            'examples': {
                'application/json': [
                    {
                        'list': 'list1'
                    },
                    {
                        'list': 'list2'
                    }
                ]
            }
        }
    })
    def get_lists():
        group = request.args.get('group', '')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if group:
            cursor.execute("SELECT DISTINCT `list` FROM users WHERE `group` = %s", (group,))
        else:
            cursor.execute("SELECT DISTINCT `list` FROM users")
        lists = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(lists), 200

    @app.route('/data/leaderboard', methods=['GET'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Leaderboard data',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'usuario_nombre': {'type': 'string'},
                            'highest_score': {'type': 'number'},
                            'role': {'type': 'string'}
                        }
                    }
                }
            },
            'examples': {
                'application/json': [
                    {
                        'usuario_nombre': 'John',
                        'highest_score': 95,
                        'role': 'student'
                    },
                    {
                        'usuario_nombre': 'Jane',
                        'highest_score': 90,
                        'role': 'student'
                    }
                ]
            }
        }
    })
    def get_leaderboard():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.initials AS usuario_nombre, 
                l.highest_score,
                u.role AS role
            FROM users u
            JOIN leaderboard l ON u.initials = l.student_id
            ORDER BY l.highest_score DESC
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data), 200

    @app.route('/user_levels/<user_initials>', methods=['PUT'])
    @swag_from({
        'responses': {
            200: {
                'description': 'User level updated successfully',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string'}
                    }
                }
            },
            'examples': {
                'application/json': {
                    'message': 'User level updated successfully'
                }
            }
        }
    })
    def update_user_level(user_initials):
        data = request.get_json()
        level_id = data.get('level_id')
        score = data.get('score', 0)
        tries = data.get('tries', 0)
        completed = data.get('completed', False)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_levels
            SET score = %s, tries = %s, completed = %s
            WHERE user_initials = %s AND level_id = %s
        """, (score, tries, completed, user_initials, level_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'User level updated successfully'}), 200

    # New endpoint to fetch group comparison data
    @app.route('/data/group-comparison', methods=['GET'])
    @swag_from({
        'responses': {
            200: {
                'description': 'Group comparison data',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'group': {'type': 'string'},
                            'scores': {'type': 'array', 'items': {'type': 'number'}}
                        }
                    }
                }
            },
            'examples': {
                'application/json': [
                    {
                        'group': 'A',
                        'scores': [95, 80, 75]
                    },
                    {
                        'group': 'B',
                        'scores': [85, 70, 90]
                    }
                ]
            }
        }
    })
    def get_group_comparison_data():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                u.group AS `group`, 
                o.score 
            FROM users u
            JOIN objects o ON u.initials = o.user_initials
            WHERE u.group IN ('A', 'B', 'C', 'D')
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        group_data = {}
        for result in results:
            group = result['group']
            score = result['score']
            if group not in group_data:
                group_data[group] = []
            group_data[group].append(score)
        
        group_comparison_data = [{'group': group, 'scores': scores} for group, scores in group_data.items()]
        
        cursor.close()
        conn.close()
        return jsonify(group_comparison_data), 200

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=14465)
