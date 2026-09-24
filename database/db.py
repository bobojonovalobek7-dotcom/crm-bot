from contextlib import asynccontextmanager
import aiosqlite
from config import normalize_role
from database.models import DB_NAME


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_NAME, timeout=30.0) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA busy_timeout = 30000;")
        db.row_factory = aiosqlite.Row
        yield db


# ==================== USERS ====================

async def add_user(telegram_id: int | None, full_name: str, phone: str = "", role: str = "parent"):
    normalized_role = normalize_role(role)
    async with get_db() as db:
        if telegram_id:
            await db.execute(
                "INSERT INTO users (telegram_id, full_name, phone, role) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(telegram_id) DO UPDATE SET full_name = excluded.full_name, phone = excluded.phone, role = excluded.role",
                (telegram_id, full_name, phone, normalized_role),
            )
        else:
            await db.execute(
                "INSERT INTO users (full_name, phone, role) VALUES (?, ?, ?)",
                (full_name, phone, normalized_role),
            )
        await db.commit()


async def get_user(telegram_id: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            return await cursor.fetchone()


async def get_user_by_id(user_id: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def get_users_by_role(role: str):
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE role = ? ORDER BY full_name", (role,)) as cursor:
            return await cursor.fetchall()


async def get_all_users():
    async with get_db() as db:
        async with db.execute("SELECT * FROM users ORDER BY role, full_name") as cursor:
            return await cursor.fetchall()


# ==================== GROUPS ====================

async def add_group(name: str, subject: str, monthly_fee: float, teacher_id: int, schedule: str = "", room: str = ""):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO groups (name, subject, monthly_fee, teacher_id, schedule, room) VALUES (?, ?, ?, ?, ?, ?)",
            (name, subject, monthly_fee, teacher_id, schedule, room),
        )
        await db.commit()
        return cursor.lastrowid


async def get_groups():
    async with get_db() as db:
        async with db.execute("""
            SELECT g.*, u.full_name AS teacher_name, u.phone AS teacher_phone,
                   (SELECT COUNT(*) FROM enrollments e WHERE e.group_id = g.id) AS student_count
            FROM groups g
            LEFT JOIN users u ON u.id = g.teacher_id
            ORDER BY g.name
        """) as cursor:
            return await cursor.fetchall()


async def get_group_by_id(group_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT g.*, u.full_name AS teacher_name, u.phone AS teacher_phone, u.telegram_id AS teacher_telegram_id
            FROM groups g
            LEFT JOIN users u ON u.id = g.teacher_id
            WHERE g.id = ?
        """, (group_id,)) as cursor:
            return await cursor.fetchone()


async def get_teacher_groups(teacher_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT g.*,
                   (SELECT COUNT(*) FROM enrollments e WHERE e.group_id = g.id) AS student_count
            FROM groups g
            WHERE g.teacher_id = ?
            ORDER BY g.name
        """, (teacher_id,)) as cursor:
            return await cursor.fetchall()


# ==================== ENROLLMENTS ====================

async def enroll_student(student_id: int, group_id: int):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO enrollments (student_id, group_id) VALUES (?, ?)",
            (student_id, group_id),
        )
        await db.commit()


async def unenroll_student(student_id: int, group_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM enrollments WHERE student_id = ? AND group_id = ?", (student_id, group_id))
        await db.commit()


async def get_student_groups(student_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT g.*, u.full_name AS teacher_name, u.phone AS teacher_phone, e.enrolled_at
            FROM enrollments e
            JOIN groups g ON g.id = e.group_id
            LEFT JOIN users u ON u.id = g.teacher_id
            WHERE e.student_id = ?
            ORDER BY g.name
        """, (student_id,)) as cursor:
            return await cursor.fetchall()


async def get_group_students(group_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT u.*, e.enrolled_at
            FROM enrollments e
            JOIN users u ON u.id = e.student_id
            WHERE e.group_id = ?
            ORDER BY u.full_name
        """, (group_id,)) as cursor:
            return await cursor.fetchall()


# ==================== PAYMENTS ====================

async def add_payment(student_id: int, group_id: int, amount: float, payment_type: str, month_for: str, note: str = ""):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO payments (student_id, group_id, amount, payment_type, month_for, note) VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, group_id, amount, payment_type, month_for, note),
        )
        await db.commit()
        return cursor.lastrowid


