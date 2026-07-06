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

def get_gcal_url():
    try:
        if "GCAL_ICS_URL" in st.secrets:
            return st.secrets["GCAL_ICS_URL"]
    except Exception:
        pass
    return os.getenv("GCAL_ICS_URL")

@st.cache_data(ttl=600)
def get_gcal_events(start_iso, end_iso):
    """Googleカレンダーの限定公開URL(iCal)からイベントを取得。日付ごとの辞書で返す"""
    url = get_gcal_url()
    if not url:
        return {}
    try:
        import icalendar
        import recurring_ical_events
        from zoneinfo import ZoneInfo
        jst = ZoneInfo("Asia/Tokyo")
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        cal = icalendar.Calendar.from_ical(res.content)
        events = recurring_ical_events.of(cal).between(
            date.fromisoformat(start_iso), date.fromisoformat(end_iso) + timedelta(days=1))
        by_date = {}
        for ev in events:
            title = str(ev.get("SUMMARY", "予定"))
            dtstart = ev["DTSTART"].dt
            if hasattr(dtstart, "hour"):  # 時刻あり
                dtstart = dtstart.astimezone(jst)
                d_str = dtstart.date().isoformat()
                label = f"{dtstart.strftime('%H:%M')} {title}"
            else:  # 終日イベント
                d_str = dtstart.isoformat()
                label = title
            by_date.setdefault(d_str, []).append(label)
        return by_date
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}

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

