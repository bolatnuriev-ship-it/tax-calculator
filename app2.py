# app2.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Налоговый калькулятор 2.1", page_icon="📊", layout="centered")

# --- Константы ---
LIMIT_SNR_MONTH = 1_300_000       # месячный лимит для СНР (~1.3M)
LIMIT_SNR_YEAR = 16_000_000       # годовой лимит для СНР (~16M) - ориентировочно
# (в коде используем оба лимита; при изменениях законов поправь значения)

# социальные ставки (можно вынести в конфиг)
RATE_OPV = 0.10         # ОПВ (удержание с работника)
RATE_OSMS_EMP = 0.02    # ОСМС (удержание с работника)
RATE_IPN = 0.10         # ИПН (условно 10% от базы)
RATE_SO = 0.035         # СО (начисление работодателя)
RATE_OSMS_ER = 0.03     # ОСМС (работодателя)
RATE_SOC_TAX = 0.095    # Социальный налог (примерно)
RATE_OS_NS = 0.005      # ОС НС (0.5% как пример)

# налоговые ставки режимов
RATE_SNR = 0.04
RATE_IP_GENERAL = 0.10
RATE_TOO_KPN = 0.20

# --- Вспомогательные функции ---
def to_annual(value, period_choice):
    """Пересчитать в годовые значения в зависимости от периода."""
    try:
        if period_choice == "В месяц":
            return value * 12
        else:
            return value
    except:
        return 0.0

def money(x):
    return f"{x:,.2f} ₸"

def calc_salary_items(salaries_annual):
    """Возвращает словарь удержаний (employee) и начислений (employer) и суммарные суммы.
       Important: IPN - удержание сотрудника, не включаем в налог компании, но показываем."""
    emp = {}
    er = {}
    emp["ОПВ (10%)"] = salaries_annual * RATE_OPV
    emp["ОСМС (удержание, 2%)"] = salaries_annual * RATE_OSMS_EMP
    # налог на доходы физлиц (удержание, показываем отдельно)
    taxable_base_for_ipn = max(0.0, salaries_annual - emp["ОПВ (10%)"] - emp["ОСМС (удержание, 2%)"])
    emp["ИПН (10% от базы)"] = taxable_base_for_ipn * RATE_IPN

    er["СО (3.5%)"] = salaries_annual * RATE_SO
    er["ОСМС (работодатель, 3%)"] = salaries_annual * RATE_OSMS_ER
    er["Соцналог (9.5%)"] = salaries_annual * RATE_SOC_TAX
    er["ОС НС (0.5%)"] = salaries_annual * RATE_OS_NS

    emp_total = sum(emp.values())
    er_total = sum(er.values())
    return emp, er, emp_total, er_total

def compute_mode_tax(mode_key, income_annual, salaries_annual, expenses_considered, amortization_annual):
    """Вычисляет налог по выбранному режиму и возвращает (mode_tax, taxable_base, warnings)."""
    warnings = []
    taxable_base = 0.0
    mode_tax = 0.0

    if mode_key == "snr_individual":
        # СНР для физлица (самозанятый)
        if salaries_annual > 0:
            warnings.append("⚠️ СНР неприменим для физлица с сотрудниками.")
        if income_annual / 12 > LIMIT_SNR_MONTH:
            warnings.append("⚠️ Доход превышает месячный лимит СНР (~1.3M).")
        if income_annual > LIMIT_SNR_YEAR:
            warnings.append("⚠️ Доход превышает годовой лимит СНР (~16M).")
        mode_tax = income_annual * RATE_SNR
        taxable_base = income_annual  # for display purpose

    elif mode_key == "snr_ip_too_kh":
        if income_annual / 12 > LIMIT_SNR_MONTH:
            warnings.append("⚠️ Доход превышает месячный лимит СНР (~1.3M).")
        if income_annual > LIMIT_SNR_YEAR:
            warnings.append("⚠️ Доход превышает годовой лимит СНР (~16M).")
        mode_tax = income_annual * RATE_SNR
        taxable_base = income_annual

    elif mode_key == "general_ip":
        # прибыль = доход - расходы_considered - salaries - amortization
        profit = income_annual - expenses_considered - salaries_annual - amortization_annual
        taxable_base = max(0.0, profit)
        if profit <= 0:
            mode_tax = 0.0
            warnings.append("⚠️ Прибыль отрицательная или нулевая — налог на прибыль = 0.")
        else:
            mode_tax = profit * RATE_IP_GENERAL

    elif mode_key == "general_too":
        profit = income_annual - expenses_considered - salaries_annual - amortization_annual
        taxable_base = max(0.0, profit)
        if profit <= 0:
            mode_tax = 0.0
            warnings.append("⚠️ Прибыль отрицательная или нулевая — КПН = 0.")
        else:
            mode_tax = profit * RATE_TOO_KPN

    else:
        mode_tax = 0.0
        taxable_base = 0.0

    return mode_tax, taxable_base, warnings

