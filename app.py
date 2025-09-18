# app.py
import streamlit as st
import pandas as pd

# --- Константы ---
LIMIT_SNR_MONTH = 1_300_000       # месячный лимит для СНР (≈300 МРП)
LIMIT_SNR_YEAR = 2_500_000_000    # годовой лимит для СНР (~2.5 млрд тг)


# --- Функции ---
def calculate_taxes(entity, mode, income_year, salaries_year, expenses_year):
    """Расчёт налогов по выбранному режиму"""
    tax = 0
    warnings = []
    after_tax_income = income_year

    if mode == "snr_individual":
        if salaries_year > 0:
            warnings.append("⚠️ СНР неприменим для физлица с сотрудниками.")
        if income_year / 12 > LIMIT_SNR_MONTH:
            warnings.append("⚠️ Доход превышает лимит для СНР (~1,3 млн ₸ в месяц).")
        if income_year > LIMIT_SNR_YEAR:
            warnings.append("⚠️ Доход превышает лимит для СНР (2,5 млрд ₸ в год).")
        tax = income_year * 0.04
        after_tax_income = income_year - tax

    elif mode == "snr_ip_too_kh":
        if income_year / 12 > LIMIT_SNR_MONTH:
            warnings.append("⚠️ Внимание!!! Доход превышает лимит для СНР (~1,3 млн ₸ в месяц).")
        if income_year > LIMIT_SNR_YEAR:
            warnings.append("⚠️ Внимание!!! Доход превышает лимит для СНР (2,5 млрд ₸ в год).")
        tax = income_year * 0.04
        after_tax_income = income_year - tax - salaries_year

    elif mode == "general_ip":
        profit = income_year - expenses_year - salaries_year
        if profit <= 0:
            tax = 0
            warnings.append("⚠️ У вас убыток, налог на прибыль не взимается.")
        else:
            tax = profit * 0.10
        after_tax_income = income_year - expenses_year - salaries_year - tax

    elif mode == "general_too":
        profit = income_year - expenses_year - salaries_year
        if profit <= 0:
            tax = 0
            warnings.append("⚠️ У вас убыток, налог на прибыль не взимается.")
        else:
            tax = profit * 0.20
        after_tax_income = income_year - expenses_year - salaries_year - tax

    return tax, after_tax_income, warnings


# --- Streamlit UI ---
def main():
    st.set_page_config(page_title="Налоговый калькулятор", page_icon="📊", layout="centered")

    st.title("📊 Налоговый калькулятор Казахстан")
    st.markdown("Простой инструмент для расчёта налоговой нагрузки в разных режимах.")

    # --- Ввод данных ---
    st.header("🔹 Ввод данных")

    entity_choice = st.radio(
        "Кто вы?",
        ["Физическое лицо (individual)", "Индивидуальный предприниматель (ИП)", 
         "ТОО / Компания", "Крестьянское хозяйство (КХ)"]
    )

    entity_map = {
        "Физическое лицо (individual)": "individual",
        "Индивидуальный предприниматель (ИП)": "ip",
        "ТОО / Компания": "too",
        "Крестьянское хозяйство (КХ)": "kh"
    }
    entity = entity_map[entity_choice]

    has_employees = st.radio("Есть ли у вас наёмные сотрудники?", ["Нет", "Да"]) == "Да"

    income = st.number_input("Введите доход:", min_value=0.0, step=1000.0, format="%.2f")

    salaries, expenses = 0, 0
    if entity in ["ip", "too"] or has_employees:
        salaries = st.number_input("Введите общую сумму зарплат сотрудников за период:", min_value=0.0, step=1000.0, format="%.2f")
        expenses = st.number_input("Введите расходы за период:", min_value=0.0, step=1000.0, format="%.2f")

    period_choice = st.radio("За какой период введены данные?", ["В месяц", "В год"])

    if st.button("🔎 Рассчитать"):
        # --- Пересчёт в годовые значения ---
        if period_choice == "В месяц":
            income *= 12
            salaries *= 12
            expenses *= 12

        # --- Доступные режимы ---
        available_modes = []
        if entity == "individual":
            if not has_employees:
                available_modes.append(("СНР — Специальный налоговый режим (самозанятые, 4%)", "snr_individual"))
        elif entity in ["ip", "too", "kh"]:
            available_modes.append(("СНР — Специальный налоговый режим (упрощённый/розничный, 4%)", "snr_ip_too_kh"))
            if entity == "ip":
                available_modes.append(("Общий режим — ИП (налог на прибыль 10%)", "general_ip"))
            elif entity == "too":
                available_modes.append(("Общий режим — ТОО (КПН 20%)", "general_too"))

        # фильтрация СНР по лимиту
        if income > LIMIT_SNR_YEAR:
            available_modes = [m for m in available_modes if not m[1].startswith("snr")]

        if not available_modes:
            st.error("⚠️ Для вашего типа и дохода нет доступных режимов.")
            return

        # выбор режима
        mode_desc = st.selectbox("Выберите налоговый режим:", [desc for desc, _ in available_modes])
        mode_key = dict(available_modes)[mode_desc]

        # --- Расчёт ---
        tax, after_tax_income, warnings = calculate_taxes(entity, mode_key, income, salaries, expenses)

        st.header("📌 Результат расчёта")

        col1, col2 = st.columns(2)
        col1.metric("Налог", f"{tax:,.2f} ₸")
        col2.metric("Доход после налогов", f"{after_tax_income:,.2f} ₸")

        for w in warnings:
            st.warning(w)

        # --- Подсказки и сравнения ---
        if len(available_modes) > 1:
            st.subheader("💡 Сравнение налоговой нагрузки и чистого дохода")

            results = []
            for desc, alt_mode in available_modes:
                alt_tax, alt_after, _ = calculate_taxes(entity, alt_mode, income, salaries, expenses)
                results.append({"Режим": desc, "Налог (₸)": alt_tax, "Чистый доход (₸)": alt_after})

            df = pd.DataFrame(results)

            st.markdown("**Сравнение налогов по режимам:**")
            st.bar_chart(df.set_index("Режим")["Налог (₸)"])

            st.markdown("**Сравнение чистого дохода по режимам:**")
            st.bar_chart(df.set_index("Режим")["Чистый доход (₸)"])

            # текстовые подсказки
            for row in results:
                if row["Режим"] != mode_desc and row["Налог (₸)"] < tax:
                    st.info(f"👉 По режиму «{row['Режим']}» налог был бы меньше: **{row['Налог (₸)']:,.2f} ₸**")
                if row["Режим"] != mode_desc and row["Чистый доход (₸)"] > after_tax_income:
                    st.success(f"💰 По режиму «{row['Режим']}» чистый доход был бы больше: **{row['Чистый доход (₸)']:,.2f} ₸**")


if __name__ == "__main__":
    main()
