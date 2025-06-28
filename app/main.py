from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app import models, auth
from app.database import engine, SessionLocal
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

# Inicializa la app
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="holahola7")

# Configuración de templates y base de datos
templates = Jinja2Templates(directory="app/templates")

# Crear las tablas
models.Base.metadata.create_all(bind=engine)

# Dependency para obtener la DB

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Obtener el usuario actual desde la cookie
def get_current_user(request: Request, db: Session):
    user_id = request.cookies.get("user_id")
    if user_id:
        return db.query(models.User).filter(models.User.id == int(user_id)).first()
    return None

# Ruta principal
@app.get("/", response_class=HTMLResponse, response_model=None)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    pending_tasks = []
    completed_tasks = []

    if user:
        tasks = db.query(models.Task).filter(models.Task.user_id == user.id).all()
        pending_tasks = [t for t in tasks if not t.completed]
        completed_tasks = [t for t in tasks if t.completed]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks
    })

# Crear tarea
@app.post("/tasks/create")
async def create_task(
    request: Request,
    title: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")

    task = models.Task(title=title, user_id=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)

    return RedirectResponse(url="/", status_code=303)

# Eliminar tarea
@app.post("/tasks/delete/{task_id}")
async def delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")

    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    db.delete(task)
    db.commit()

    return RedirectResponse(url="/", status_code=303)

# Alternar estado de tarea
@app.get("/tasks/toggle/{task_id}")
async def toggle_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")

    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    task.completed = not task.completed
    db.commit()

    return RedirectResponse(url="/", status_code=303)

# Registro (GET)
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Registro (POST)
@app.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "El usuario ya existe."
        })

    hashed_pw = auth.hash_password(password)
    new_user = models.User(username=username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()

    return RedirectResponse(url="/login?msg=Registro exitoso", status_code=303)

# Login (GET)
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    msg = request.query_params.get("msg")
    return templates.TemplateResponse("login.html", {"request": request, "msg": msg})

# Login (POST)
@app.post("/login")
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Credenciales inválidas."
        })

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(user.id), httponly=True)
    return response

# Logout
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login?msg=Has cerrado sesión", status_code=303)
    response.delete_cookie("user_id")
    return response

# Editar Tarea 
@app.post("/tasks/edit/{task_id}")
async def edit_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(lambda request=Depends(), db=Depends(get_db): get_current_user(request, db))
):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == user.id).first()
    if task:
        task.title = title
        db.commit()
    return RedirectResponse(url="/?msg=Tarea+editada+correctamente", status_code=HTTP_303_SEE_OTHER)