"""정식 전환 A 신규 기능 테스트 — 회원가입·기업등록·초대·권한격리."""
import io


def _signup(client, email, name="테스터", pw="password123"):
    r = client.post("/api/auth/register",
                    json={"email": email, "password": pw, "name": name})
    return r


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_success(client):
    r = _signup(client, "new1@test.dev")
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user"]["company_id"] is None  # 기업 미소속 상태


def test_register_duplicate_email(client):
    _signup(client, "dup@test.dev")
    r = _signup(client, "dup@test.dev")
    assert r.status_code == 409


def test_register_short_password(client):
    r = _signup(client, "short@test.dev", pw="123")
    assert r.status_code == 422  # pydantic min_length


def test_company_create_assigns_owner(client):
    r = _signup(client, "owner2@test.dev")
    h = _headers(r.json()["token"])
    r = client.post("/api/companies", headers=h,
                    json={"name": "테스트제조"})
    assert r.status_code == 200
    assert r.json()["role"] == "OWNER"
    cid = r.json()["company"]["id"]

    me = client.get("/api/auth/me", headers=h).json()
    assert me["company_id"] == cid and me["role"] == "OWNER"

    # 소속 기업 목록
    mine = client.get("/api/companies/mine", headers=h).json()
    assert any(c["company_id"] == cid and c["active"] for c in mine)


def test_new_company_has_no_demo_data(client):
    r = _signup(client, "fresh@test.dev")
    h = _headers(r.json()["token"])
    client.post("/api/companies", headers=h, json={"name": "빈기업"})
    dash = client.get("/api/dashboard", headers=h)
    assert dash.status_code == 200
    assert dash.json().get("has_data") in (False, None) or "kpis" in str(dash.json())
    # 재무 데이터 없음
    rows = client.get("/api/financial/monthly", headers=h).json()
    assert rows == []


def test_invite_flow(client):
    # 기업 생성
    r = _signup(client, "invowner@test.dev")
    h_owner = _headers(r.json()["token"])
    client.post("/api/companies", headers=h_owner, json={"name": "초대기업"})

    # 초대 생성 (MEMBER)
    r = client.post("/api/invites", headers=h_owner,
                    json={"email": "invited@test.dev", "role": "MEMBER"})
    assert r.status_code == 200
    token = r.json()["invite_token"]

    # OWNER 역할 초대 불가
    r = client.post("/api/invites", headers=h_owner,
                    json={"email": "x@test.dev", "role": "OWNER"})
    assert r.status_code == 400

    # 수락자 가입 후 수락
    r = _signup(client, "invited@test.dev")
    h_new = _headers(r.json()["token"])
    r = client.post("/api/invites/accept", headers=h_new, json={"token": token})
    assert r.status_code == 200
    assert r.json()["role"] == "MEMBER"

    # 재수락 불가
    r = client.post("/api/invites/accept", headers=h_new, json={"token": token})
    assert r.status_code == 400

    # 초대 목록에 accepted 표시
    invs = client.get("/api/invites", headers=h_owner).json()
    assert any(i["email"] == "invited@test.dev" and i["status"] == "accepted" for i in invs)


def test_invite_wrong_email_rejected(client):
    r = _signup(client, "o3@test.dev")
    h = _headers(r.json()["token"])
    client.post("/api/companies", headers=h, json={"name": "기업3"})
    tok = client.post("/api/invites", headers=h,
                      json={"email": "a@test.dev", "role": "VIEWER"}).json()["invite_token"]
    r2 = _signup(client, "b@test.dev")  # 다른 이메일 계정
    h2 = _headers(r2.json()["token"])
    r = client.post("/api/invites/accept", headers=h2, json={"token": tok})
    assert r.status_code == 403


def test_invite_cancel(client):
    r = _signup(client, "o4@test.dev")
    h = _headers(r.json()["token"])
    client.post("/api/companies", headers=h, json={"name": "기업4"})
    inv = client.post("/api/invites", headers=h,
                      json={"email": "c@test.dev", "role": "MEMBER"}).json()
    r = client.post(f"/api/invites/{inv['invite']['id']}/cancel", headers=h)
    assert r.status_code == 200
    r2 = _signup(client, "c@test.dev")
    h2 = _headers(r2.json()["token"])
    r = client.post("/api/invites/accept", headers=h2,
                    json={"token": inv["invite_token"]})
    assert r.status_code == 400


