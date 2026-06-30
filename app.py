import streamlit as st
import requests
import os
import json
import calendar
import plotly.graph_objects as go
from dotenv import load_dotenv
from datetime import date, time, timedelta

load_dotenv()

DOMAIN = os.getenv("KINTONE_DOMAIN")
TOKEN_STAFF = os.getenv("API_TOKEN_STAFF")
TOKEN_SHIFT = os.getenv("API_TOKEN_SHIFT")
APP_STAFF = os.getenv("APP_ID_STAFF")
APP_SHIFT = os.getenv("APP_ID_SHIFT")
BASE_URL = f"https://{DOMAIN}/k/v1"
APP_PASSWORD = os.getenv("APP_PASSWORD", "tored2024")

STAFF_COLOR_LIST = [
    "#1565C0", "#E53935", "#2E7D32", "#F57C00",
    "#6A1B9A", "#00838F", "#AD1457", "#4E342E",
]

def get_staff_color(name, all_names):
    idx = all_names.index(name) if name in all_names else 0
    return STAFF_COLOR_LIST[idx % len(STAFF_COLOR_LIST)]

def get_staff():
    res = requests.get(f"{BASE_URL}/records.json",
        headers={"X-Cybozu-API-Token": TOKEN_STAFF},
        params={"app": APP_STAFF})
    return [r for r in res.json()["records"] if r["在籍ステータス"]["value"] == "在籍中"]

def get_shifts():
    res = requests.get(f"{BASE_URL}/records.json",
        headers={"X-Cybozu-API-Token": TOKEN_SHIFT},
        params={"app": APP_SHIFT})
    return res.json()["records"]

def post_shift(staff_id, staff_name, work_date, start_t, end_t, shift_type):
    res = requests.post(f"{BASE_URL}/record.json",
        headers={"X-Cybozu-API-Token": TOKEN_SHIFT, "Content-Type": "application/json"},
        data=json.dumps({"app": APP_SHIFT, "record": {
            "スタッフID": {"value": staff_id},
            "スタッフ名": {"value": staff_name},
            "勤務日":     {"value": str(work_date)},
            "開始時刻":   {"value": str(start_t)[:5]},
            "終了時刻":   {"value": str(end_t)[:5]},
            "シフト区分": {"value": shift_type},
        }}))
    return res.status_code == 200

def update_shift(record_id, start_t, end_t, shift_type):
    res = requests.put(f"{BASE_URL}/record.json",
        headers={"X-Cybozu-API-Token": TOKEN_SHIFT, "Content-Type": "application/json"},
        data=json.dumps({"app": APP_SHIFT, "id": record_id, "record": {
            "開始時刻":   {"value": str(start_t)[:5]},
            "終了時刻":   {"value": str(end_t)[:5]},
            "シフト区分": {"value": shift_type},
        }}))
    return res.status_code == 200

def delete_shift(record_id):
    res = requests.delete(f"{BASE_URL}/records.json",
        headers={"X-Cybozu-API-Token": TOKEN_SHIFT, "Content-Type": "application/json"},
        data=json.dumps({"app": APP_SHIFT, "ids": [record_id]}))
    return res.status_code == 200

