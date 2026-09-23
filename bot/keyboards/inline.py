from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_teacher_groups_keyboard(groups: list) -> InlineKeyboardMarkup:
    buttons = []
    for g in groups:
        buttons.append([
            InlineKeyboardButton(text=f"📚 {g['name']} ({g['student_count']} ta)", callback_data=f"t_grp_{g['id']}"),
            InlineKeyboardButton(text="✅ Davomat", callback_data=f"t_att_{g['id']}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_attendance_marking_keyboard(students: list, group_id: int, current_status: dict[int, str]) -> InlineKeyboardMarkup:
    buttons = []
    for s in students:
        status = current_status.get(s["id"], "keldi")
        status_icon = "✅" if status == "keldi" else ("❌" if status == "kelmadi" else "⚠️")
        buttons.append([
            InlineKeyboardButton(
                text=f"{s['full_name']} - {status_icon}",
                callback_data=f"att_toggle_{group_id}_{s['id']}_{status}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="💾 Davomatni yakunlash", callback_data=f"att_done_{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍👩‍👧 Barcha o'quvchi va ota-onalarga", callback_data="bc_parents")],
            [InlineKeyboardButton(text="👨‍🏫 Barcha o'qituvchilarga", callback_data="bc_teachers")],
            [InlineKeyboardButton(text="👥 Barcha foydalanuvchilarga", callback_data="bc_all")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc_cancel")],
        ]
    )


def get_parent_children_keyboard(children: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in children:
        d = dict(ch)
        rel = d.get("relation_type")
        relation = f" ({rel.capitalize()})" if rel else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"👶 {d['full_name']}{relation}",
                callback_data=f"child_view_{d['student_id']}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_child_details_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Dars jadvali", callback_data=f"ch_sch_{student_id}"),
                InlineKeyboardButton(text="✅ Davomat", callback_data=f"ch_att_{student_id}"),
            ],
            [
                InlineKeyboardButton(text="💳 To'lovlar", callback_data=f"ch_pay_{student_id}"),
                InlineKeyboardButton(text="💬 Murojaat", callback_data=f"ch_fb_{student_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Boshqa farzand", callback_data="child_back")],
        ]
    )


def get_feedback_type_keyboard(student_id: int | None = None) -> InlineKeyboardMarkup:
    prefix = f"fbtype_{student_id or 0}_"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💡 Taklif", callback_data=f"{prefix}taklif"),
                InlineKeyboardButton(text="⚠️ Shikoyat", callback_data=f"{prefix}shikoyat"),
            ],
            [
                InlineKeyboardButton(text="❓ Savol", callback_data=f"{prefix}savol"),
                InlineKeyboardButton(text="📝 Boshqa", callback_data=f"{prefix}boshqa"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="fb_cancel")],
        ]
    )


def get_admin_feedback_action_keyboard(feedback_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Javob berish", callback_data=f"admfb_reply_{feedback_id}")],
        ]
    )


def get_admins_management_keyboard(admins: list, super_admin_ids: list[int] | None = None) -> InlineKeyboardMarkup:
    super_admin_ids = super_admin_ids or []
    buttons = []
    for adm in admins:
        tid = adm.get("telegram_id")
        name = adm.get("full_name", "Admin")
        adm_id = adm.get("id")
        if tid and tid in super_admin_ids:
            buttons.append([
                InlineKeyboardButton(text=f"👑 {name} (Super Admin)", callback_data="adm_noop")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text=f"🛡 {name}", callback_data="adm_noop"),
                InlineKeyboardButton(text="❌ O'chirish", callback_data=f"del_adm_{adm_id}")
            ])

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="adm_add_new")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_delete_admin_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Ha, admin o'chirilsin", callback_data=f"confirm_del_adm_{admin_id}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_del_adm")],
        ]
    )

