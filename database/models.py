import aiosqlite

DB_NAME = "educenter.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        # Foydalanuvchilar (O'quvchi, O'qituvchi, Admin, Ota-ona)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT NOT NULL,
            phone TEXT,
            role TEXT DEFAULT 'parent', -- super_admin, admin, teacher, parent, student
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Guruhlar
        await db.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            monthly_fee REAL NOT NULL,
            teacher_id INTEGER,
            schedule TEXT DEFAULT '',
            room TEXT DEFAULT '',
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
        """)

        # Guruhga biriktirilgan o'quvchilar
        await db.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            group_id INTEGER,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id),
            UNIQUE(student_id, group_id)
        )
        """)

        # To'lovlar tarixi
        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            group_id INTEGER,
            amount REAL NOT NULL,
            payment_type TEXT NOT NULL, -- naqd yoki karta
            month_for TEXT NOT NULL,    -- masalan: '2026-09'
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
        """)

        # Davomat
        await db.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            student_id INTEGER,
            date TEXT NOT NULL,
            status TEXT NOT NULL, -- keldi, kelmadi, sababli
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
        """)

        # Ota-ona va O'quvchi bog'lanishi (Parent - Student relationship)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS student_parents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            parent_id INTEGER NOT NULL,
            relation_type TEXT DEFAULT 'ota', -- ota, ona, vasiy, boshqa
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(student_id, parent_id)
        )
        """)

        # Murojaat va takliflar (Feedbacks / Tickets)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            student_id INTEGER,
            feedback_type TEXT DEFAULT 'taklif', -- taklif, shikoyat, savol, boshqa
            message TEXT NOT NULL,
            status TEXT DEFAULT 'yangi', -- yangi, korildi, javob_berildi
            admin_reply TEXT,
            replied_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            replied_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (replied_by) REFERENCES users (id)
        )
        """)

        # Safe migration for existing tables
        async with db.execute("PRAGMA table_info(groups)") as cursor:
            cols = [row[1] for row in await cursor.fetchall()]
            if "schedule" not in cols:
                await db.execute("ALTER TABLE groups ADD COLUMN schedule TEXT DEFAULT ''")
            if "room" not in cols:
                await db.execute("ALTER TABLE groups ADD COLUMN room TEXT DEFAULT ''")

        async with db.execute("PRAGMA table_info(enrollments)") as cursor:
            e_cols = [row[1] for row in await cursor.fetchall()]
            if "enrolled_at" not in e_cols:
                await db.execute("ALTER TABLE enrollments ADD COLUMN enrolled_at TIMESTAMP DEFAULT ''")

        # Indexes for fast lookup
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_enrollments_student_group ON enrollments(student_id, group_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_group ON enrollments(group_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_student ON payments(student_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(group_id, date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_student_parents_parent ON student_parents(parent_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_student_parents_student ON student_parents(student_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_user ON feedbacks(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_status ON feedbacks(status)")

        await db.commit()