# 🚀 Pasos para ejecutar el proyecto

### 1️⃣ Crear entorno virtual

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3️⃣ Ejecutar el proyecto

```bash
uvicorn App.Main:app --reload
```

### 4️⃣ Abrir en el navegador

- 🌐 [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📘 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 🧾 [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
