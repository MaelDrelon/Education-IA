from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin, require_staff
from ..db import get_db
from ..models import Role, User
from ..schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["utilisateurs"])


@router.get("", response_model=list[UserOut])
def list_users(role: Role | None = None, db: Session = Depends(get_db),
               user: User = Depends(require_staff)):
    # Le formateur n'a besoin que de la liste des apprenants (pour assigner les examens)
    if user.role == Role.formateur:
        role = Role.apprenant
    q = select(User).order_by(User.full_name)
    if role:
        q = q.where(User.role == role)
    return db.scalars(q).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "Email déjà utilisé")
    user = User(email=data.email, full_name=data.full_name, role=data.role,
                hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    if user.id == admin.id and (data.is_active is False or (data.role and data.role != Role.admin)):
        raise HTTPException(400, "Vous ne pouvez pas vous désactiver ni vous retirer le rôle admin")
    for field in ("full_name", "role", "is_active"):
        value = getattr(data, field)
        if value is not None:
            setattr(user, field, value)
    if data.password:
        user.hashed_password = hash_password(data.password)
    db.commit()
    return user
