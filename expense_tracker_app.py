import streamlit as st
import sqlite3
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# --- DATABASE SETUP ---
conn = sqlite3.connect("budget_app.db", check_same_thread=False)
c = conn.cursor()

# Create tables if not exist
c.execute('''CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                name TEXT,
                category TEXT,
                amount REAL,
                date TEXT)''')
conn.commit()

# ---- MIGRATION: ensure 'name' column exists for older databases ----
c.execute("PRAGMA table_info(expenses)")
cols = [row[1] for row in c.fetchall()]
if "name" not in cols:
    c.execute("ALTER TABLE expenses ADD COLUMN name TEXT")
    conn.commit()

# --- FUNCTIONS ---
def add_user(username, password):
    c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

def add_expense(username, name, category, amount, date):
    c.execute("INSERT INTO expenses (username, name, category, amount, date) VALUES (?, ?, ?, ?, ?)",
              (username, name, category, amount, date))
    conn.commit()

def get_expenses(username):
    c.execute("SELECT id, name, category, amount, date FROM expenses WHERE username=?", (username,))
    return c.fetchall()

def delete_expense(expense_id):
    c.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    conn.commit()

# --- APP START ---
st.title("💰 Budget Tracker")

# --- LOGIN / SIGNUP ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.subheader("Login to continue")

    choice = st.radio("Account:", ["Login", "Sign Up"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.button("Create Account"):
            add_user(username, password)
            st.success("Account created! Please log in.")

    elif choice == "Login":
        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome {username} 👋")
            else:
                st.error("Invalid Username/Password")

else:
    # --- MAIN DASHBOARD ---
    st.sidebar.header(f"Welcome, {st.session_state.username}")

    # Budget input on sidebar
    budget = st.sidebar.number_input("Set your Budget", min_value=0.0, step=100.0)

    st.subheader("➕ Add an Expense")
    name = st.text_input("Expense Name")
    category = st.selectbox("Category", ["Food", "Transport", "Entertainment", "Bills", "Other"])
    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
    date = st.date_input("Date", datetime.date.today())

    if st.button("Add Expense"):
        if name.strip() and amount > 0:
            add_expense(st.session_state.username, name, category, amount, str(date))
            st.success(f"Expense '{name}' added!")
        else:
            st.warning("⚠️ Please enter a valid name and amount")

    # Show expense history
    expenses = get_expenses(st.session_state.username)
    if expenses:
        st.subheader("📊 Your Expenses")
        df = pd.DataFrame(expenses, columns=["ID", "Name", "Category", "Amount", "Date"])

        # Display clean table without IDs
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True)

        # Delete section below the table
        delete_id = st.selectbox("Select an expense to delete", df["ID"],
                                 format_func=lambda x: f"{df.loc[df['ID']==x, 'Name'].values[0]} - ₹{df.loc[df['ID']==x, 'Amount'].values[0]}")
        if st.button("❌ Delete Selected Expense"):
            delete_expense(delete_id)
            st.success("Expense deleted successfully!")
            st.rerun()

        # Show total spent
        total_spent = df["Amount"].sum()
        st.metric("Total Spent", f"₹{total_spent}")
        st.metric("Remaining Budget", f"₹{budget - total_spent}")

        # Graphs
        st.subheader("📈 Expense Analysis")
        st.bar_chart(df.groupby("Category")["Amount"].sum())

        # Pie chart for category split
        st.subheader("📊 Category Distribution")
        # Correctly plot the pie chart using matplotlib and st.pyplot
        category_amounts = df.groupby("Category")["Amount"].sum()
        fig, ax = plt.subplots()
        category_amounts.plot.pie(ax=ax, autopct="%1.1f%%")
        ax.set_ylabel('') # Hides the 'Amount' label on the y-axis
        st.pyplot(fig)


        # Line chart for expenses over time
        st.subheader("📅 Spending Over Time")
        df["Date"] = pd.to_datetime(df["Date"])
        st.line_chart(df.groupby("Date")["Amount"].sum())

        # Download button
        st.download_button(
            label="⬇️ Download Expenses as CSV",
            data=df.to_csv(index=False),
            file_name="expenses.csv",
            mime="text/csv"
        )

        # Filter by category
        category_filter = st.selectbox("Filter by Category", df["Category"].unique())
        filtered_df = df[df["Category"] == category_filter]
        st.write("Filtered Expenses:", filtered_df)
