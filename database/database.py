import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent.parent / "loan.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(cursor, table, column, definition):
    columns = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            balance INTEGER NOT NULL DEFAULT 1000,
            bank INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            daily_streak INTEGER NOT NULL DEFAULT 0,
            last_daily TEXT,
            job_key TEXT,
            job_level INTEGER NOT NULL DEFAULT 1,
            job_xp INTEGER NOT NULL DEFAULT 0,
            last_interest TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    # Existing databases from earlier versions get upgraded automatically.
    _ensure_column(cur, "users", "daily_streak", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cur, "users", "last_daily", "TEXT")
    _ensure_column(cur, "users", "job_key", "TEXT")
    _ensure_column(cur, "users", "job_level", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(cur, "users", "job_xp", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cur, "users", "last_interest", "TEXT")
    _ensure_column(cur, "users", "created_at", "TEXT NOT NULL DEFAULT ''")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            bank_after INTEGER NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            item_key TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id, item_key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            treasury INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            xp INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_members (
            company_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            salary INTEGER NOT NULL DEFAULT 0,
            role TEXT NOT NULL DEFAULT 'Çalışan',
            last_paid TEXT,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (company_id, user_id),
            FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)

    _ensure_column(cur, "company_members", "last_paid", "TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            price REAL NOT NULL,
            last_price REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            average_price REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id, symbol),
            FOREIGN KEY(symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            starting_money INTEGER NOT NULL DEFAULT 1000,
            daily_reward INTEGER NOT NULL DEFAULT 750,
            bank_interest REAL NOT NULL DEFAULT 0.02
        )
    """)

    seed_stocks = [
        ("AEX", "Axiom Enerji", "Enerji", 145.0),
        ("NOVA", "Nova Teknoloji", "Teknoloji", 230.0),
        ("MTRX", "Matrix Lojistik", "Lojistik", 98.0),
        ("VOLT", "Volt Otomotiv", "Otomotiv", 176.0),
        ("ORCA", "Orca Gıda", "Gıda", 72.0),
        ("SKY", "SkyNet Medya", "Medya", 315.0),
    ]
    now = datetime.now(timezone.utc).isoformat()
    for symbol, name, sector, price in seed_stocks:
        cur.execute("""
            INSERT OR IGNORE INTO stocks(symbol, name, sector, price, last_price, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (symbol, name, sector, price, price, now))

    conn.commit()
    conn.close()


def create_user(user_id, guild_id, starting_money=1000):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT OR IGNORE INTO users(
            user_id, guild_id, balance, bank, xp, level,
            daily_streak, last_daily, job_key, job_level, job_xp, last_interest, created_at
        ) VALUES (?, ?, ?, 0, 0, 1, 0, NULL, NULL, 1, 0, NULL, ?)
    """, (user_id, guild_id, starting_money, now))
    conn.commit()
    conn.close()


def get_user(user_id, guild_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    conn.close()
    return row


def ensure_guild(guild_id):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO guild_settings(guild_id) VALUES (?)",
        (guild_id,)
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM guild_settings WHERE guild_id=?",
        (guild_id,)
    ).fetchone()
    conn.close()
    return row


def update_user_money(user_id, guild_id, balance_delta=0, bank_delta=0, note=None, tx_type="işlem"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET balance = balance + ?, bank = bank + ?
        WHERE user_id=? AND guild_id=?
    """, (balance_delta, bank_delta, user_id, guild_id))
    row = cur.execute(
        "SELECT balance, bank FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO transactions(
            user_id, guild_id, type, amount,
            balance_after, bank_after, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, guild_id, tx_type,
        balance_delta + bank_delta,
        row["balance"], row["bank"], note, now
    ))
    conn.commit()
    conn.close()
    return row


