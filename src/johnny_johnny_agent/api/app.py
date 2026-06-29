from fastapi import FastAPI


app = FastAPI(title="Johnny-Johnny Agent")


@app.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello from Johnny-Johnny"}