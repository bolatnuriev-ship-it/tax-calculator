# app2.py
import streamlit as st
import pandas as pd

# --- Константы ---
LIMIT_SNR_MONTH = 1_300_000       # лимит в месяц для СНР (~300 МРП)
LIMIT_SNR_YEAR = 2_500_000_000    # лимит в год для СНР

# --- Функции расчета ---
def calculate_deductions(salaries):
    """Расчёт удержаний и начислений по зарплатам"""
    deductions = {}
    
    # --- Удержания с работника ---
    deductions["ОПВ (10%)"] = salaries * 0.10
    deductions["ОСМС (2%)"] = salaries * 0.02
    taxable_base = salaries - deductions["ОПВ (10%)"] - deductions["ОСМС (2%)"]
    deductions["ИПН (10% от базы)"] = taxable_base * 0.10

    # --- Начисления работодателя ---
    deductions["СО (3.5%)"] = salaries * 0.035
    deductions["ОСМС раб. (3%)"] = salaries * 0.03
    deductions["Соцналог (9.5%)"] = salaries * 0.095
    deductions["ОС НС (0.5%)"] = salaries * 0.005

    total = sum(deductions.values())
    return deductions, total


def calculate_taxes(entity, mode, income_year, salaries_year, expenses_year, amortization):
    """Расчёт налогов по выбранному режиму с учётом всех удержаний"""
    details = {}
    warnings = []

    # --- Удержания и начисления ---
    salary_deductions, salary_total = calculate_deductions(salaries_year)
    details.update(salary_deductions)

    # --- База для налогообложения прибыли ---
    profit_base = income_year - expenses_year - amortization - salaries_year

    # --- Режимы ---
    if mode == "snr_individual":
        if salaries_year > 0:
            warnings.append("⚠️ СНР неприменим для физлица с сотрудниками.")
        if income_year / 12 > LIMIT_SNR_MONTH:
            warnings.append("⚠️ Доход превышает лимит для СНР (~1,3 млн ₸ в месяц).")
        if income_year > LIMIT_SNR_YEAR:
            warnings.append("⚠️ Доход превышает лимит для СНР (2,5 млрд ₸ в год).")
        tax = income_year * 0.04
        details["Единый налог (4%)"] = tax
        total_tax = tax

    elif mode == "snr_ip_too_kh":
        if income_year / 12 > LIMIT_SNR_MONTH:
            warnings.append("⚠️ Внимание!!! Доход превышает лимит для СНР (~1,3 млн ₸ в месяц).")
        if income_year > LIMIT_SNR_YEAR:
            warnings.append("⚠️ Внимание!!! Доход превышает лимит для СНР (2,5 млрд ₸ в год).")
        tax = income_year * 0.04
        details["Единый налог (4%)"] = tax
        total_tax = tax + salary_total

    elif mode == "general_ip":
        if profit_base <= 0:
            profit_tax = 0
            warnings.append("⚠️ У вас убыток, налог на прибыль не взимается.")
        else:
            profit_tax = profit_base * 0.10
        details["Налог на прибыль (10%)"] = profit_tax
        total_tax = profit_tax + salary_total

    elif mode == "general_too":
        if profit_base <= 0:
            profit_tax = 0
            warnings.append("⚠️ У вас убыток, налог на прибыль не взимается.")
        else:
            profit_tax = profit_base * 0.20
        details["КПН (20%)"] = profit_tax
        total_tax = profit_tax + salary_total

    else:
        total_tax, details = 0, {}

    after_tax_income = income_year - total_tax - expenses_year - salaries_year - amortization
    return total_tax, after_tax_income, details, warnings


# --- Streamlit UI ---
def main():
    st.set_page_config(page_title="Налоговый калькулятор 2.0", page_icon="📊", layout="centered")

    st.title("📊 Налоговый калькулятор Казахстан 2.0")
    st.markdown("Расчёт налоговой нагрузки с детализацией всех удержаний и начислений.")

    # --- Ввод данных ---
    st.header("🔹 Ввод данных")

    entity_choice = st.radio(
        "Кто вы?",
        ["Физическое лицо (individual)", "ИП", "ТОО / Компания", "Крестьянское хозяйство (КХ)"]
    )

    entity_map = {
        "Физическое лицо (individual)": "individual",
        "ИП": "ip",
        "ТОО / Компания": "too",
        "Крестьянское хозяйство (КХ)": "kh"
    }
    entity = entity_map[entity_choice]

    has_employees = st.radio("Есть ли у вас сотрудники?", ["Нет", "Да"]) == "Да"

    income = st.number_input("Введите доход:", min_value=0.0, step=1000.0, format="%.2f")
    salaries, expenses, amortization = 0, 0, 0
    if entity in ["ip", "too"] or has_employees:
        salaries = st.number_input("Введите фонд зарплаты сотрудников за период:", min_value=0.0, step=1000.0, format="%.2f")
        expenses = st.number_input("Введите расходы (кроме зарплат):", min_value=0.0, step=1000.0, format="%.2f")
        amortization = st.number_input("Введите амортизацию:", min_value=0.0, step=1000.0, format="%.2f")

    period_choice = st.radio("За какой период данные?", ["В месяц", "В год"])

    # --- Доступные режимы ---
    available_modes = []
    if entity == "individual":
        if not has_employees:
            available_modes.append(("СНР — самозанятые (4%)", "snr_individual"))
    elif entity in ["ip", "too", "kh"]:
        available_modes.append(("СНР — упрощённый/розничный (4%)", "snr_ip_too_kh"))
        if entity == "ip":
            available_modes.append(("Общий режим — ИП (10%)", "general_ip"))
        elif entity == "too":
            available_modes.append(("Общий режим — ТОО (КПН 20%)", "general_too"))

    if not available_modes:
        st.error("⚠️ Для вашего типа и условий нет доступных режимов.")
        st.stop()

    mode_desc = st.selectbox("Выберите налоговый режим:", [desc for desc, _ in available_modes])
    mode_key = dict(available_modes)[mode_desc]

    if st.button("🔎 Рассчитать"):
        # Пересчёт в год
        if period_choice == "В месяц":
            income *= 12
            salaries *= 12
            expenses *= 12
            amortization *= 12

        total_tax, after_tax_income, details, warnings = calculate_taxes(entity, mode_key, income, salaries, expenses, amortization)

        st.header("📌 Результат")
        col1, col2 = st.columns(2)
        col1.metric("Совокупный налог", f"{total_tax:,.2f} ₸")
        col2.metric("Доход после налогов", f"{after_tax_income:,.2f} ₸")

        st.subheader("📊 Детализация")
        df = pd.DataFrame(list(details.items()), columns=["Платёж", "Сумма, ₸"])
        st.table(df)

        for w in warnings:
            st.warning(w)


if __name__ == "__main__":
    main()
