from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st


# Връзка към Supabase PostgreSQL чрез SQLAlchemy
def get_engine():
    db_url = st.secrets["postgres"]["url"]
    return create_engine(db_url)


# Инициализация на таблиците в Supabase
def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                last_name TEXT,
                company TEXT,
                email TEXT,
                phone TEXT,
                status TEXT DEFAULT 'Нов'
            );
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                last_name TEXT,
                company TEXT,
                email TEXT,
                phone TEXT
            );
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS addresses (
                id SERIAL PRIMARY KEY,
                address_text TEXT NOT NULL,
                address_type TEXT NOT NULL,
                lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
                client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL
            );
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS deals (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                amount NUMERIC DEFAULT 0.0,
                stage TEXT,
                client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE
            );
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS meetings (
                id SERIAL PRIMARY KEY,
                meeting_date TEXT NOT NULL,
                company TEXT,
                contact_name TEXT,
                notes TEXT,
                lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
                client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL
            );
        """)
        )


init_db()

st.set_page_config(page_title="yoCRM", layout="wide")

st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 10px; background-color: #0e1117; border-radius: 10px; margin-bottom: 20px; border: 1px solid #464b5d;">
        <span style="font-size: 32px; font-weight: bold; color: #ff4b4b; font-family: 'Arial Black', Gadget, sans-serif;">yo</span>
        <span style="font-size: 32px; font-weight: bold; color: #ffffff; font-family: 'Arial Black', Gadget, sans-serif;">CRM</span>
        <p style="font-size: 12px; color: #a3a8b4; margin: 0; font-style: italic;">Sales Management System</p>
    </div>
    """,
    unsafe_allow_html=True,
)

menu = st.sidebar.radio(
    "Меню", ["Лийдове", "Клиенти", "Адреси", "Сделки", "Срещи"]
)

engine = get_engine()