def test_admin_cannot_grant_owner(client):
    # OWNER 생성 → ADMIN 초대 → ADMIN이 OWNER 부여 시도 → 403
    r = _signup(client, "o5@test.dev")
    h_owner = _headers(r.json()["token"])
    client.post("/api/companies", headers=h_owner, json={"name": "기업5"})
    tok = client.post("/api/invites", headers=h_owner,
                      json={"email": "adm@test.dev", "role": "ADMIN"}).json()["invite_token"]
    r2 = _signup(client, "adm@test.dev")
    h_admin = _headers(r2.json()["token"])
    client.post("/api/invites/accept", headers=h_admin, json={"token": tok})

    # ADMIN이 제3 사용자에게 OWNER 부여 시도
    tok3 = client.post("/api/invites", headers=h_admin,
                       json={"email": "m3@test.dev", "role": "MEMBER"}).json()["invite_token"]
    r3 = _signup(client, "m3@test.dev")
    client.post("/api/invites/accept", headers=_headers(r3.json()["token"]),
                json={"token": tok3})
    uid = r3.json()["user"]["id"]
    r = client.put(f"/api/users/{uid}", headers=h_admin, json={"role": "OWNER"})
    assert r.status_code == 403
    # OWNER는 부여 가능
    r = client.put(f"/api/users/{uid}", headers=h_owner, json={"role": "OWNER"})
    assert r.status_code == 200 and r.json()["role"] == "OWNER"


def test_cross_company_isolation(client):
    # 기업A 생성, 기업B 사용자가 기업A의 사용자 목록 접근 시도
    r = _signup(client, "a1@test.dev")
    h_a = _headers(r.json()["token"])
    client.post("/api/companies", headers=h_a, json={"name": "기업A"})
    client.post("/api/financial/monthly", headers=h_a,
                json={"month": "2026-01", "revenue": 999, "operating_profit": 1})

    r2 = _signup(client, "b1@test.dev")
    h_b = _headers(r2.json()["token"])
    client.post("/api/companies", headers=h_b, json={"name": "기업B"})
    rows = client.get("/api/financial/monthly", headers=h_b).json()
    assert all(m["month"] != "2026-01" for m in rows)


def test_deactivate_user(client):
    r = _signup(client, "o6@test.dev")
    h = _headers(r.json()["token"])
    client.post("/api/companies", headers=h, json={"name": "기업6"})
    tok = client.post("/api/invites", headers=h,
                      json={"email": "off@test.dev", "role": "MEMBER"}).json()["invite_token"]
    r2 = _signup(client, "off@test.dev")
    uid = r2.json()["user"]["id"]
    client.post("/api/invites/accept", headers=_headers(r2.json()["token"]),
                json={"token": tok})
    r = client.delete(f"/api/users/{uid}", headers=h)
    assert r.status_code == 200
    users = client.get("/api/users", headers=h).json()
    assert all(u["id"] != uid for u in users)


def test_no_company_write_blocked(client):
    """기업 미소속 사용자는 쓰기 API 거부."""
    r = _signup(client, "nocorp@test.dev")
    h = _headers(r.json()["token"])
    r = client.post("/api/financial/monthly", headers=h,
                    json={"month": "2026-01", "revenue": 1})
    assert r.status_code == 400


def test_change_password(client):
    r = _signup(client, "pw@test.dev")
    h = _headers(r.json()["token"])
    r = client.post("/api/auth/change-password", headers=h,
                    json={"current_password": "password123", "new_password": "newpassword9"})
    assert r.status_code == 200
    # 기존 토큰 무효화
    assert client.get("/api/auth/me", headers=h).status_code == 401
    # 새 비밀번호로 로그인
    r = client.post("/api/auth/login",
                    json={"email": "pw@test.dev", "password": "newpassword9"})
    assert r.status_code == 200


def test_password_reset_flow(client):
    _signup(client, "reset@test.dev")
    r = client.post("/api/auth/password-reset/request",
                    json={"email": "reset@test.dev"})
    assert r.status_code == 200
    tok = r.json()["demo_reset_token"]
    assert tok
    r = client.post("/api/auth/password-reset/confirm",
                    json={"token": tok, "new_password": "resetpass99"})
    assert r.status_code == 200
    # 재사용 불가
    r = client.post("/api/auth/password-reset/confirm",
                    json={"token": tok, "new_password": "again12345"})
    assert r.status_code == 400
    # 새 비밀번호 로그인
    r = client.post("/api/auth/login",
                    json={"email": "reset@test.dev", "password": "resetpass99"})
    assert r.status_code == 200


def test_health_db(client):
    r = client.get("/api/health/db")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_company_select_requires_membership(client):
    r = _signup(client, "solo@test.dev")
    h = _headers(r.json()["token"])
    # 존재하는 데모 기업(1)을 소속 없이 선택 시도 → 403
    r = client.post("/api/companies/select", headers=h, json={"company_id": 1})
    assert r.status_code == 403
