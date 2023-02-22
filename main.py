import sqlite3
import uvicorn
from multiprocessing import cpu_count, freeze_support
import api





def start_server(host="127.0.0.1",
                 port=8000,
                 num_workers=4,
                 loop="asyncio",
                 reload=False):
    uvicorn.run("api:app",
                host=host,
                port=port,
                workers=num_workers,
                loop=loop,
                reload=reload)


if __name__ == "__main__":
    freeze_support()  # Needed for pyinstaller for multiprocessing on WindowsOS
    num_workers = 4
    start_server(num_workers=num_workers)
    print(sqlite3.version)