from apps.backend.core.security import hash_password
from apps.backend.models import Role, User


def make_user(db_session, org, role_name: str, user_id: str, email: str) -> User:
    role = db_session.query(Role).filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name)
        db_session.add(role)
        db_session.flush()
    user = User(
        id=user_id,
        org_id=org.id,
        email=email,
        full_name=user_id,
        hashed_password=hash_password("pw12345"),
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


def auth_headers(app_client, email: str, password: str = "pw12345") -> dict:
    res = app_client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