async def get_student_payments(student_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT p.*, g.name AS group_name, g.subject
            FROM payments p
            JOIN groups g ON g.id = p.group_id
            WHERE p.student_id = ?
            ORDER BY p.created_at DESC
        """, (student_id,)) as cursor:
            return await cursor.fetchall()


async def get_all_payments(limit: int = 100):
    async with get_db() as db:
        async with db.execute("""
            SELECT p.*, u.full_name AS student_name, u.phone AS student_phone, g.name AS group_name
            FROM payments p
            JOIN users u ON u.id = p.student_id
            JOIN groups g ON g.id = p.group_id
            ORDER BY p.created_at DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return await cursor.fetchall()


# ==================== ATTENDANCE ====================

async def record_attendance(group_id: int, student_id: int, date: str, status: str):
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM attendance WHERE group_id = ? AND student_id = ? AND date = ?",
            (group_id, student_id, date),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            await db.execute(
                "UPDATE attendance SET status = ? WHERE id = ?",
                (status, row["id"]),
            )
        else:
            await db.execute(
                "INSERT INTO attendance (group_id, student_id, date, status) VALUES (?, ?, ?, ?)",
                (group_id, student_id, date, status),
            )
        await db.commit()


async def get_group_attendance(group_id: int, date: str):
    async with get_db() as db:
        async with db.execute("""
            SELECT a.*, u.full_name AS student_name
            FROM attendance a
            JOIN users u ON u.id = a.student_id
            WHERE a.group_id = ? AND a.date = ?
            ORDER BY u.full_name
        """, (group_id, date)) as cursor:
            return await cursor.fetchall()


async def get_student_attendance(student_id: int, limit: int = 30):
    async with get_db() as db:
        async with db.execute("""
            SELECT a.*, g.name AS group_name, g.subject
            FROM attendance a
            JOIN groups g ON g.id = a.group_id
            WHERE a.student_id = ?
            ORDER BY a.date DESC
            LIMIT ?
        """, (student_id, limit)) as cursor:
            return await cursor.fetchall()


# ==================== STATS ====================

async def get_stats_summary():
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'student'") as c:
            students_count = (await c.fetchone())["total"]

        async with db.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'teacher'") as c:
            teachers_count = (await c.fetchone())["total"]

        async with db.execute("SELECT COUNT(*) AS total FROM groups") as c:
            groups_count = (await c.fetchone())["total"]

        async with db.execute("SELECT SUM(amount) AS total FROM payments") as c:
            row = await c.fetchone()
            total_revenue = float(row["total"] if row and row["total"] is not None else 0)

        async with db.execute("SELECT COUNT(*) AS total FROM attendance") as c:
            att_total = (await c.fetchone())["total"]

        async with db.execute("SELECT COUNT(*) AS total FROM attendance WHERE status = 'keldi'") as c:
            att_attended = (await c.fetchone())["total"]

        attendance_rate = (att_attended / att_total * 100) if att_total > 0 else 0

        async with db.execute("SELECT COUNT(*) AS total FROM feedbacks WHERE status = 'yangi'") as c:
            row_fb = await c.fetchone()
            new_feedbacks_count = row_fb["total"] if row_fb else 0

        async with db.execute("SELECT COUNT(DISTINCT parent_id) AS total FROM student_parents") as c:
            row_p = await c.fetchone()
            linked_parents_count = row_p["total"] if row_p else 0

        return {
            "students": students_count,
            "teachers": teachers_count,
            "groups": groups_count,
            "total_revenue": total_revenue,
            "attendance_rate": attendance_rate,
            "new_feedbacks": new_feedbacks_count,
            "linked_parents": linked_parents_count,
        }


# ==================== PARENT - STUDENT RELATIONSHIPS ====================

async def link_parent_student(parent_id: int, student_id: int, relation_type: str = "ota"):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO student_parents (parent_id, student_id, relation_type) VALUES (?, ?, ?) "
            "ON CONFLICT(student_id, parent_id) DO UPDATE SET relation_type = excluded.relation_type",
            (parent_id, student_id, relation_type),
        )
        await db.commit()