if menu == "Лийдове":
    st.header("Управление на Лийдове")
    with st.expander("Добави нов лийд"):
        with st.form("add_lead_form", clear_on_submit=True):
            col_fn, col_ln = st.columns(2)
            with col_fn:
                name = st.text_input("Име *")
            with col_ln:
                last_name = st.text_input("Фамилия")
            company = st.text_input("Компания")
            email = st.text_input("Имейл")
            phone = st.text_input("Телефон")
            submit = st.form_submit_button("Запази Лийд")
            if submit and name:
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                        INSERT INTO leads (name, last_name, company, email, phone)
                        VALUES (:name, :last_name, :company, :email, :phone)
                    """),
                        {
                            "name": name,
                            "last_name": last_name,
                            "company": company,
                            "email": email,
                            "phone": phone,
                        },
                    )
                st.success("Лийдът е добавен успешно!")
                st.rerun()

    st.subheader("Списък на Лийдове")
    with engine.connect() as conn:
        leads_df = pd.read_sql(
            text(
                'SELECT id, company as "Компания", name as "Име", last_name as'
                ' "Фамилия", email as "Имейл", phone as "Телефон", status as'
                ' "Статус" FROM leads ORDER BY id DESC'
            ),
            conn,
        )

    if not leads_df.empty:
        with st.expander("🔍 Филтри за колоните", expanded=False):
            f1, f2, f3 = st.columns(3)
            with f1:
                fc_company = st.text_input(
                    "Компания съдържа:", key="f_lead_comp"
                )
                fc_name = st.text_input("Име/Фамилия съдържа:", key="f_lead_name")
            with f2:
                fc_email = st.text_input("Имейл съдържа:", key="f_lead_email")
                fc_phone = st.text_input("Телефон съдържа:", key="f_lead_phone")
            with f3:
                statuses = [
                    s for s in leads_df["Статус"].unique() if s is not None
                ]
                fc_status = st.multiselect(
                    "Статус:", statuses, default=statuses, key="f_lead_stat"
                )

        filtered_leads = leads_df.copy()
        if fc_company:
            filtered_leads = filtered_leads[
                filtered_leads["Компания"]
                .fillna("")
                .str.contains(fc_company, case=False)
            ]
        if fc_name:
            filtered_leads = filtered_leads[
                filtered_leads["Име"].fillna("").str.contains(fc_name, case=False)
                | filtered_leads["Фамилия"]
                .fillna("")
                .str.contains(fc_name, case=False)
            ]
        if fc_email:
            filtered_leads = filtered_leads[
                filtered_leads["Имейл"]
                .fillna("")
                .str.contains(fc_email, case=False)
            ]
        if fc_phone:
            filtered_leads = filtered_leads[
                filtered_leads["Телефон"]
                .fillna("")
                .str.contains(fc_phone, case=False)
            ]
        if fc_status:
            filtered_leads = filtered_leads[
                filtered_leads["Статус"].isin(fc_status)
            ]

        edited_leads = st.data_editor(
            filtered_leads,
            key="edit_leads_table",
            hide_index=True,
            column_config={"id": None},
            use_container_width=True,
        )

        if st.button("Запази промените по лийдовете"):
            with engine.begin() as conn:
                for _, row in edited_leads.iterrows():
                    conn.execute(
                        text("""
                        UPDATE leads SET company=:company, name=:name, last_name=:last_name, email=:email, phone=:phone, status=:status WHERE id=:id
                    """),
                        {
                            "company": row["Компания"],
                            "name": row["Име"],
                            "last_name": row["Фамилия"],
                            "email": row["Имейл"],
                            "phone": row["Телефон"],
                            "status": row["Статус"],
                            "id": int(row["id"]),
                        },
                    )
            st.success("Успешно редактирахте лийдовете!")
            st.rerun()

        st.divider()
        st.subheader("Действия по Лийд")

        selected_lead_id = st.selectbox(
            "Избери лийд за допълнителни действия:",
            options=filtered_leads["id"].tolist(),
            format_func=lambda x: f"{filtered_leads.loc[filtered_leads['id'] == x, 'Име'].values[0]} {filtered_leads.loc[filtered_leads['id'] == x, 'Фамилия'].values[0] or ''} ({filtered_leads.loc[filtered_leads['id'] == x, 'Компания'].values[0] or ''})",
        )

        act_col1, act_col2 = st.columns(2)

        with act_col1:
            if st.button("Към Клиент (Конвертиране)"):
                with engine.begin() as conn:
                    l_data = conn.execute(
                        text(
                            "SELECT name, last_name, company, email, phone FROM"
                            " leads WHERE id = :id"
                        ),
                        {"id": int(selected_lead_id)},
                    ).fetchone()
                    if l_data:
                        res = conn.execute(
                            text("""
                            INSERT INTO clients (name, last_name, company, email, phone)
                            VALUES (:name, :last_name, :company, :email, :phone)
                            RETURNING id
                        """),
                            {
                                "name": l_data[0],
                                "last_name": l_data[1],
                                "company": l_data[2],
                                "email": l_data[3],
                                "phone": l_data[4],
                            },
                        )
                        new_client_id = res.fetchone()[0]
                        conn.execute(
                            text(
                                "UPDATE addresses SET client_id = :cid, lead_id"
                                " = NULL WHERE lead_id = :lid"
                            ),
                            {
                                "cid": new_client_id,
                                "lid": int(selected_lead_id),
                            },
                        )
                        conn.execute(
                            text("DELETE FROM leads WHERE id = :id"),
                            {"id": int(selected_lead_id)},
                        )
                        st.success("Лийдът беше успешно конвертиран в клиент!")
                st.rerun()

        with act_col2:
            if st.button("Покажи адреси за избрания лийд"):
                st.session_state["show_addr_selected_lead"] = (
                    not st.session_state.get("show_addr_selected_lead", False)
                )

        if st.session_state.get("show_addr_selected_lead", False):
            with engine.connect() as conn:
                l_addr = pd.read_sql(
                    text(
                        'SELECT address_text as "Адрес", address_type as'
                        ' "Тип" FROM addresses WHERE lead_id = :id'
                    ),
                    conn,
                    params={"id": int(selected_lead_id)},
                )
            if not l_addr.empty:
                st.dataframe(l_addr, hide_index=True, use_container_width=True)
            else:
                st.info("Няма регистрирани адреси за този лийд.")

    else:
        st.info("Няма налични лийдове.")

elif menu == "Клиенти":
    st.header("Списък на Клиенти")
    with engine.connect() as conn:
        clients_df = pd.read_sql(
            text(
                'SELECT id, company as "Компания", name as "Име", last_name as'
                ' "Фамилия", email as "Имейл", phone as "Телефон" FROM clients'
                " ORDER BY id DESC"
            ),
            conn,
        )

    if not clients_df.empty:
        with st.expander("🔍 Филтри за колоните", expanded=False):
            f1, f2 = st.columns(2)
            with f1:
                fc_comp = st.text_input(
                    "Компания съдържа:", key="f_client_comp"
                )
                fc_name = st.text_input(
                    "Име/Фамилия съдържа:", key="f_client_name"
                )
            with f2:
                fc_email = st.text_input("Имейл съдържа:", key="f_client_email")
                fc_phone = st.text_input(
                    "Телефон съдържа:", key="f_client_phone"
                )

        filtered_clients = clients_df.copy()
        if fc_comp:
            filtered_clients = filtered_clients[
                filtered_clients["Компания"]
                .fillna("")
                .str.contains(fc_comp, case=False)
            ]
        if fc_name:
            filtered_clients = filtered_clients[
                filtered_clients["Име"]
                .fillna("")
                .str.contains(fc_name, case=False)
                | filtered_clients["Фамилия"]
                .fillna("")
                .str.contains(fc_name, case=False)
            ]
        if fc_email:
            filtered_clients = filtered_clients[
                filtered_clients["Имейл"]
                .fillna("")
                .str.contains(fc_email, case=False)
            ]
        if fc_phone:
            filtered_clients = filtered_clients[
                filtered_clients["Телефон"]
                .fillna("")
                .str.contains(fc_phone, case=False)
            ]

        edited_clients = st.data_editor(
            filtered_clients,
            key="edit_clients_table",
            hide_index=True,
            column_config={"id": None},
            use_container_width=True,
        )

        if st.button("Запази промените по клиентите"):
            with engine.begin() as conn:
                for _, row in edited_clients.iterrows():
                    conn.execute(
                        text("""
                        UPDATE clients SET company=:company, name=:name, last_name=:last_name, email=:email, phone=:phone WHERE id=:id
                    """),
                        {
                            "company": row["Компания"],
                            "name": row["Име"],
                            "last_name": row["Фамилия"],
                            "email": row["Имейл"],
                            "phone": row["Телефон"],
                            "id": int(row["id"]),
                        },
                    )
            st.success("Успешно редактирахте клиентите!")
            st.rerun()

        st.divider()
        st.subheader("Действия по Клиент")

        selected_client_id = st.selectbox(
            "Избери клиент за преглед на адреси:",
            options=filtered_clients["id"].tolist(),
            format_func=lambda x: f"{filtered_clients.loc[filtered_clients['id'] == x, 'Име'].values[0]} {filtered_clients.loc[filtered_clients['id'] == x, 'Фамилия'].values[0] or ''} ({filtered_clients.loc[filtered_clients['id'] == x, 'Компания'].values[0] or ''})",
        )

        if st.button("Покажи адреси за избрания клиент"):
            st.session_state["show_addr_selected_client"] = (
                not st.session_state.get("show_addr_selected_client", False)
            )

        if st.session_state.get("show_addr_selected_client", False):
            with engine.connect() as conn:
                c_addr = pd.read_sql(
                    text(
                        'SELECT address_text as "Адрес", address_type as'
                        ' "Тип" FROM addresses WHERE client_id = :id'
                    ),
                    conn,
                    params={"id": int(selected_client_id)},
                )
            if not c_addr.empty:
                st.dataframe(c_addr, hide_index=True, use_container_width=True)
            else:
                st.info("Няма регистрирани адреси за този клиент.")

    else:
        st.info("Няма регистрирани клиенти.")

elif menu == "Адреси":
    st.header("Управление на Адреси")

    with engine.connect() as conn:
        leads = conn.execute(
            text("SELECT id, name, last_name, company FROM leads")
        ).fetchall()
        clients = conn.execute(
            text("SELECT id, name, last_name, company FROM clients")
        ).fetchall()

    target_options = {}
    for l in leads:
        lbl = (
            f"Лийд: {l[3]} ({l[1]} {l[2] or ''})".strip().rstrip(")")
            if l[3]
            else f"Лийд: {l[1]} {l[2] or ''}".strip()
        )
        target_options[lbl] = ("lead", l[0])
    for c in clients:
        lbl = (
            f"Клиент: {c[3]} ({c[1]} {c[2] or ''})".strip().rstrip(")")
            if c[3]
            else f"Клиент: {c[1]} {c[2] or ''}".strip()
        )
        target_options[lbl] = ("client", c[0])

    with st.expander("Добави нов Адрес"):
        with st.form("add_address_form", clear_on_submit=True):
            if target_options:
                selected_target = st.selectbox(
                    "Избери Лийд или Клиент *", list(target_options.keys())
                )
            else:
                st.text_input(
                    "Избери Лийд или Клиент",
                    value="Няма налични записи",
                    disabled=True,
                )
                selected_target = None

            col_addr, col_type = st.columns([3, 1])
            with col_addr:
                address_text = st.text_input("Адрес (улица, №, град) *")
            with col_type:
                address_type = st.selectbox(
                    "Тип адрес", ["Основен", "За кореспонденция", "Друг"]
                )

            submit_addr = st.form_submit_button("Запази Адрес")
            if submit_addr and address_text and selected_target:
                t_type, t_id = target_options[selected_target]
                lead_id = int(t_id) if t_type == "lead" else None
                client_id = int(t_id) if t_type == "client" else None

                with engine.begin() as conn:
                    conn.execute(
                        text("""
                        INSERT INTO addresses (address_text, address_type, lead_id, client_id)
                        VALUES (:address_text, :address_type, :lead_id, :client_id)
                    """),
                        {
                            "address_text": address_text,
                            "address_type": address_type,
                            "lead_id": lead_id,
                            "client_id": client_id,
                        },
                    )
                st.success("Адресът е добавен успешно!")
                st.rerun()

    st.subheader("Списък и Редакция на Адреси")

    filter_options = ["--- Всички адреси ---"] + list(target_options.keys())
    selected_filter = st.selectbox(
        "Филтрирай адресите по Клиент/Лийд:", filter_options
    )

    with engine.connect() as conn:
        if selected_filter == "--- Всички адреси ---":
            query = """
                SELECT a.id, a.address_text as "Адрес", a.address_type as "Тип",
                       COALESCE(c.company, l.company, c.name, l.name) as "Свързан обект"
                FROM addresses a
                LEFT JOIN clients c ON a.client_id = c.id
                LEFT JOIN leads l ON a.lead_id = l.id
            """
            addresses_df = pd.read_sql(text(query), conn)
        else:
            t_type, t_id = target_options[selected_filter]
            if t_type == "lead":
                query = (
                    'SELECT id, address_text as "Адрес", address_type as "Тип"'
                    ' FROM addresses WHERE lead_id = :id'
                )
            else:
                query = (
                    'SELECT id, address_text as "Адрес", address_type as "Тип"'
                    ' FROM addresses WHERE client_id = :id'
                )
            addresses_df = pd.read_sql(
                text(query), conn, params={"id": int(t_id)}
            )

    if not addresses_df.empty:
        edited_addresses = st.data_editor(
            addresses_df,
            key="edit_addresses_table",
            hide_index=True,
            column_config={"id": None},
            use_container_width=True,
        )
        if st.button("Запази промените по адресите"):
            with engine.begin() as conn:
                for _, row in edited_addresses.iterrows():
                    conn.execute(
                        text("""
                        UPDATE addresses SET address_text=:address_text, address_type=:address_type WHERE id=:id
                    """),
                        {
                            "address_text": row["Адрес"],
                            "address_type": row["Тип"],
                            "id": int(row["id"]),
                        },
                    )
            st.success("Промените са запазени!")
            st.rerun()
    else:
        st.info("Няма намерени адреси.")

elif menu == "Сделки":
    st.header("Управление на Сделки")
    with engine.connect() as conn:
        clients = conn.execute(
            text("SELECT id, name, last_name, company FROM clients")
        ).fetchall()

    client_options = (
        {
            f"{c[3] or ''} ({c[1]} {c[2] or ''})".strip()
            .lstrip("(")
            .rstrip(")"): c[0]
            for c in clients
        }
        if clients
        else {}
    )

    with st.expander("Създай нова Сделка"):
        if not client_options:
            st.warning("Първо трябва да имаш регистриран Клиент!")
        with st.form("add_deal_form", clear_on_submit=True):
            title = st.text_input("Име/Предмет на сделката")
            amount = st.number_input("Сума (BGN)", min_value=0.0, step=100.0)
            stage = st.selectbox(
                "Етап",
                ["В преговори", "Изпратена оферта", "Спечелена", "Загубена"],
            )
            if client_options:
                selected_client = st.selectbox(
                    "Избери Клиент/Фирма", list(client_options.keys())
                )
            else:
                st.text_input(
                    "Избери Клиент/Фирма",
                    value="Няма налични клиенти",
                    disabled=True,
                )
                selected_client = None
            submit_deal = st.form_submit_button("Създай Сделка")
            if submit_deal and title:
                client_id = (
                    int(client_options[selected_client])
                    if selected_client
                    else None
                )
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                        INSERT INTO deals (title, amount, stage, client_id)
                        VALUES (:title, :amount, :stage, :client_id)
                    """),
                        {
                            "title": title,
                            "amount": amount,
                            "stage": stage,
                            "client_id": client_id,
                        },
                    )
                st.success("Сделката е създадена!")
                st.rerun()

    st.subheader("Списък и Редакция на Сделки")
    with engine.connect() as conn:
        deals_df = pd.read_sql(
            text(
                'SELECT id, title as "Предмет на сделката", amount as "Сума'
                ' (BGN)", stage as "Етап" FROM deals ORDER BY id DESC'
            ),
            conn,
        )

    if not deals_df.empty:
        with st.expander("🔍 Филтри за колоните", expanded=False):
            f1, f2 = st.columns(2)
            with f1:
                fc_title = st.text_input(
                    "Предмет съдържа:", key="f_deal_title"
                )
            with f2:
                stages = [
                    s for s in deals_df["Етап"].unique() if s is not None
                ]
                fc_stage = st.multiselect(
                    "Етап:", stages, default=stages, key="f_deal_stage"
                )

        filtered_deals = deals_df.copy()
        if fc_title:
            filtered_deals = filtered_deals[
                filtered_deals["Предмет на сделката"]
                .fillna("")
                .str.contains(fc_title, case=False)
            ]
        if fc_stage:
            filtered_deals = filtered_deals[
                filtered_deals["Етап"].isin(fc_stage)
            ]

        edited_deals = st.data_editor(
            filtered_deals,
            key="edit_deals_table",
            hide_index=True,
            column_config={"id": None},
            use_container_width=True,
        )
        if st.button("Запази промените по сделките"):
            with engine.begin() as conn:
                for _, row in edited_deals.iterrows():
                    conn.execute(
                        text("""
                        UPDATE deals SET title=:title, amount=:amount, stage=:stage WHERE id=:id
                    """),
                        {
                            "title": row["Предмет на сделката"],
                            "amount": float(row["Сума (BGN)"]),
                            "stage": row["Етап"],
                            "id": int(row["id"]),
                        },
                    )
            st.success("Успешно редактирахте сделките!")
            st.rerun()
    else:
        st.info("Няма налични сделки.")