def show_day_detail(selected_date, all_shifts, all_staff_names, staff_list, key_prefix=""):
    day_shifts = [sh for sh in all_shifts if sh["勤務日"]["value"] == str(selected_date)]
    if day_shifts:
        staff_in_day = list(dict.fromkeys(sh["スタッフ名"]["value"] for sh in day_shifts))
        fig = go.Figure()
        for sh in day_shifts:
            s_str = sh["開始時刻"]["value"] or "00:00"
            e_str = sh["終了時刻"]["value"] or "00:00"
            name = sh["スタッフ名"]["value"]
            stype = sh["シフト区分"]["value"] or "その他"
            s_h = int(s_str[:2]) + int(s_str[3:5]) / 60
            e_h = int(e_str[:2]) + int(e_str[3:5]) / 60
            y = staff_in_day.index(name)
            color = get_staff_color(name, all_staff_names)
            fig.add_shape(type="rect", x0=s_h, x1=e_h, y0=y-0.35, y1=y+0.35,
                fillcolor=color, line=dict(color="white", width=2))
            fig.add_annotation(x=(s_h+e_h)/2, y=y,
                text=f"{name}　{s_str}〜{e_str}　{stype}",
                showarrow=False, font=dict(size=12, color="white"))
        fig.update_layout(
            xaxis=dict(range=[7, 22], tickvals=list(range(7, 23)),
                ticktext=[f"{h}:00" for h in range(7, 23)], gridcolor="#EEE", title="時刻"),
            yaxis=dict(tickvals=list(range(len(staff_in_day))), ticktext=staff_in_day),
            height=max(250, len(staff_in_day) * 130),
            plot_bgcolor="#FAFAFA", margin=dict(l=130, r=20, t=20, b=50), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("##### 編集・削除")
        shift_choices = ["早番", "遅番", "イベント番（平日）", "イベント番（休日）", "特別"]
        for sh in day_shifts:
            record_id = sh["$id"]["value"]
            name = sh["スタッフ名"]["value"]
            s_str = sh["開始時刻"]["value"] or "00:00"
            e_str = sh["終了時刻"]["value"] or "00:00"
            stype = sh["シフト区分"]["value"] or "早番"
            with st.expander(f"　{name}　{s_str}〜{e_str}　{stype}"):
                col_s, col_e, col_t = st.columns(3)
                with col_s:
                    new_start = st.time_input("開始時刻", value=time(int(s_str[:2]), int(s_str[3:5])), key=f"{key_prefix}start_{record_id}")
                with col_e:
                    new_end = st.time_input("終了時刻", value=time(int(e_str[:2]), int(e_str[3:5])), key=f"{key_prefix}end_{record_id}")
                with col_t:
                    new_type = st.selectbox("シフト区分", shift_choices,
                        index=shift_choices.index(stype) if stype in shift_choices else 0,
                        key=f"{key_prefix}type_{record_id}")
                col_upd, col_del = st.columns(2)
                with col_upd:
                    if st.button("💾 更新", key=f"{key_prefix}upd_{record_id}"):
                        if update_shift(record_id, new_start, new_end, new_type):
                            st.success("更新しました！")
                            st.rerun()
                        else:
                            st.error("更新に失敗しました。")
                with col_del:
                    if st.button("🗑️ 削除", key=f"{key_prefix}del_{record_id}"):
                        if delete_shift(record_id):
                            st.success("削除しました！")
                            st.rerun()
                        else:
                            st.error("削除に失敗しました。")
    else:
        st.info("この日のシフトはありません。")

st.set_page_config(page_title="シフト管理", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("シフト管理アプリ")
    st.markdown("### ログイン")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン", type="primary"):
        if password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

col_title, col_logout = st.columns([8, 1])
with col_title:
    st.title("シフト管理アプリ")
with col_logout:
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()

if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

tab1, tab2, tab3 = st.tabs(["スタッフ一覧", "シフト登録", "シフトカレンダー"])

with tab1:
    st.subheader("スタッフ一覧")
    for s in get_staff():
        st.write(f"**{s['氏名']['value']}**　{s['所属組織']['value']}　{s['役職']['value']}")

with tab2:
    st.subheader("シフト登録")
    staff_list = get_staff()
    staff_options = {s["氏名"]["value"]: s["スタッフID"]["value"] for s in staff_list}
    selected_name = st.selectbox("スタッフ", list(staff_options.keys()))
    work_date = st.date_input("勤務日", value=date.today())
    col_s, col_e = st.columns(2)
    with col_s:
        start_t = st.time_input("開始時刻", value=time(9, 0))
    with col_e:
        end_t = st.time_input("終了時刻", value=time(18, 0))
    shift_type = st.selectbox("シフト区分", ["早番", "遅番", "イベント番（平日）", "イベント番（休日）", "特別"])
    if st.button("登録する", type="primary"):
        ok = post_shift(staff_options[selected_name], selected_name, work_date, start_t, end_t, shift_type)
        st.success("登録しました！") if ok else st.error("登録に失敗しました。")

with tab3:
    view = st.radio("表示モード", ["📅 週間", "🗓️ 月間"], horizontal=True)
    all_shifts = get_shifts()
    all_staff_names = [s["氏名"]["value"] for s in get_staff()]
    staff_list = get_staff()
    DAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

    if view == "📅 週間":
        today = date.today()
        week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state.week_offset)
        week_end = week_start + timedelta(days=6)
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            if st.button("◀ 前の週"):
                st.session_state.week_offset -= 1
                st.rerun()
        with col2:
            st.markdown(f"### {week_start.strftime('%Y年%m月%d日')}（月）〜{week_end.strftime('%m月%d日')}（日）")
        with col3:
            if st.button("次の週 ▶"):
                st.session_state.week_offset += 1
                st.rerun()
        week_shifts = [sh for sh in all_shifts if sh["勤務日"]["value"] and
                       week_start <= date.fromisoformat(sh["勤務日"]["value"]) <= week_end]
        day_order = [f"{DAY_JA[i]} {(week_start+timedelta(days=i)).strftime('%m/%d')}" for i in range(7)]
        if week_shifts:
            fig = go.Figure()
            staff_in_week = list(dict.fromkeys(sh["スタッフ名"]["value"] for sh in week_shifts))
            n_staff = len(staff_in_week)
            bar_width = 0.8 / n_staff
            for sh in week_shifts:
                d = date.fromisoformat(sh["勤務日"]["value"])
                day_label = f"{DAY_JA[d.weekday()]} {d.strftime('%m/%d')}"
                s_str = sh["開始時刻"]["value"] or "00:00"
                e_str = sh["終了時刻"]["value"] or "00:00"
                name = sh["スタッフ名"]["value"]
                stype = sh["シフト区分"]["value"] or "その他"
                s_h = int(s_str[:2]) + int(s_str[3:5]) / 60
                e_h = int(e_str[:2]) + int(e_str[3:5]) / 60
                color = get_staff_color(name, all_staff_names)
                staff_idx = staff_in_week.index(name)
                fig.add_trace(go.Bar(
                    name=name, x=[day_label], y=[e_h - s_h], base=[s_h],
                    marker_color=color, marker_line=dict(color="white", width=1),
                    text=f"{name}<br>{s_str}〜{e_str}<br>{stype}",
                    textposition="inside", insidetextanchor="middle",
                    hovertemplate=f"<b>{name}</b><br>{stype}<br>{s_str}〜{e_str}<extra></extra>",
                    showlegend=False, offsetgroup=str(staff_idx), width=bar_width,
                ))
            fig.update_layout(
                barmode="group", bargroupgap=0.1,
                xaxis=dict(categoryorder="array", categoryarray=day_order, tickfont=dict(size=13)),
                yaxis=dict(range=[22, 7], tickvals=list(range(7, 23)),
                    ticktext=[f"{h}:00" for h in range(7, 23)], title="時刻", gridcolor="#EEE"),
                height=550, plot_bgcolor="#FAFAFA",
                margin=dict(l=60, r=20, t=20, b=40), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("この週にシフトはありません。")
        st.markdown("---")
        st.subheader("日別詳細・編集")
        selected_date = st.date_input("日付を選択", value=today, key="week_detail_date")
        show_day_detail(selected_date, all_shifts, all_staff_names, staff_list, key_prefix="week_")

    else:
        today = date.today()
        target_month = today.replace(day=1) + timedelta(days=32 * st.session_state.month_offset)
        target_month = target_month.replace(day=1)
        year = target_month.year
        month = target_month.month
        _, last_day = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            if st.button("◀ 前の月"):
                st.session_state.month_offset -= 1
                st.rerun()
        with col2:
            st.markdown(f"### {year}年{month}月")
        with col3:
            if st.button("次の月 ▶"):
                st.session_state.month_offset += 1
                st.rerun()
        month_shifts = [sh for sh in all_shifts if sh["勤務日"]["value"] and
                        month_start <= date.fromisoformat(sh["勤務日"]["value"]) <= month_end]
        shifts_by_date = {}
        for sh in month_shifts:
            d = sh["勤務日"]["value"]
            if d not in shifts_by_date:
                shifts_by_date[d] = []
            shifts_by_date[d].append(sh)
        day_headers = ["月", "火", "水", "木", "金", "土", "日"]
        cal = calendar.monthcalendar(year, month)
        cols = st.columns(7)
        for i, h in enumerate(day_headers):
            hcolor = "#E53935" if h == "日" else "#1565C0" if h == "土" else "#333"
            cols[i].markdown(f"<div style='text-align:center;font-weight:bold;color:{hcolor}'>{h}</div>", unsafe_allow_html=True)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown("<div style='min-height:80px'></div>", unsafe_allow_html=True)
                    else:
                        d_str = f"{year}-{month:02d}-{day:02d}"
                        day_color = "#E53935" if i == 6 else "#1565C0" if i == 5 else "#333"
                        st.markdown(f"<div style='font-weight:bold;color:{day_color}'>{day}</div>", unsafe_allow_html=True)
                        if d_str in shifts_by_date:
                            for sh in shifts_by_date[d_str]:
                                name = sh["スタッフ名"]["value"]
                                s_str = sh["開始時刻"]["value"] or ""
                                e_str = sh["終了時刻"]["value"] or ""
                                color = get_staff_color(name, all_staff_names)
                                st.markdown(
                                    f"<div style='background:{color};color:white;border-radius:4px;"
                                    f"padding:2px 4px;margin:2px 0;font-size:11px'>"
                                    f"{name}<br>{s_str}〜{e_str}</div>",
                                    unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("日別詳細・編集")
        selected_date = st.date_input("日付を選択", value=today, key="month_detail_date")
        show_day_detail(selected_date, all_shifts, all_staff_names, staff_list, key_prefix="month_")