def set_money(user_id, guild_id, balance=None, bank=None, note=None, tx_type="ayarlama"):
    conn = get_connection()
    cur = conn.cursor()
    old = cur.execute(
        "SELECT balance, bank FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    if old is None:
        conn.close()
        return None

    new_balance = old["balance"] if balance is None else balance
    new_bank = old["bank"] if bank is None else bank
    cur.execute("""
        UPDATE users SET balance=?, bank=? WHERE user_id=? AND guild_id=?
    """, (new_balance, new_bank, user_id, guild_id))
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO transactions(
            user_id, guild_id, type, amount,
            balance_after, bank_after, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, guild_id, tx_type,
        (new_balance - old["balance"]) + (new_bank - old["bank"]),
        new_balance, new_bank, note, now
    ))
    conn.commit()
    conn.close()
    return {"balance": new_balance, "bank": new_bank}


def add_xp(user_id, guild_id, amount):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT xp, level FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    if not row:
        conn.close()
        return None

    xp = row["xp"] + amount
    level = row["level"]
    leveled_up = False
    while xp >= level * 1000:
        xp -= level * 1000
        level += 1
        leveled_up = True

    cur.execute(
        "UPDATE users SET xp=?, level=? WHERE user_id=? AND guild_id=?",
        (xp, level, user_id, guild_id)
    )
    conn.commit()
    conn.close()
    return {"xp": xp, "level": level, "leveled_up": leveled_up}


def set_job(user_id, guild_id, job_key):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET job_key=?, job_level=1, job_xp=0 WHERE user_id=? AND guild_id=?",
        (job_key, user_id, guild_id)
    )
    conn.commit()
    conn.close()


def add_job_xp(user_id, guild_id, amount):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT job_xp, job_level FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    xp = row["job_xp"] + amount
    level = row["job_level"]
    leveled_up = False
    while xp >= level * 500:
        xp -= level * 500
        level += 1
        leveled_up = True
    cur.execute(
        "UPDATE users SET job_xp=?, job_level=? WHERE user_id=? AND guild_id=?",
        (xp, level, user_id, guild_id)
    )
    conn.commit()
    conn.close()
    return {"job_xp": xp, "job_level": level, "leveled_up": leveled_up}


def claim_daily_state(user_id, guild_id, reward):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT balance, bank, daily_streak, last_daily FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "reason": "user"}

    now = datetime.now(timezone.utc)
    last = None
    if row["last_daily"]:
        try:
            last = datetime.fromisoformat(row["last_daily"])
        except ValueError:
            last = None

    if last and (now - last).total_seconds() < 86400:
        remaining = 86400 - (now - last).total_seconds()
        conn.close()
        return {"ok": False, "reason": "cooldown", "remaining": int(remaining)}

    streak = row["daily_streak"] + 1 if last and (now - last).total_seconds() <= 172800 else 1
    final_reward = reward + min(streak * 50, 1000)
    cur.execute("""
        UPDATE users SET balance=balance+?, daily_streak=?, last_daily=?
        WHERE user_id=? AND guild_id=?
    """, (final_reward, streak, now.isoformat(), user_id, guild_id))
    new_row = cur.execute(
        "SELECT balance, bank FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    cur.execute("""
        INSERT INTO transactions(user_id,guild_id,type,amount,balance_after,bank_after,note,created_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (
        user_id, guild_id, "günlük", final_reward,
        new_row["balance"], new_row["bank"], f"{streak}. gün serisi",
        now.isoformat()
    ))
    conn.commit()
    conn.close()
    return {"ok": True, "reward": final_reward, "streak": streak, "balance": new_row["balance"]}


def claim_bank_interest(user_id, guild_id, rate):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT bank, last_interest FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "reason": "user"}

    now = datetime.now(timezone.utc)
    last = None
    if row["last_interest"]:
        try:
            last = datetime.fromisoformat(row["last_interest"])
        except ValueError:
            last = None
    if last and (now - last).total_seconds() < 86400:
        remaining = int(86400 - (now - last).total_seconds())
        conn.close()
        return {"ok": False, "reason": "cooldown", "remaining": remaining}

    interest = int(row["bank"] * rate)
    if interest <= 0:
        conn.execute(
            "UPDATE users SET last_interest=? WHERE user_id=? AND guild_id=?",
            (now.isoformat(), user_id, guild_id)
        )
        conn.commit()
        conn.close()
        return {"ok": True, "interest": 0}

    cur.execute(
        "UPDATE users SET bank=bank+?, last_interest=? WHERE user_id=? AND guild_id=?",
        (interest, now.isoformat(), user_id, guild_id)
    )
    new = cur.execute(
        "SELECT balance, bank FROM users WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    cur.execute("""
        INSERT INTO transactions(user_id,guild_id,type,amount,balance_after,bank_after,note,created_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (user_id, guild_id, "faiz", interest, new["balance"], new["bank"], f"Banka faizi %{rate*100:.2f}", now.isoformat()))
    conn.commit()
    conn.close()
    return {"ok": True, "interest": interest, "bank": new["bank"]}


def add_inventory(user_id, guild_id, item_key, quantity):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory(user_id,guild_id,item_key,quantity)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id,guild_id,item_key)
        DO UPDATE SET quantity=quantity+excluded.quantity
    """, (user_id, guild_id, item_key, quantity))
    cur.execute(
        "DELETE FROM inventory WHERE user_id=? AND guild_id=? AND quantity<=0",
        (user_id, guild_id)
    )
    conn.commit()
    conn.close()


def get_inventory(user_id, guild_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT item_key, quantity FROM inventory WHERE user_id=? AND guild_id=? AND quantity>0 ORDER BY item_key",
        (user_id, guild_id)
    ).fetchall()
    conn.close()
    return rows


def get_transactions(user_id, guild_id, limit=10):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM transactions
        WHERE user_id=? AND guild_id=?
        ORDER BY id DESC LIMIT ?
    """, (user_id, guild_id, limit)).fetchall()
    conn.close()
    return rows


