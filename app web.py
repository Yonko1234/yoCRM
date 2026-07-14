import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

# Връзка към PostgreSQL (Supabase)
# Данните за връзката ще бъдат скрити безопасно в Streamlit Secrets
def get_engine():
    db_url = st.secrets["postgres"]["url"]
    return create_engine(db_url)

def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        # Таблица Лийдове
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                last_name TEXT,
                company TEXT,
                email TEXT,
                phone TEXT,
                status TEXT DEFAULT 'Нов'
            )
        '''))

        # Таблица Клиенти
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                last_name TEXT,
                company TEXT,
                email TEXT,
                phone TEXT
            )
        '''))

        # Таблица Адреси
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS addresses (
                id SERIAL PRIMARY KEY,
                address_text TEXT NOT NULL,
                address_type TEXT NOT NULL,
                lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
                client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE
            )
        '''))

        # Таблица Сделки
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS deals (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                amount NUMERIC DEFAULT 0.0,
                stage TEXT,
                client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE
            )
        '''))

        # Таблица Срещи
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS meetings (
                id SERIAL PRIMARY KEY,
                meeting_date TEXT NOT NULL,
                company TEXT,
                contact_name TEXT,
                notes TEXT,
                lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
                client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE
            )
        '''))
        conn.commit()

init_db()

st.set_page_config(page_title="yoCRM", layout="wide")

# Текстово лого в Sidebar
st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 10px; background-color: #0e1117; border-radius: 10px; margin-bottom: 20px; border: 1px solid #464b5d;">
        <span style="font-size: 32px; font-weight: bold; color: #ff4b4b; font-family: 'Arial Black', Gadget, sans-serif;">yo</span>
        <span style="font-size: 32px; font-weight: bold; color: #ffffff; font-family: 'Arial Black', Gadget, sans-serif;">CRM</span>
        <p style="font-size: 12px; color: #a3a8b4; margin: 0; font-style: italic;">Sales Management System</p>
    </div>
    """,
    unsafe_allow_html=True
)

menu = st.sidebar.radio("Меню", ["🎯 Лийдове", "👥 Клиенти", "📍 Адреси", "💰 Сделки", "📅 Срещи"])

engine = get_engine()

if menu == "🎯 Лийдове":
    st.header("🎯 Управление на Лийдове")
    with st.expander("➕ Добави нов лийд"):
        with st.form("add_lead_form"):
            col_fn, col_ln = st.columns(2)
            with col_fn: name = st.text_input("Име *")
            with col_ln: last_name = st.text_input("Фамилия")
            company = st.text_input("Компания")
            email = st.text_input("Имейл")
            phone = st.text_input("Телефон")
            submit = st.form_submit_button("Запази Лийд")
            if submit and name:
                with engine.connect() as conn:
                    conn.execute(
                        text("INSERT INTO leads (name, last_name, company, email, phone) VALUES (:name, :last_name, :company, :email, :phone)"),
                        {"name": name, "last_name": last_name, "company": company, "email": email, "phone": phone}
                    )
                    conn.commit()
                st.success("Лийдът е добавен успешно!")
                st.rerun()

    st.subheader("📝 Списък на Лийдове")
    leads_df = pd.read_sql("SELECT id, company, name, last_name, email, phone, status FROM leads ORDER BY id DESC", engine)
    
    if not leads_df.empty:
        c_comp, c_name, c_lname, c_email, c_phone, c_stat, c_btn = st.columns([2, 1.5, 1.5, 2, 1.5, 1.5, 1])
        c_comp.write("**Компания**")
        c_name.write("**Име**")
        c_lname.write("**Фамилия**")
        c_email.write("**Имейл**")
        c_phone.write("**Телефон**")
        c_stat.write("**Статус**")
        c_btn.write("**Действие**")
        st.divider()

        for idx, row in leads_df.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.5, 1.5, 2, 1.5, 1.5, 1])
            col1.text(row['company'] or '')
            col2.text(row['name'] or '')
            col3.text(row['last_name'] or '')
            col4.text(row['email'] or '')
            col5.text(row['phone'] or '')
            col6.text(row['status'] or 'Нов')
            
            if col7.button("📍 Адрес", key=f"btn_lead_addr_{row['id']}"):
                st.session_state[f"show_addr_lead_{row['id']}"] = not st.session_state.get(f"show_addr_lead_{row['id']}", False)
            
            if st.session_state.get(f"show_addr_lead_{row['id']}", False):
                with st.expander(f"📍 Адреси за {row['name']} ({row['company'] or ''})", expanded=True):
                    l_addr = pd.read_sql(f"SELECT address_text as [Адрес], address_type as [Тип] FROM addresses WHERE lead_id = {row['id']}", engine)
                    if not l_addr.empty:
                        st.dataframe(l_addr, hide_index=True, use_container_width=True)
                    else:
                        st.info("Няма регистрирани адреси за този лийд.")

        st.divider()
        st.subheader("🚀 Конвертиране на Лийд в Клиент")
        leads_raw = pd.read_sql("SELECT id, name, last_name, company FROM leads", engine).values.tolist()
        lead_options = {f"{r[3] or ''} ({r[1]} {r[2] or ''})".strip().lstrip('(').rstrip(')'): r[0] for r in leads_raw}
        
        if lead_options:
            col_sel, col_conv = st.columns([3, 1])
            with col_sel:
                selected_lead_label = st.selectbox("Избери Лийд за конвертиране", list(lead_options.keys()), label_visibility="collapsed")
            with col_conv:
                if st.button("🚀 Конвертирай в Клиент", use_container_width=True):
                    lead_id = lead_options[selected_lead_label]
                    with engine.connect() as conn:
                        l_data = conn.execute(text("SELECT name, last_name, company, email, phone FROM leads WHERE id = :id"), {"id": lead_id}).fetchone()
                        if l_data:
                            res = conn.execute(
                                text("INSERT INTO clients (name, last_name, company, email, phone) VALUES (:name, :last_name, :company, :email, :phone) RETURNING id"),
                                {"name": l_data[0], "last_name": l_data[1], "company": l_data[2], "email": l_data[3], "phone": l_data[4]}
                            )
                            new_client_id = res.fetchone()[0]
                            conn.execute(text("UPDATE addresses SET client_id = :c_id, lead_id = NULL WHERE lead_id = :l_id"), {"c_id": new_client_id, "l_id": lead_id})
                            conn.execute(text("DELETE FROM leads WHERE id = :id"), {"id": lead_id})
                            conn.commit()
                    st.success("Лийдът е конвертиран успешно!")
                    st.rerun()
    else:
        st.info("Няма налични лийдове.")

elif menu == "👥 Клиенти":
    st.header("👥 Списък на Клиенти")
    clients_df = pd.read_sql("SELECT id, company, name, last_name, email, phone FROM clients ORDER BY id DESC", engine)
    
    if not clients_df.empty:
        c_comp, c_name, c_lname, c_email, c_phone, c_btn = st.columns([2, 1.5, 1.5, 2, 1.5, 1])
        c_comp.write("**Компания**")
        c_name.write("**Име**")
        c_lname.write("**Фамилия**")
        c_email.write("**Имейл**")
        c_phone.write("**Телефон**")
        c_btn.write("**Действие**")
        st.divider()

        for idx, row in clients_df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 2, 1.5, 1])
            col1.text(row['company'] or '')
            col2.text(row['name'] or '')
            col3.text(row['last_name'] or '')
            col4.text(row['email'] or '')
            col5.text(row['phone'] or '')
            
            if col6.button("📍 Адрес", key=f"btn_client_addr_{row['id']}"):
                st.session_state[f"show_addr_client_{row['id']}"] = not st.session_state.get(f"show_addr_client_{row['id']}", False)
            
            if st.session_state.get(f"show_addr_client_{row['id']}", False):
                with st.expander(f"📍 Адреси за {row['name']} ({row['company'] or ''})", expanded=True):
                    c_addr = pd.read_sql(f"SELECT address_text as [Адрес], address_type as [Тип] FROM addresses WHERE client_id = {row['id']}", engine)
                    if not c_addr.empty:
                        st.dataframe(c_addr, hide_index=True, use_container_width=True)
                    else:
                        st.info("Няма регистрирани адреси за този клиент.")
    else:
        st.info("Няма регистрирани клиенти.")

elif menu == "📍 Адреси":
    st.header("📍 Управление на Адреси")
    
    leads = pd.read_sql("SELECT id, name, last_name, company FROM leads", engine).values.tolist()
    clients = pd.read_sql("SELECT id, name, last_name, company FROM clients", engine).values.tolist()
    
    target_options = {}
    for l in leads: 
        lbl = f"🎯 Лийд: {l[3]} ({l[1]} {l[2] or ''})".strip().rstrip(')') if l[3] else f"🎯 Лийд: {l[1]} {l[2] or ''}".strip()
        target_options[lbl] = ('lead', l[0])
    for c in clients: 
        lbl = f"👥 Клиент: {c[3]} ({c[1]} {c[2] or ''})".strip().rstrip(')') if c[3] else f"👥 Клиент: {c[1]} {c[2] or ''}".strip()
        target_options[lbl] = ('client', c[0])

    with st.expander("➕ Добави нов Адрес"):
        with st.form("add_address_form"):
            if target_options:
                selected_target = st.selectbox("Избери Лийд или Клиент *", list(target_options.keys()))
            else:
                st.text_input("Избери Лийд или Клиент", value="Няма налични записи", disabled=True)
                selected_target = None
            
            col_addr, col_type = st.columns([3, 1])
            with col_addr: address_text = st.text_input("Адрес (улица, №, град) *")
            with col_type: address_type = st.selectbox("Тип адрес", ["Основен", "За кореспонденция", "Друг"])
                
            submit_addr = st.form_submit_button("Запази Адрес")
            if submit_addr and address_text and selected_target:
                t_type, t_id = target_options[selected_target]
                lead_id = t_id if t_type == 'lead' else None
                client_id = t_id if t_type == 'client' else None
                
                with engine.connect() as conn:
                    conn.execute(
                        text("INSERT INTO addresses (address_text, address_type, lead_id, client_id) VALUES (:addr, :type, :l_id, :c_id)"),
                        {"addr": address_text, "type": address_type, "l_id": lead_id, "c_id": client_id}
                    )
                    conn.commit()
                st.success("Адресът е добавен успешно!")
                st.rerun()

    st.subheader("📝 Списък на Адреси")
    addresses_df = pd.read_sql("""
        SELECT a.id, a.address_text as [Адрес], a.address_type as [Тип],
               COALESCE(c.company, l.company, c.name, l.name) as [Свързан обект]
        FROM addresses a
        LEFT JOIN clients c ON a.client_id = c.id
        LEFT JOIN leads l ON a.lead_id = l.id
    """, engine)

    if not addresses_df.empty:
        st.dataframe(addresses_df, hide_index=True, use_container_width=True)
    else:
        st.info("Няма намерени адреси.")

elif menu == "💰 Сделки":
    st.header("💰 Управление на Сделки")
    clients = pd.read_sql("SELECT id, name, last_name, company FROM clients", engine).values.tolist()
    client_options = {f"{c[3] or ''} ({c[1]} {c[2] or ''})".strip().lstrip('(').rstrip(')'): c[0] for c in clients} if clients else {}

    with st.expander("➕ Създай нова Сделка"):
        if not client_options:
            st.warning("⚠️ Първо трябва да имаш регистриран Клиент!")
        with st.form("add_deal_form"):
            title = st.text_input("Име/Предмет на сделката")
            amount = st.number_input("Сума (BGN)", min_value=0.0, step=100.0)
            stage = st.selectbox("Етап", ["В преговори", "Изпратена оферта", "Спечелена", "Загубена"])
            selected_client = st.selectbox("Избери Клиент/Фирма", list(client_options.keys())) if client_options else None
            
            submit_deal = st.form_submit_button("Създай Сделка")
            if submit_deal and title:
                client_id = client_options[selected_client] if selected_client else None
                with engine.connect() as conn:
                    conn.execute(
                        text("INSERT INTO deals (title, amount, stage, client_id) VALUES (:title, :amount, :stage, :c_id)"),
                        {"title": title, "amount": amount, "stage": stage, "c_id": client_id}
                    )
                    conn.commit()
                st.success("Сделката е създадена!")
                st.rerun()

    deals_df = pd.read_sql("SELECT title as [Предмет на сделката], amount as [Сума (BGN)], stage as [Етап] FROM deals", engine)
    if not deals_df.empty:
        st.dataframe(deals_df, hide_index=True, use_container_width=True)
    else:
        st.info("Няма налични сделки.")

elif menu == "📅 Срещи":
    st.header("📅 График и Бележки от Срещи")
    meetings_df = pd.read_sql("SELECT meeting_date as [Дата], company as [Компания], contact_name as [Лице за контакт], notes as [Бележки] FROM meetings ORDER BY meeting_date DESC", engine)
    if not meetings_df.empty:
        st.dataframe(meetings_df, hide_index=True, use_container_width=True)
    else:
        st.info("Няма регистрирани срещи.")