async def unlink_parent_student(parent_id: int, student_id: int):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM student_parents WHERE parent_id = ? AND student_id = ?",
            (parent_id, student_id),
        )
        await db.commit()


async def get_student_parents(student_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT sp.id AS link_id, sp.relation_type, sp.created_at,
                   u.id AS parent_id, u.telegram_id, u.full_name, u.phone, u.role
            FROM student_parents sp
            JOIN users u ON u.id = sp.parent_id
            WHERE sp.student_id = ?
            ORDER BY u.full_name
        """, (student_id,)) as cursor:
            return await cursor.fetchall()


async def get_parent_students(parent_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT sp.id AS link_id, sp.relation_type, sp.created_at,
                   u.id AS student_id, u.telegram_id, u.full_name, u.phone, u.role
            FROM student_parents sp
            JOIN users u ON u.id = sp.student_id
            WHERE sp.parent_id = ?
            ORDER BY u.full_name
        """, (parent_id,)) as cursor:
            return await cursor.fetchall()


async def get_all_parent_student_links():
    async with get_db() as db:
        async with db.execute("""
            SELECT sp.id AS link_id, sp.relation_type, sp.created_at,
                   p.id AS parent_id, p.full_name AS parent_name, p.phone AS parent_phone, p.telegram_id AS parent_telegram_id,
                   s.id AS student_id, s.full_name AS student_name, s.phone AS student_phone
            FROM student_parents sp
            JOIN users p ON p.id = sp.parent_id
            JOIN users s ON s.id = sp.student_id
            ORDER BY s.full_name, p.full_name
        """) as cursor:
            return await cursor.fetchall()


# ==================== FEEDBACKS / TICKETS ====================

async def create_feedback(user_id: int, message: str, feedback_type: str = "taklif", student_id: int | None = None):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO feedbacks (user_id, student_id, feedback_type, message, status) VALUES (?, ?, ?, ?, 'yangi')",
            (user_id, student_id, feedback_type, message),
        )
        await db.commit()
        return cursor.lastrowid


async def get_feedbacks(status: str | None = None, limit: int = 50):
    async with get_db() as db:
        query = """
            SELECT f.*,
                   u.full_name AS user_name, u.phone AS user_phone, u.role AS user_role, u.telegram_id AS user_telegram_id,
                   s.full_name AS student_name,
                   adm.full_name AS admin_name
            FROM feedbacks f
            JOIN users u ON u.id = f.user_id
            LEFT JOIN users s ON s.id = f.student_id
            LEFT JOIN users adm ON adm.id = f.replied_by
        """
        params = []
        if status:
            query += " WHERE f.status = ?"
            params.append(status)
        query += " ORDER BY f.created_at DESC LIMIT ?"
        params.append(limit)

        async with db.execute(query, tuple(params)) as cursor:
            return await cursor.fetchall()


async def get_feedback_by_id(feedback_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT f.*,
                   u.full_name AS user_name, u.phone AS user_phone, u.role AS user_role, u.telegram_id AS user_telegram_id,
                   s.full_name AS student_name,
                   adm.full_name AS admin_name
            FROM feedbacks f
            JOIN users u ON u.id = f.user_id
            LEFT JOIN users s ON s.id = f.student_id
            LEFT JOIN users adm ON adm.id = f.replied_by
            WHERE f.id = ?
        """, (feedback_id,)) as cursor:
            return await cursor.fetchone()


async def reply_to_feedback(feedback_id: int, reply_text: str, admin_id: int):
    async with get_db() as db:
        await db.execute("""
            UPDATE feedbacks
            SET admin_reply = ?, replied_by = ?, status = 'javob_berildi', replied_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reply_text, admin_id, feedback_id))
        await db.commit()


async def update_user_role(telegram_id: int, role: str):
    normalized = normalize_role(role)
    async with get_db() as db:
        await db.execute("UPDATE users SET role = ? WHERE telegram_id = ?", (normalized, telegram_id))
        await db.commit()


async def remove_admin(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM users WHERE id = ? AND role = 'admin'", (user_id,))
        await db.commit()


async def remove_admin_by_telegram_id(telegram_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM users WHERE telegram_id = ? AND role = 'admin'", (telegram_id,))
        await db.commit()