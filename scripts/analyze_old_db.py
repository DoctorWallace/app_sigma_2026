"""Analizar usuarios y grupos de old_db.sqlite3"""
import sqlite3

conn = sqlite3.connect('media/Datos/old_db.sqlite3')
cursor = conn.cursor()

print("="*60)
print("USUARIOS EN BD ANTIGUA")
print("="*60)
cursor.execute("SELECT id, username, email, first_name, last_name, is_active, is_staff, is_superuser FROM auth_user ORDER BY username")
users = cursor.fetchall()
print(f"Total usuarios: {len(users)}")
for u in users:
    print(f"  {u[0]:>3}. {u[1]:<20} {u[2]:<30} {u[3]} {u[4]}")

print("\n" + "="*60)
print("RELACION USUARIOS-GRUPOS (auth_user_groups)")
print("="*60)
cursor.execute("""
    SELECT u.username, g.name 
    FROM auth_user_groups ug
    JOIN auth_user u ON ug.user_id = u.id
    JOIN auth_group g ON ug.group_id = g.id
    ORDER BY g.name, u.username
""")
relations = cursor.fetchall()
print(f"Total relaciones: {len(relations)}")
for r in relations:
    print(f"  {r[0]:<25} -> {r[1]}")

conn.close()
