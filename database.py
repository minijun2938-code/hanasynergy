import sqlite3
from datetime import datetime, timedelta, timezone

import pytz

def get_connection():
    return sqlite3.connect('poc_chemistry.db')

def get_kst_now():
    """현재 시간을 한국 표준시(KST)로 반환합니다."""
    tz_kst = pytz.timezone('Asia/Seoul')
    return datetime.now(tz_kst).strftime('%Y-%m-%d %H:%M:%S')

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_profiles 
                     (emp_id TEXT PRIMARY KEY, 
                      password TEXT, 
                      name TEXT, 
                      team_name TEXT,
                      profile_data TEXT,
                      last_sync TEXT,
                      llm_name TEXT)''')
        
        # 기존 테이블에 새 컬럼이 없을 경우 추가 (Migration)
        try:
            c.execute("ALTER TABLE user_profiles ADD COLUMN last_sync TEXT")
        except: pass
        try:
            c.execute("ALTER TABLE user_profiles ADD COLUMN llm_name TEXT")
        except: pass
        try:
            c.execute("ALTER TABLE user_profiles ADD COLUMN team_name TEXT")
        except: pass
        
        c.execute('''CREATE TABLE IF NOT EXISTS matches 
                     (req_id TEXT, target_id TEXT, status TEXT, UNIQUE(req_id, target_id))''')
        
        # 분석 리포트 히스토리 테이블 추가
        c.execute('''CREATE TABLE IF NOT EXISTS analysis_history 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      emp_id TEXT,
                      target_id TEXT,
                      mode TEXT,
                      report TEXT,
                      created_at TEXT,
                      is_favorite INTEGER DEFAULT 0)''')
        
        # Migration: is_favorite 컬럼 추가
        try:
            c.execute("ALTER TABLE analysis_history ADD COLUMN is_favorite INTEGER DEFAULT 0")
        except: pass

        # (관리자용) 분석 감사 로그: 어떤 요청(프롬프트)이 어떤 결과를 만들었는지 추적
        c.execute('''CREATE TABLE IF NOT EXISTS analysis_audit
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      emp_id TEXT,
                      target_id TEXT,
                      mode TEXT,
                      model TEXT,
                      system_prompt TEXT,
                      user_prompt TEXT,
                      report TEXT,
                      created_at TEXT)''')

        conn.commit()

def save_profile(emp_id, profile_json, llm_name=None):
    """프로필 데이터를 저장합니다. 이미 존재한다면 업데이트합니다."""
    now = get_kst_now()
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""UPDATE user_profiles 
                     SET profile_data = ?, last_sync = ?, llm_name = ? 
                     WHERE emp_id = ?""", 
                  (profile_json, now, llm_name, emp_id))
        conn.commit()

def get_user_info(emp_id):
    """사번으로 이름과 성향 데이터를 한꺼번에 가져옵니다."""
    with get_connection() as conn:
        c = conn.cursor()
        return c.execute("SELECT name, profile_data, last_sync, llm_name, team_name FROM user_profiles WHERE emp_id=?", (emp_id,)).fetchone()

def send_match_request(req_id, target_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO matches VALUES (?, ?, ?)", (req_id, target_id, 'Pending'))
        conn.commit()

def get_pending_requests(emp_id):
    with get_connection() as conn:
        c = conn.cursor()
        return c.execute("SELECT req_id FROM matches WHERE target_id=? AND status='Pending'", (emp_id,)).fetchall()

def accept_match_request(req_id, target_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE matches SET status='Accepted' WHERE req_id=? AND target_id=?", (req_id, target_id))
        conn.commit()

def cancel_match_request(req_id, target_id):
    """보낸 요청을 취소(삭제)합니다."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM matches WHERE req_id=? AND target_id=? AND status='Pending'", (req_id, target_id))
        conn.commit()

def remove_match(id_a, id_b):
    """이미 수락된 매칭 관계를 삭제합니다."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM matches WHERE (req_id=? AND target_id=?) OR (req_id=? AND target_id=?)", (id_a, id_b, id_b, id_a))
        conn.commit()

def get_sent_requests(emp_id):
    """내가 보낸 대기 중인 요청 목록을 가져옵니다."""
    with get_connection() as conn:
        c = conn.cursor()
        return c.execute("SELECT target_id FROM matches WHERE req_id=? AND status='Pending'", (emp_id,)).fetchall()

def get_accepted_matches(emp_id):
    with get_connection() as conn:
        c = conn.cursor()
        return c.execute("""SELECT req_id, target_id FROM matches 
                            WHERE (req_id=? OR target_id=?) AND status='Accepted'""", 
                         (emp_id, emp_id)).fetchall()

def get_team_members(team_name):
    """같은 팀 멤버들의 이름과 프로필 데이터를 가져옵니다."""
    with get_connection() as conn:
        c = conn.cursor()
        return c.execute("SELECT name, profile_data, emp_id FROM user_profiles WHERE team_name=? AND profile_data IS NOT NULL", (team_name,)).fetchall()

def save_analysis_report(emp_id, target_id, mode, report):
    """분석된 리포트를 저장합니다."""
    now = get_kst_now()
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO analysis_history (emp_id, target_id, mode, report, created_at, is_favorite) VALUES (?, ?, ?, ?, ?, 0)",
            (emp_id, target_id, mode, report, now),
        )
        conn.commit()


def save_analysis_audit(emp_id, target_id, mode, model, system_prompt, user_prompt, report):
    """관리자용: 분석 요청/프롬프트/결과를 함께 저장합니다."""
    now = get_kst_now()
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO analysis_audit
               (emp_id, target_id, mode, model, system_prompt, user_prompt, report, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (emp_id, target_id, mode, model, system_prompt, user_prompt, report, now),
        )
        conn.commit()


def get_analysis_audit(limit=200, emp_id=None, mode=None):
    """관리자용: 최근 분석 감사 로그를 가져옵니다."""
    q = "SELECT id, emp_id, target_id, mode, model, system_prompt, user_prompt, report, created_at FROM analysis_audit"
    where = []
    params = []
    if emp_id:
        where.append("emp_id = ?")
        params.append(emp_id)
    if mode and mode != "(전체)":
        where.append("mode = ?")
        params.append(mode)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))

    with get_connection() as conn:
        c = conn.cursor()
        return c.execute(q, params).fetchall()

def get_analysis_history(emp_id):
    """사용자의 최근 분석 히스토리를 가져옵니다."""
    with get_connection() as conn:
        c = conn.cursor()
        # target_id가 NULL인 경우는 '내 성향 분석'
        return c.execute("""
            SELECT h.target_id, u.name, h.mode, h.report, h.created_at, h.id, h.is_favorite
            FROM analysis_history h
            LEFT JOIN user_profiles u ON h.target_id = u.emp_id
            WHERE h.emp_id=? 
            ORDER BY h.is_favorite DESC, h.created_at DESC LIMIT 20
        """, (emp_id,)).fetchall()

def delete_analysis_history(history_id, emp_id):
    """특정 분석 히스토리를 삭제합니다."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM analysis_history WHERE id=? AND emp_id=?", (history_id, emp_id))
        conn.commit()

def toggle_favorite(history_id, emp_id):
    """즐겨찾기 상태를 토글합니다."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE analysis_history SET is_favorite = 1 - is_favorite WHERE id=? AND emp_id=?", (history_id, emp_id))
        conn.commit()
