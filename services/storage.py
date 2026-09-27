import os
import json
import sqlite3
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uyirnilam.db")


def connection():
    database = sqlite3.connect(DB_PATH)
    database.row_factory = sqlite3.Row
    return database


def init_db(demo_mode=True):
    database = connection()
    database.executescript("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            location TEXT,
            preferred_language TEXT NOT NULL DEFAULT 'English',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS farms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            farm_name TEXT NOT NULL,
            location TEXT NOT NULL,
            area TEXT NOT NULL,
            crop TEXT NOT NULL,
            soil_type TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT '',
            district TEXT NOT NULL DEFAULT '',
            irrigation_type TEXT NOT NULL DEFAULT 'Unknown',
            created_at TEXT NOT NULL,
            FOREIGN KEY (farmer_id) REFERENCES farmers(id)
        );
        CREATE TABLE IF NOT EXISTS diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_id INTEGER NOT NULL,
            crop TEXT NOT NULL,
            condition TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            severity TEXT NOT NULL,
            symptoms TEXT NOT NULL,
            explanation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (farm_id) REFERENCES farms(id)
        );
    """)
    farmer_columns = {row[1] for row in database.execute("PRAGMA table_info(farmers)").fetchall()}
    farm_columns = {row[1] for row in database.execute("PRAGMA table_info(farms)").fetchall()}
    if "preferred_language" not in farmer_columns:
        database.execute("ALTER TABLE farmers ADD COLUMN preferred_language TEXT NOT NULL DEFAULT 'English'")
    for column in ("state", "district", "irrigation_type"):
        if column not in farm_columns:
            database.execute(f"ALTER TABLE farms ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    if demo_mode:
        farmer = database.execute("SELECT id FROM farmers WHERE phone = ?", ("demo@uyirnilam.local",)).fetchone()
        if farmer is None:
            cursor = database.execute("INSERT INTO farmers (name, phone, password_hash, location, preferred_language, created_at) VALUES (?, ?, ?, ?, ?, ?)", ("Ravi Kumar", "demo@uyirnilam.local", "demo", "Pune", "Hindi", datetime.now().isoformat()))
            database.execute("INSERT INTO farms (farmer_id, farm_name, location, area, crop, soil_type, state, district, irrigation_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (cursor.lastrowid, "Green Valley Farm", "Pune", "2.5 acres", "Tomato", "Black Soil", "Maharashtra", "Pune", "Drip", datetime.now().isoformat()))
    database.commit()
    database.close()


def get_farmer(farmer_id):
    database = connection()
    farmer = database.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    database.close()
    return dict(farmer) if farmer else None


def get_farmer_by_phone(phone):
    database = connection()
    farmer = database.execute("SELECT * FROM farmers WHERE phone = ?", (phone,)).fetchone()
    database.close()
    return dict(farmer) if farmer else None


def create_farmer(name, phone, password_hash, location, preferred_language="Hindi"):
    database = connection()
    cursor = database.execute("INSERT INTO farmers (name, phone, password_hash, location, preferred_language, created_at) VALUES (?, ?, ?, ?, ?, ?)", (name, phone, password_hash, location, preferred_language, datetime.now().isoformat()))
    database.execute("INSERT INTO farms (farmer_id, farm_name, location, area, crop, soil_type, state, district, irrigation_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (cursor.lastrowid, f"{name}'s Farm", location, "1 acre", "Tomato", "Don't Know", "", location, "Unknown", datetime.now().isoformat()))
    database.commit()
    farmer_id = cursor.lastrowid
    database.close()
    return farmer_id


def get_farm(farmer_id):
    database = connection()
    farm = database.execute("SELECT * FROM farms WHERE farmer_id = ? ORDER BY id LIMIT 1", (farmer_id,)).fetchone()
    database.close()
    return dict(farm) if farm else None


def update_farm(farmer_id, values):
    database = connection()
    database.execute("UPDATE farms SET farm_name = ?, location = ?, area = ?, crop = ?, soil_type = ?, state = ?, district = ?, irrigation_type = ? WHERE farmer_id = ?", (values["farm_name"], values["location"], values["area"], values["crop"], values["soil_type"], values.get("state", ""), values.get("district", ""), values.get("irrigation_type", "Unknown"), farmer_id))
    database.commit()
    database.close()


def update_language(farmer_id, preferred_language):
    database = connection()
    database.execute("UPDATE farmers SET preferred_language = ? WHERE id = ?", (preferred_language, farmer_id))
    database.commit()
    database.close()


def save_diagnosis(farmer_id, diagnosis):
    farm = get_farm(farmer_id)
    if farm is None:
        return None
    database = connection()
    cursor = database.execute("INSERT INTO diagnoses (farm_id, crop, condition, confidence, severity, symptoms, explanation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (farm["id"], diagnosis["crop"], diagnosis["condition"], diagnosis["confidence"], diagnosis["severity"], json.dumps(diagnosis["symptoms"]), diagnosis["explanation"], datetime.now().isoformat()))
    database.commit()
    diagnosis_id = cursor.lastrowid
    database.close()
    return diagnosis_id


def list_diagnoses(farmer_id):
    database = connection()
    rows = database.execute("SELECT diagnoses.* FROM diagnoses JOIN farms ON farms.id = diagnoses.farm_id WHERE farms.farmer_id = ? ORDER BY diagnoses.id DESC", (farmer_id,)).fetchall()
    database.close()
    return [dict(row) for row in rows]