elif menu == "Срещи":
    st.header("График и Бележки от Срещи")
    with engine.connect() as conn:
        leads = conn.execute(
            text("SELECT id, name, last_name, company FROM leads")
        ).fetchall()
        clients = conn.execute(
            text("SELECT id, name, last_name, company FROM clients")
        ).fetchall()

    target_options = {}
    for l in leads:
        lbl = (
            f"Лийд: {l[3]} ({l[1]} {l[2] or ''})".strip().rstrip(")")
            if l[3]
            else f"Лийд: {l[1]} {l[2] or ''}".strip()
        )
        target_options[lbl] = (
            "lead",
            l[0],
            l[3],
            f"{l[1]} {l[2] or ''}".strip(),
        )
    for c in clients:
        lbl = (
            f"Клиент: {c[3]} ({c[1]} {c[2] or ''})".strip().rstrip(")")
            if c[3]
            else f"Клиент: {c[1]} {c[2] or ''}".strip()
        )
        target_options[lbl] = (
            "client",
            c[0],
            c[3],
            f"{c[1]} {c[2] or ''}".strip(),
        )

    with st.expander("Насрочи нова Среща"):
        with st.form("add_meeting_form", clear_on_submit=True):
            meeting_date = st.date_input("Дата на срещата", datetime.now())
            if target_options:
                selected_target = st.selectbox(
                    "Избери Лийд или Клиент", list(target_options.keys())
                )
            else:
                st.text_input(
                    "Избери Лийд или Клиент",
                    value="Няма налични лийдове или клиенти",
                    disabled=True,
                )
                selected_target = None
            notes_input = st.text_area("Бележки от срещата")
            submit_meeting = st.form_submit_button("Запази Срещата")
            if submit_meeting and selected_target:
                t_type, t_id, t_company, t_contact = target_options[
                    selected_target
                ]
                lead_id = int(t_id) if t_type == "lead" else None
                client_id = int(t_id) if t_type == "client" else None

                with engine.begin() as conn:
                    conn.execute(
                        text("""
                        INSERT INTO meetings (meeting_date, company, contact_name, notes, lead_id, client_id)
                        VALUES (:meeting_date, :company, :contact_name, :notes, :lead_id, :client_id)
                    """),
                        {
                            "meeting_date": str(meeting_date),
                            "company": t_company,
                            "contact_name": t_contact,
                            "notes": notes_input,
                            "lead_id": lead_id,
                            "client_id": client_id,
                        },
                    )
                st.success("Срещата е запазена успешно!")
                st.rerun()

    st.subheader("Списък и Редакция на Бележки от Срещи")
    with engine.connect() as conn:
        meetings_df = pd.read_sql(
            text(
                'SELECT id, meeting_date as "Дата", company as "Компания",'
                ' contact_name as "Лице за контакт", notes as "Бележки" FROM'
                " meetings ORDER BY meeting_date DESC"
            ),
            conn,
        )

    if not meetings_df.empty:
        with st.expander("🔍 Филтри за колоните", expanded=False):
            f1, f2 = st.columns(2)
            with f1:
                fc_m_comp = st.text_input(
                    "Компания съдържа:", key="f_meet_comp"
                )
                fc_m_contact = st.text_input(
                    "Лице за контакт съдържа:", key="f_meet_contact"
                )
            with f2:
                fc_m_notes = st.text_input(
                    "Бележки съдържат:", key="f_meet_notes"
                )

        filtered_meetings = meetings_df.copy()
        if fc_m_comp:
            filtered_meetings = filtered_meetings[
                filtered_meetings["Компания"]
                .fillna("")
                .str.contains(fc_m_comp, case=False)
            ]
        if fc_m_contact:
            filtered_meetings = filtered_meetings[
                filtered_meetings["Лице за контакт"]
                .fillna("")
                .str.contains(fc_m_contact, case=False)
            ]
        if fc_m_notes:
            filtered_meetings = filtered_meetings[
                filtered_meetings["Бележки"]
                .fillna("")
                .str.contains(fc_m_notes, case=False)
            ]

        edited_meetings = st.data_editor(
            filtered_meetings,
            key="edit_meetings_table",
            hide_index=True,
            column_config={"id": None},
            use_container_width=True,
        )
        if st.button("Запази промените по срещите"):
            with engine.begin() as conn:
                for _, row in edited_meetings.iterrows():
                    conn.execute(
                        text("""
                        UPDATE meetings SET meeting_date=:meeting_date, company=:company, contact_name=:contact_name, notes=:notes WHERE id=:id
                    """),
                        {
                            "meeting_date": str(row["Дата"]),
                            "company": row["Компания"],
                            "contact_name": row["Лице за контакт"],
                            "notes": row["Бележки"],
                            "id": int(row["id"]),
                        },
                    )
            st.success("Бележките от срещите са актуализирани успешно!")
            st.rerun()
    else:
        st.info("Няма регистрирани срещи.")
