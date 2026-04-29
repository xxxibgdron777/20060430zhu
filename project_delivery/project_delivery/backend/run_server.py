import uvicorn

if __name__ == "__main__":
    print("Starting server at http://localhost:80")
    uvicorn.run("main:app", host="0.0.0.0", port=80)
