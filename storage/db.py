from sqlmodel import create_engine, Session, SQLModel
from config import settings
from .models import User
from passlib.context import CryptContext

engine = create_engine(settings.DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    SQLModel.metadata.create_all(engine)
    
    # Create initial admin user if it doesn't exist
    with Session(engine) as session:
        from sqlmodel import select
        admin = session.exec(select(User).where(User.username == settings.ADMIN_USERNAME)).first()
        if not admin:
            hashed_pw = pwd_context.hash(settings.ADMIN_PASSWORD)
            new_admin = User(username=settings.ADMIN_USERNAME, hashed_password=hashed_pw)
            session.add(new_admin)
            session.commit()

def get_session():
    with Session(engine) as session:
        yield session