tab3, tab1, tab2 = st.tabs(["シフトカレンダー", "スタッフ一覧", "シフト登録"])

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
    view = st.radio("表示モード", ["📅 週間", "🗓️ 月間"], horizontal=True, index=1)
    if not get_gcal_url():
        st.caption("📌 Googleカレンダー：未連携（Secretsに GCAL_ICS_URL が読み込めていません）")
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
        gcal_events = get_gcal_events(str(week_start), str(week_end))
        gcal_err = gcal_events.pop("_error", None)
        if gcal_err:
            st.warning(f"Googleカレンダーの取得に失敗：{gcal_err}")
        if week_shifts:
            fig = go.Figure()
            shifts_by_day = {}
            for sh in week_shifts:
                d = date.fromisoformat(sh["勤務日"]["value"])
                shifts_by_day.setdefault(d, []).append(sh)
            for d, day_shifts in shifts_by_day.items():
                day_shifts.sort(key=lambda x: x["開始時刻"]["value"] or "99:99")
                day_idx = (d - week_start).days
                w = 0.8 / len(day_shifts)
                for pos, sh in enumerate(day_shifts):
                    s_str = sh["開始時刻"]["value"] or "00:00"
                    e_str = sh["終了時刻"]["value"] or "00:00"
                    name = sh["スタッフ名"]["value"]
                    stype = sh["シフト区分"]["value"] or "その他"
                    s_h = int(s_str[:2]) + int(s_str[3:5]) / 60
                    e_h = int(e_str[:2]) + int(e_str[3:5]) / 60
                    color = get_staff_color(name, all_staff_names)
                    fig.add_trace(go.Bar(
                        name=name, x=[day_idx], y=[e_h - s_h], base=[s_h],
                        marker_color=color, marker_line=dict(color="white", width=1),
                        text=f"{name}<br>{s_str}〜{e_str}<br>{stype}",
                        textposition="inside", insidetextanchor="middle",
                        hovertemplate=f"<b>{name}</b><br>{stype}<br>{s_str}〜{e_str}<extra></extra>",
                        showlegend=False, width=w,
                        offset=-0.4 + pos * w,
                    ))
            # Googleカレンダーのイベントをグラフ上部に表示（列ズレしないようグラフ内に描画）
            ev_rows = max((len(gcal_events.get(str(week_start + timedelta(days=i)), [])) for i in range(7)), default=0)
            y_top = 7 - 0.9 * ev_rows - 0.1 if ev_rows else 7
            for i in range(7):
                for j, ev in enumerate(gcal_events.get(str(week_start + timedelta(days=i)), [])):
                    label = ev if len(ev) <= 14 else ev[:13] + "…"
                    fig.add_annotation(x=i, y=6.55 - 0.9 * (ev_rows - 1 - j),
                        text=label, showarrow=False,
                        font=dict(size=9, color="#5D4037"),
                        bgcolor="#FFF3CD", bordercolor="#F57C00", borderwidth=1,
                        hovertext=ev)
            if week_start <= today <= week_end:
                t_idx = (today - week_start).days
                fig.add_vrect(x0=t_idx - 0.5, x1=t_idx + 0.5, fillcolor="#64B5F6",
                    opacity=0.15, layer="below", line_width=0)
            fig.update_layout(
                barmode="group",
                xaxis=dict(tickvals=list(range(7)), ticktext=day_order,
                    range=[-0.5, 6.5], tickfont=dict(size=13)),
                yaxis=dict(range=[22, y_top], tickvals=list(range(7, 23)),
                    ticktext=[f"{h}:00" for h in range(7, 23)], title="時刻", gridcolor="#EEE"),
                height=550 + 30 * ev_rows, plot_bgcolor="#FAFAFA",
                margin=dict(l=60, r=20, t=20, b=40), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            if gcal_events:
                st.markdown("##### 📌 イベント（Googleカレンダー）")
                for i in range(7):
                    d = week_start + timedelta(days=i)
                    for ev in gcal_events.get(str(d), []):
                        st.markdown(f"- {DAY_JA[i]} {d.strftime('%m/%d')}：{ev}")
            st.info("この週にシフトはありません。")
        st.markdown("---")
        st.subheader("日別詳細・編集")
        selected_date = st.date_input("日付を選択", value=today, key="week_detail_date")
        show_day_detail(selected_date, all_shifts, all_staff_names, staff_list, key_prefix="week_")

    else:
        today = date.today()
        total_months = today.year * 12 + (today.month - 1) + st.session_state.month_offset
        year = total_months // 12
        month = total_months % 12 + 1
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
        for d in shifts_by_date:
            shifts_by_date[d].sort(key=lambda x: x["開始時刻"]["value"] or "99:99")
        gcal_events = get_gcal_events(str(month_start), str(month_end))
        gcal_err = gcal_events.pop("_error", None)
        if gcal_err:
            st.warning(f"Googleカレンダーの取得に失敗：{gcal_err}")
        day_headers = ["月", "火", "水", "木", "金", "土", "日"]
        day_colors = ["#333","#333","#333","#333","#333","#1565C0","#E53935"]
        cal = calendar.monthcalendar(year, month)

        html = "<table style='width:100%;border-collapse:collapse;font-size:11px'><tr>"
        for h, hc in zip(day_headers, day_colors):
            html += f"<th style='text-align:center;color:{hc};padding:4px 1px;border-bottom:1px solid #ddd'>{h}</th>"
        html += "</tr>"

        for week in cal:
            html += "<tr style='vertical-align:top'>"
            for i, day in enumerate(week):
                if day == 0:
                    html += "<td style='padding:2px'></td>"
                else:
                    d_str = f"{year}-{month:02d}-{day:02d}"
                    dc = "#E53935" if i == 6 else "#1565C0" if i == 5 else "#333"
                    cell = f"<div style='font-weight:bold;color:{dc};font-size:11px'>{day}</div>"
                    for ev in gcal_events.get(d_str, []):
                        cell += f"<div style='background:#FFF3CD;border-left:3px solid #F57C00;color:#5D4037;border-radius:3px;padding:1px 2px;margin:1px 0;font-size:9px;line-height:1.3;word-break:break-all'>{ev}</div>"
                    if d_str in shifts_by_date:
                        for sh in shifts_by_date[d_str]:
                            name = sh["スタッフ名"]["value"]
                            s_str = sh["開始時刻"]["value"] or ""
                            e_str = sh["終了時刻"]["value"] or ""
                            color = get_staff_color(name, all_staff_names)
                            short_name = name.split()[0] if name else name
                            cell += f"<div style='background:{color};color:white;border-radius:3px;padding:1px 2px;margin:1px 0;font-size:9px;line-height:1.3'>{short_name}<br>{s_str[:5]}~{e_str[:5]}</div>"
                    is_today = (d_str == str(today))
                    td_style = "padding:2px;border:2px solid #64B5F6;background:#E3F2FD;min-height:50px" if is_today else "padding:2px;border:1px solid #eee;min-height:50px"
                    html += f"<td style='{td_style}'>{cell}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("日別詳細・編集")
        selected_date = st.date_input("日付を選択", value=today, key="month_detail_date")
        show_day_detail(selected_date, all_shifts, all_staff_names, staff_list, key_prefix="month_")