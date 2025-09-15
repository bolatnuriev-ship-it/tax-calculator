import streamlit as st

def tax_calculator(income, rate=0.10):
    return income * rate

st.title("💰 Налоговый калькулятор для ИП")

income = st.number_input("Введите ваш доход (тенге):", min_value=0.0, step=1000.0)

tax_mode = st.selectbox(
    "Выберите налоговый режим:",
    ("УСН (10%)", "ОСН (20%)", "СНР (3%)")
)

if tax_mode == "УСН (10%)":
    rate = 0.10
elif tax_mode == "ОСН (20%)":
    rate = 0.20
else:
    rate = 0.03

if income > 0:
    tax = tax_calculator(income, rate)
    st.write(f"**Доход:** {income:,.2f} ₸")
    st.write(f"**Ставка налога:** {rate*100:.0f}%")
    st.write(f"**Налог:** {tax:,.2f} ₸")
    st.write(f"**Доход после налога:** {income - tax:,.2f} ₸")
    