# --- Streamlit UI ---
def main():
    st.title("📊 Налоговый калькулятор — расширенная версия")
    st.markdown(
        "Детализированный расчёт налоговой нагрузки. "
        "Поля расходов — необязательные: бухгалтер может отметить, какие расходы учитывать как вычеты. "
        "IPN сотрудников показывается как удержание (информативно), но **не** включается в налоговую нагрузку компании."
    )

    st.header("🔹 Ввод данных")
    col1, col2 = st.columns([1, 1])

    with col1:
        entity_choice = st.selectbox("Кто вы?", ["Физическое лицо (individual)", "ИП", "TOO / Компания", "Крестьянское хозяйство (КХ)"])
        entity_map = {
            "Физическое лицо (individual)": "individual",
            "ИП": "ip",
            "TOO / Компания": "too",
            "Крестьянское хозяйство (КХ)": "kh"
        }
        entity = entity_map[entity_choice]

        has_employees = st.radio("Есть ли у вас сотрудники?", ["Нет", "Да"]) == "Да"

        period_choice = st.radio("За какой период данные?", ["В месяц", "В год"])

    with col2:
        income = st.number_input("Введите доход:", min_value=0.0, step=1000.0, format="%.2f", value=0.0)
        salaries = st.number_input("Введите фонд зарплаты сотрудников за период:", min_value=0.0, step=1000.0, format="%.2f", value=0.0) if (entity in ["ip", "too", "kh"] or has_employees) else 0.0
        amortization = st.number_input("Введите амортизацию (перечень/сумма):", min_value=0.0, step=100.0, format="%.2f", value=0.0) if (entity in ["ip", "too", "kh"] or has_employees) else 0.0

    st.markdown("---")
    st.subheader("📋 Расходы (необязательные — бухгалтер отмечает, что учитывать)")

    # Expense categories with checkboxes
    exp_cols = st.columns(3)
    with exp_cols[0]:
        use_rent = st.checkbox("Учитывать аренду?", value=True)
        rent = st.number_input("Аренда:", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_rent else 0.0
    with exp_cols[1]:
        use_materials = st.checkbox("Учитывать материалы?", value=True)
        materials = st.number_input("Материалы:", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_materials else 0.0
    with exp_cols[2]:
        use_services = st.checkbox("Учитывать услуги подрядчиков?", value=True)
        services = st.number_input("Услуги:", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_services else 0.0

    exp_cols2 = st.columns(3)
    with exp_cols2[0]:
        use_travel = st.checkbox("Учитывать командировочные?", value=False)
        travel = st.number_input("Командировочные:", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_travel else 0.0
    with exp_cols2[1]:
        use_interest = st.checkbox("Учитывать проценты по кредитам?", value=False)
        interest = st.number_input("Проценты по кредитам:", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_interest else 0.0
    with exp_cols2[2]:
        use_other = st.checkbox("Учитывать прочие расходы?", value=False)
        other = st.number_input("Прочие:", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_other else 0.0

    # always show explicit "штрафы и пени" but disabled by default and warn
    st.caption("⚠️ Штрафы и пени обычно не принимаются к вычету.")
    use_penalties = st.checkbox("Есть штрафы/пени (показывать, но не учитывать)?", value=False)
    penalties = st.number_input("Штрафы/пени (указываются для информации):", min_value=0.0, step=100.0, format="%.2f", value=0.0) if use_penalties else 0.0

    st.markdown("---")

    # Choose mode(s) available (we will compute all and then mark availability)
    st.subheader("🔧 Режим налогообложения (выберите для расчёта)")
    modes_user = st.multiselect("Отметьте режимы, которые хотите сравнить (можно несколько):",
                                ["СНР — самозанятые (4%)", "СНР — упрощёнка/розница (4%)",
                                 "Общий режим — ИП (10%)", "Общий режим — ТОО (КПН 20%)"],
                                default=["СНР — упрощёнка/розница (4%)", "Общий режим — ТОО (КПН 20%)"])
    # Map to internal keys
    mode_map = {
        "СНР — самозанятые (4%)": "snr_individual",
        "СНР — упрощёнка/розница (4%)": "snr_ip_too_kh",
        "Общий режим — ИП (10%)": "general_ip",
        "Общий режим — ТОО (КПН 20%)": "general_too"
    }
    selected_modes = [mode_map[m] for m in modes_user]

    # ACTION: Calculate (button)
    if st.button("🔎 Рассчитать"):
        # --- Пересчёт в годовые значения корректно ---
        income_annual = to_annual(income, period_choice)
        salaries_annual = to_annual(salaries, period_choice)
        amortization_annual = to_annual(amortization, period_choice)

        # Build expenses_considered based on checkboxes
        expenses_components = {}
        if use_rent:
            expenses_components["Аренда"] = to_annual(rent, period_choice)
        if use_materials:
            expenses_components["Материалы"] = to_annual(materials, period_choice)
        if use_services:
            expenses_components["Услуги подрядчиков"] = to_annual(services, period_choice)
        if use_travel:
            expenses_components["Командировочные"] = to_annual(travel, period_choice)
        if use_interest:
            expenses_components["Проценты по кредитам"] = to_annual(interest, period_choice)
        if use_other:
            expenses_components["Прочие расходы"] = to_annual(other, period_choice)
        # penalties shown but not included
        expenses_sum = sum(expenses_components.values())

        # salary items
        emp_items, er_items, emp_total, er_total = calc_salary_items(salaries_annual)

        # For each mode compute taxes (we compute all to compare)
        results = []
        mode_infos = {}
        for mk in ["snr_individual", "snr_ip_too_kh", "general_ip", "general_too"]:
            mode_tax, taxable_base, warnings = compute_mode_tax(mk, income_annual, salaries_annual, expenses_sum, amortization_annual)
            # company_total_tax: include ONLY employer contributions + mode_tax (do not include IPN)
            company_total_tax = mode_tax + er_total
            # company_total_liability_for_display: also optionally show employee withholdings separately
            mode_infos[mk] = {
                "mode_tax": mode_tax,
                "taxable_base": taxable_base,
                "warnings": warnings,
                "company_total_tax": company_total_tax,
                "employee_withholdings_total": emp_total,
                "employer_contributions_total": er_total
            }

        # Build display: choose which modes to show (those user selected)
        display_results = []
        for mk in selected_modes:
            info = mode_infos[mk]
            # availability check for SNR:
            available = True
            reason = ""
            if mk in ("snr_individual", "snr_ip_too_kh"):
                if income_annual / 12 > LIMIT_SNR_MONTH:
                    available = False
                    reason = f"доход (в мес.) {income_annual/12:,.2f} ₸ > лимит {LIMIT_SNR_MONTH:,.2f} ₸"
                if income_annual > LIMIT_SNR_YEAR:
                    available = False
                    reason = f"доход (в год.) {income_annual:,.2f} ₸ > лимит {LIMIT_SNR_YEAR:,.2f} ₸"
                if mk == "snr_individual" and salaries_annual > 0:
                    available = False
                    reason = "в самозанятых нельзя иметь сотрудников"
            # for general modes, typically available
            display_results.append((mk, info, available, reason))

        # --- Primary result: show detailed breakdown for chosen primary mode (first in selected_modes) ---
        primary = selected_modes[0] if selected_modes else None
        if primary is None:
            st.error("Выберите хотя бы один режим для расчёта.")
            st.stop()

        info = mode_infos[primary]
        # Company tax (exclude IPN), employee withholdings shown separately
        company_tax = info["company_total_tax"]
        emp_with = info["employee_withholdings_total"]
        er_contrib = info["employer_contributions_total"]
        mode_tax = info["mode_tax"]
        taxable_base = info["taxable_base"]
        warnings = info["warnings"]

        # Compute net income after taxes for company perspective:
        # note: Net = income - expenses_sum - salaries - amortization - company_tax
        net_after_taxes = income_annual - expenses_sum - salaries_annual - amortization_annual - company_tax

        # Output top metrics
        st.header("📌 Результат")
        col_a, col_b = st.columns(2)
        col_a.metric("Совокупный налог (для компании)", money(company_tax))
        col_b.metric("Доход после налогов (для компании)", money(net_after_taxes))

        # Show immediate warnings
        for w in warnings:
            st.warning(w)

        # Detailed breakdown: Deductions -> Tax base -> Taxes -> Contributions
        st.subheader("🔍 Детализация расчёта (пошагово)")

        # DEDUCTIONS block (visible)
        ded_rows = []
        ded_rows.append(("Доход (валовой)", money(income_annual)))
        ded_rows.append(("Вычеты: фонд зарплаты (ФОТ)", money(salaries_annual)))
        # list expense components
        for k, v in expenses_components.items():
            ded_rows.append((f"Вычеты: {k}", money(v)))
        ded_rows.append(("Вычеты: амортизация", money(amortization_annual)))
        ded_rows.append(("Итого вычеты (зарплаты + расходы + амортизация)", money(salaries_annual + expenses_sum + amortization_annual)))
        # taxable base (for profit taxes)
        if primary in ("general_ip", "general_too"):
            ded_rows.append(("Налогооблагаемая база (прибыль)", money(taxable_base)))
        else:
            ded_rows.append(("Налогооблагаемая база (для режима)", money(taxable_base)))

        df_ded = pd.DataFrame(ded_rows, columns=["Позиция", "Сумма"])
        st.table(df_ded)

        # Salary-related items (two groups: удержания сотрудников и начисления работодателя)
        st.subheader("🧾 Удержания сотрудников (информативно)")
        emp_list = [(k, money(v)) for k, v in emp_items.items()]
        df_emp = pd.DataFrame(emp_list, columns=["Удержание (сотрудник)", "Сумма"])
        st.table(df_emp)
        st.caption("ИПН удерживается у сотрудника и перечисляется работодателем, но не увеличивает налоговую нагрузку компании (показывается для прозрачности).")

        st.subheader("🏢 Начисления работодателя (нагрузка компании)")
        er_list = [(k, money(v)) for k, v in er_items.items()]
        df_er = pd.DataFrame(er_list, columns=["Начисление (работодатель)", "Сумма"])
        st.table(df_er)

        # Mode tax and company totals
        st.subheader("💸 Налоги по режиму и итоговые обязательства")
        main_rows = []
        main_rows.append(("Налог по режиму", money(mode_tax)))
        main_rows.append(("Начисления работодателя (итого)", money(er_contrib)))
        main_rows.append(("Совокупная сумма обязательств (компания)", money(company_tax)))
        main_rows.append(("Удержания сотрудников (итого, информативно)", money(emp_with)))
        df_main = pd.DataFrame(main_rows, columns=["Позиция", "Сумма"])
        st.table(df_main)

        # Consistency check
        st.subheader("🔁 Проверка консистентности")
        calc_net = income_annual - (salaries_annual + expenses_sum + amortization_annual + company_tax)
        st.write(f"Чистый доход (проверка) = Доход - (ФОТ + расходы + амортизация + обязательства компании) = {money(calc_net)}")
        if abs(calc_net - net_after_taxes) > 1e-6:
            st.error("Несоответствие в вычислениях! Обратитесь к разработчику.")

        # Recommendations and comparison
        st.subheader("💡 Сравнение доступных режимов и рекомендации")
        # Build results table for user-selected modes
        comp_rows = []
        for mk, info, available, reason in display_results:
            comp_company_tax = info["company_total_tax"]
            comp_emp_with = info["employee_withholdings_total"]
            comp_er = info["employer_contributions_total"]
            comp_taxable = info["taxable_base"]
            comp_net = income_annual - (salaries_annual + expenses_sum + amortization_annual + comp_company_tax)
            status = "Доступен" if available else f"⚠️ Недоступен ({reason})" if reason else "⚠️ Недоступен"
            comp_rows.append({
                "Режим": mk,
                "Статус": status,
                "Налог (компания)": comp_company_tax,
                "Чистый доход (компания)": comp_net
            })

        df_comp = pd.DataFrame(comp_rows)
        # Format money in dataframe for display
        df_comp["Налог (компания)"] = df_comp["Налог (компания)"].apply(money)
        df_comp["Чистый доход (компания)"] = df_comp["Чистый доход (компания)"].apply(money)
        st.table(df_comp)

        # Recommendations textual (always show)
        # Determine best by minimal company tax among available modes
        available_modes_list = [r for r in comp_rows if r["Статус"].startswith("Доступен")]
        if available_modes_list:
            best_by_tax = min(available_modes_list, key=lambda x: x["Налог (компания)"])
            # but note columns currently strings; rebuild to numeric selection
            best = min(available_modes_list, key=lambda x: x["Налог (компания)"])
            # Actually we need numeric comparisons -> recompute quick
            best_idx = None
            best_tax_num = None
            for i, r in enumerate(comp_rows):
                if r["Статус"] == "Доступен":
                    taxn = r["Налог (компания)"]
                    # numeric from money string not needed if we use info earlier - simpler:
                    pass
            # Build using mode_infos numeric
            best_mode = None
            best_tax_val = None
            best_net_val = None
            for mk, info, available, reason in display_results:
                if available:
                    val = info["company_total_tax"]
                    netv = income_annual - (salaries_annual + expenses_sum + amortization_annual + val)
                    if best_mode is None or val < best_tax_val:
                        best_mode = mk
                        best_tax_val = val
                        best_net_val = netv
            if best_mode:
                st.success(f"Рекомендация: минимальная налоговая нагрузка у режима «{best_mode}» — налог ≈ {money(best_tax_val)}, чистый доход ≈ {money(best_net_val)}.")
        else:
            st.info("Нет доступных режимов (по ограничениям). Показаны расчёты для сравнения — рассмотрите переход на другой режим или изменение структуры бизнеса.")

        # Provide targeted tips: where you can reduce tax
        st.subheader("🛠️ Подсказки по снижению налоговой нагрузки")
        # Tip: check amortization
        # compute impact of excluding amortization (if considered)
        if amortization_annual > 0 and primary in ("general_ip", "general_too"):
            # recompute profit without amortization
            _, base_with_amort, _ = compute_mode_tax(primary, income_annual, salaries_annual, expenses_sum, amortization_annual)
            tax_with_amort = mode_infos[primary]["mode_tax"]
            _, base_no_amort, _ = compute_mode_tax(primary, income_annual, salaries_annual, expenses_sum, 0.0)
            tax_no_amort = 0.0
            if primary in ("general_ip"):
                tax_no_amort = max(0.0, base_no_amort * RATE_IP_GENERAL)
            elif primary in ("general_too"):
                tax_no_amort = max(0.0, base_no_amort * RATE_TOO_KPN)
            diff = tax_with_amort - tax_no_amort
            st.info(f"Учёт амортизации снижает налог по выбранному режиму примерно на {money(diff)} (проверьте нормы амортизации и подтверждающие документы).")

        # Tip: expenses categories
        st.markdown("**Совет:** убедитесь, что у вас есть первичные документы (счета, акты, договоры) для тех расходов, которые вы хотите учитывать — налоговая может отказать в вычете без подтверждений.")

        st.balloons()

if __name__ == "__main__":
    main()

