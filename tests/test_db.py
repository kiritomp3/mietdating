from models import User, Like, ViewedProfile
from datetime import date

def test_create_user(db_session):
    """Тест на создание пользователя"""
    user = User(
        id=12345,
        username="testuser",
        name="Test Name",
        birthdate=date(2000, 1, 1),
        city="Test City",
        description="Test description",
        photo_id="photo123",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    user_in_db = db_session.query(User).filter(User.id == 12345).first()
    assert user_in_db is not None
    assert user_in_db.name == "Test Name"
    assert user_in_db.city == "Test City"

def test_like_functionality(db_session):
    """Тест на работу лайков"""
    user1 = User(id=1, username="user1", name="Alice", birthdate=date(1990, 5, 10), city="NY", is_active=True)
    user2 = User(id=2, username="user2", name="Bob", birthdate=date(1992, 8, 15), city="LA", is_active=True)

    db_session.add_all([user1, user2])
    db_session.commit()

    like = Like(user_id=1, liked_user_id=2)
    db_session.add(like)
    db_session.commit()

    like_in_db = db_session.query(Like).filter(Like.user_id == 1, Like.liked_user_id == 2).first()
    assert like_in_db is not None

def test_profile_viewing(db_session):
    """Тест на запись просмотренных анкет"""
    viewed = ViewedProfile(user_id=1, target_id=2)
    db_session.add(viewed)
    db_session.commit()

    viewed_in_db = db_session.query(ViewedProfile).filter_by(user_id=1, target_id=2).first()
    assert viewed_in_db is not None