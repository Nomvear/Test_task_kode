import csv
import requests
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from users import authenticate_user


app = FastAPI()
security = HTTPBasic()

FILE_NOTES = "notes.csv"
YA_SPELL_URL = "https://speller.yandex.net/services/spellservice.json/checkText"

#Модель для данных заметки
class NoteBase(BaseModel):
    content: str

#Модель для создания новой заметки
class NoteCreate(NoteBase):
    pass

#Полная модель заметки
class Note(NoteBase):
    id: int
    owner: str

#Проверка орфографии текста
def check_text(text:str):
    response = requests.get(f"{YA_SPELL_URL}?text={text}")
    if response.status_code == 200:
        errors = response.json()
        return len(errors) == 0
    return False

#Загрузка заметки из csv-файла
def load_notes() -> List[Note]:
    notes = []
    with open(FILE_NOTES, mode = "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            notes.append(Note(id = int(row["id"]), content = row["content"], owner = row["owner"]))
    return notes

#Сохранение новой заметки в csv-файл
def save_notes(note: NoteCreate, owner: str):
    notes = load_notes()
    new_id = len(notes) + 1
    with open(FILE_NOTES, mode = "a", newline = "") as file:
        writer = csv.DictWriter(file, fieldnames = ["id", "content", "owner"])
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow({"id": new_id, "content": note.content, "owner": owner})

#Получение текущего пользователя
def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code = 401, detail = "Incorrect username or password")
    return user["username"]

#Добавление новой заметки
@app.post("/notes/", response_model = List[Note])
async def create_note(note:NoteCreate, username: str = Depends(get_current_user())):
    if not check_text(note.content):
        raise HTTPException(status_code = 400, detail = "Orthographic errors found in the note")
    save_notes(note, username)
    return {"id": len(load_notes()), "content": note.content, "owner": username}


#Получение всех заметок текущего пользователя
@app.get("/notes/", response_model = List[Note])
async def get_notes(username: str = Depends(get_current_user())):
    notes = load_notes()
    user_notes = [note for note in notes if note.owner == username]
    return user_notes