def get_company_by_user(guild_id, user_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT c.* FROM companies c
        JOIN company_members cm ON cm.company_id=c.id
        WHERE c.guild_id=? AND cm.user_id=?
    """, (guild_id, user_id)).fetchone()
    conn.close()
    return row


def get_company_by_name(guild_id, name):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM companies WHERE guild_id=? AND lower(name)=lower(?)",
        (guild_id, name)
    ).fetchone()
    conn.close()
    return row


def create_company(guild_id, owner_id, name, cost):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO companies(guild_id,owner_id,name,treasury,level,xp,created_at)
        VALUES(?,?,?,?,1,0,?)
    """, (guild_id, owner_id, name, cost, datetime.now(timezone.utc).isoformat()))
    company_id = cur.lastrowid
    cur.execute("""
        INSERT INTO company_members(company_id,guild_id,user_id,salary,role,last_paid,joined_at)
        VALUES(?,?,?,?,?,?,?)
    """, (company_id, guild_id, owner_id, 0, "Kurucu", None, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return company_id


def add_company_employee(guild_id, company_id, user_id, salary):
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM company_members WHERE company_id=? AND user_id=?",
        (company_id, user_id)
    ).fetchone()
    if exists:
        conn.close()
        return False
    conn.execute("""
        INSERT INTO company_members(company_id,guild_id,user_id,salary,role,last_paid,joined_at)
        VALUES(?,?,?,?,?,?,?)
    """, (company_id, guild_id, user_id, salary, "Çalışan", None, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return True


def remove_company_employee(company_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM company_members WHERE company_id=? AND user_id=?",
        (company_id, user_id)
    )
    changed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def claim_salary(guild_id, company_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    member = cur.execute(
        "SELECT salary, last_paid FROM company_members WHERE company_id=? AND user_id=?",
        (company_id, user_id)
    ).fetchone()
    company = cur.execute(
        "SELECT treasury FROM companies WHERE id=? AND guild_id=?",
        (company_id, guild_id)
    ).fetchone()
    if not member or not company:
        conn.close()
        return {"ok": False, "reason": "not_member"}
    if member["salary"] <= 0:
        conn.close()
        return {"ok": False, "reason": "zero_salary"}

    now = datetime.now(timezone.utc)
    if member["last_paid"]:
        try:
            last = datetime.fromisoformat(member["last_paid"])
            if (now - last).total_seconds() < 86400:
                remaining = int(86400 - (now - last).total_seconds())
                conn.close()
                return {"ok": False, "reason": "cooldown", "remaining": remaining}
        except ValueError:
            pass

    salary = member["salary"]
    if company["treasury"] < salary:
        conn.close()
        return {"ok": False, "reason": "treasury", "treasury": company["treasury"]}

    cur.execute("UPDATE companies SET treasury=treasury-? WHERE id=? AND guild_id=?", (salary, company_id, guild_id))
    cur.execute("UPDATE company_members SET last_paid=? WHERE company_id=? AND user_id=?", (now.isoformat(), company_id, user_id))
    cur.execute("UPDATE users SET balance=balance+? WHERE user_id=? AND guild_id=?", (salary, user_id, guild_id))
    user = cur.execute("SELECT balance, bank FROM users WHERE user_id=? AND guild_id=?", (user_id, guild_id)).fetchone()
    cur.execute("""
        INSERT INTO transactions(user_id,guild_id,type,amount,balance_after,bank_after,note,created_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (user_id, guild_id, "maaş", salary, user["balance"], user["bank"], "Şirket maaşı", now.isoformat()))
    conn.commit()
    conn.close()
    return {"ok": True, "salary": salary, "balance": user["balance"]}


def get_company_members(company_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM company_members WHERE company_id=? ORDER BY role DESC, user_id",
        (company_id,)
    ).fetchall()
    conn.close()
    return rows


def update_company(guild_id, company_id, treasury_delta=0, xp_delta=0):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT treasury, xp, level FROM companies WHERE id=? AND guild_id=?",
        (company_id, guild_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    treasury = row["treasury"] + treasury_delta
    xp = row["xp"] + xp_delta
    level = row["level"]
    while xp >= level * 1000:
        xp -= level * 1000
        level += 1
    cur.execute(
        "UPDATE companies SET treasury=?,xp=?,level=? WHERE id=? AND guild_id=?",
        (treasury, xp, level, company_id, guild_id)
    )
    conn.commit()
    conn.close()
    return {"treasury": treasury, "xp": xp, "level": level}


def get_stock(symbol):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM stocks WHERE symbol=?",
        (symbol.upper(),)
    ).fetchone()
    conn.close()
    return row


def get_stocks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM stocks ORDER BY symbol").fetchall()
    conn.close()
    return rows


def set_stock_price(symbol, price):
    conn = get_connection()
    row = conn.execute("SELECT price FROM stocks WHERE symbol=?", (symbol.upper(),)).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute(
        "UPDATE stocks SET last_price=price, price=?, updated_at=? WHERE symbol=?",
        (price, datetime.now(timezone.utc).isoformat(), symbol.upper())
    )
    conn.commit()
    conn.close()
    return price


def get_portfolio(user_id, guild_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.*, s.name, s.price, s.sector
        FROM portfolios p JOIN stocks s ON s.symbol=p.symbol
        WHERE p.user_id=? AND p.guild_id=? AND p.quantity>0
        ORDER BY p.symbol
    """, (user_id, guild_id)).fetchall()
    conn.close()
    return rows


def set_portfolio(user_id, guild_id, symbol, quantity, average_price):
    conn = get_connection()
    if quantity <= 0:
        conn.execute(
            "DELETE FROM portfolios WHERE user_id=? AND guild_id=? AND symbol=?",
            (user_id, guild_id, symbol.upper())
        )
    else:
        conn.execute("""
            INSERT INTO portfolios(user_id,guild_id,symbol,quantity,average_price)
            VALUES(?,?,?,?,?)
            ON CONFLICT(user_id,guild_id,symbol)
            DO UPDATE SET quantity=excluded.quantity, average_price=excluded.average_price
        """, (user_id, guild_id, symbol.upper(), quantity, average_price))
    conn.commit()
    conn.close()


def leaderboard(guild_id, order_by, limit=10):
    allowed = {"balance", "level", "xp"}
    if order_by not in allowed:
        raise ValueError("Invalid leaderboard field")
    conn = get_connection()
    rows = conn.execute(
        f"SELECT * FROM users WHERE guild_id=? ORDER BY {order_by} DESC LIMIT ?",
        (guild_id, limit)
    ).fetchall()
    conn.close()
    return rows
